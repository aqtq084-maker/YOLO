"""
野菜判定AI 精度評価スクリプト (線形プルーブ版) エントリーポイント

使い方:
    # 既定: 線形プルーブ (ロジスティック回帰) + 5分割層化交差検証
    python main.py --data-dir features_photo_homu --strategy cls

    # 正則化の強さ・特徴量の合成方法を変える場合
    python main.py --strategy cls_patch_mean_concat --C 0.1

    # (拡張例) k-NNで評価したい場合、同じCLIのまま手法だけ差し替え可能
    python main.py --method knn --k 5 --metric cosine --cv loo

主な処理の流れ:
    1. FeatureDataset で features_photo_homu 以下を読み込み
    2. feature_processor で指定した戦略に基づき特徴ベクトルを構築
    3. evaluators で指定した手法(既定: 線形プルーブ)により交差検証で精度評価
    4. 結果をコンソール出力 + report.txt / confusion_matrix.png として保存
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np

from data_loader import FeatureDataset
from evaluators import build_evaluator, list_methods
from evaluators.knn_evaluator import KNNConfig
from evaluators.linear_probe_evaluator import LinearProbeConfig
from feature_processor import build_feature_vector, list_strategies


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="野菜判定AIの精度評価 (既定: 線形プルーブ)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="features_photo_homu",
        help="特徴量が保存されているルートディレクトリ",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="cls",
        choices=list_strategies(),
        help="特徴ベクトルの構築方法",
    )
    parser.add_argument(
        "--method",
        type=str,
        default="linear_probe",
        choices=list_methods(),
        help="評価手法 (linear_probe=線形プルーブ, knn=k近傍法)",
    )
    parser.add_argument(
        "--cv",
        type=str,
        default="kfold",
        choices=["loo", "kfold"],
        help="交差検証方法 (loo=Leave-One-Out, kfold=層化K分割)",
    )
    parser.add_argument(
        "--n-splits", type=int, default=5, help="cv=kfold のときの分割数"
    )

    # --- 線形プルーブ用オプション ---
    parser.add_argument(
        "--C", type=float, default=1.0, help="[linear_probe] 正則化の強さの逆数"
    )
    parser.add_argument(
        "--max-iter", type=int, default=2000, help="[linear_probe] 最大反復回数"
    )
    parser.add_argument(
        "--no-standardize",
        action="store_true",
        help="[linear_probe] 特徴量の標準化を無効にする",
    )
    parser.add_argument(
        "--class-weight",
        type=str,
        default="balanced",
        help="[linear_probe] クラス重み ('balanced' または None相当の 'none')",
    )

    # --- k-NN用オプション (拡張例) ---
    parser.add_argument("--k", type=int, default=5, help="[knn] k-NNのk値")
    parser.add_argument(
        "--metric", type=str, default="cosine", help="[knn] 距離指標"
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="distance",
        choices=["uniform", "distance"],
        help="[knn] 重み付け方法",
    )

    parser.add_argument(
        "--out-dir",
        type=str,
        default="eval_results",
        help="結果の出力先ディレクトリ",
    )
    return parser.parse_args()


def _build_config(args: argparse.Namespace):
    """--method に応じて対応するConfigオブジェクトを組み立てる"""
    if args.method == "linear_probe":
        class_weight = None if args.class_weight.lower() == "none" else args.class_weight
        return LinearProbeConfig(
            C=args.C,
            max_iter=args.max_iter,
            standardize=not args.no_standardize,
            class_weight=class_weight,
            cv_method=args.cv,
            n_splits=args.n_splits,
        )
    if args.method == "knn":
        return KNNConfig(
            k=args.k,
            metric=args.metric,
            weights=args.weights,
            cv_method=args.cv,
            n_splits=args.n_splits,
        )
    raise ValueError(f"未知の評価手法です: {args.method}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    args = parse_args()

    # 1. データ読み込み
    dataset = FeatureDataset(args.data_dir)
    print(f"クラス数: {len(dataset.labels)}  サンプル総数: {len(dataset.samples)}")
    print("クラスごとのサンプル数:", dataset.summary())
    print("利用可能な特徴量:", dataset.available_suffixes())

    # 2. 特徴ベクトル構築
    X_list, y_list = [], []
    for sample in dataset.samples:
        try:
            vec = build_feature_vector(sample, args.strategy)
        except KeyError as e:
            logging.warning("スキップ: %s", e)
            continue
        X_list.append(vec)
        y_list.append(sample.label)

    if not X_list:
        raise RuntimeError(
            f"strategy='{args.strategy}' に必要な特徴量を持つサンプルが1件もありません"
        )

    X = np.stack(X_list, axis=0)
    y = y_list

    # 3. 評価 (既定: 線形プルーブ)
    config = _build_config(args)
    evaluator = build_evaluator(args.method, config)
    result = evaluator.evaluate(X, y)

    print(f"\n=== 評価結果 (method={args.method}, strategy={args.strategy}, cv={args.cv}) ===")
    print(f"設定: {config}")
    print(f"Accuracy: {result.accuracy:.4f}")
    print(result.report_text)

    # 4. 結果保存
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "report.txt", "w", encoding="utf-8") as f:
        f.write(f"method={args.method}, strategy={args.strategy}, cv={args.cv}\n")
        f.write(f"config={config}\n")
        f.write(f"Accuracy: {result.accuracy:.4f}\n\n")
        f.write(result.report_text)

    _plot_confusion_matrix(
        result.confusion, result.class_labels, out_dir / "confusion_matrix.png"
    )
    print(f"\n結果を {out_dir} に保存しました。(report.txt, confusion_matrix.png)")


def _plot_confusion_matrix(cm: np.ndarray, labels: list, save_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(labels)
    fig, ax = plt.subplots(figsize=(max(6, n * 0.6), max(5, n * 0.6)))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix")

    thresh = cm.max() / 2 if cm.max() > 0 else 0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j,
                i,
                str(cm[i, j]),
                ha="center",
                va="center",
                color="white" if cm[i, j] > thresh else "black",
            )

    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
