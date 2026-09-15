"""
野菜判定AI 精度評価スクリプト エントリーポイント

使い方:
    python main.py --data-dir features_photo_homu --strategy cls --k 5

    # patch特徴量の平均プーリングを使い、5分割交差検証で評価する場合
    python main.py --strategy patch_mean --cv kfold --n-splits 5

主な処理の流れ:
    1. FeatureDataset で features_photo_homu 以下を読み込み
    2. feature_processor で指定した戦略に基づき特徴ベクトルを構築
    3. KNNEvaluator で交差検証による精度評価
    4. 結果をコンソール出力 + report.txt / confusion_matrix.png として保存
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np

from data_loader import FeatureDataset
from evaluator import EvalConfig, KNNEvaluator
from feature_processor import build_feature_vector, list_strategies


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="野菜判定AIのk-NN精度評価")
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
    parser.add_argument("--k", type=int, default=5, help="k-NNのk値")
    parser.add_argument(
        "--metric",
        type=str,
        default="cosine",
        help="距離指標 (cosine, euclidean, manhattan など)",
    )
    parser.add_argument(
        "--cv",
        type=str,
        default="loo",
        choices=["loo", "kfold"],
        help="交差検証方法 (loo=Leave-One-Out, kfold=層化K分割)",
    )
    parser.add_argument(
        "--n-splits", type=int, default=5, help="cv=kfold のときの分割数"
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="distance",
        choices=["uniform", "distance"],
        help="k-NNの重み付け方法",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="eval_results",
        help="結果の出力先ディレクトリ",
    )
    return parser.parse_args()


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

    # 3. k-NN評価
    config = EvalConfig(
        k=args.k,
        metric=args.metric,
        cv_method=args.cv,
        n_splits=args.n_splits,
        weights=args.weights,
    )
    evaluator = KNNEvaluator(config)
    result = evaluator.evaluate(X, y)

    print(
        f"\n=== 評価結果 (strategy={args.strategy}, k={args.k}, "
        f"metric={args.metric}, cv={args.cv}) ==="
    )
    print(f"Accuracy: {result.accuracy:.4f}")
    print(result.report_text)

    # 4. 結果保存
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "report.txt", "w", encoding="utf-8") as f:
        f.write(
            f"strategy={args.strategy}, k={args.k}, metric={args.metric}, "
            f"cv={args.cv}, weights={args.weights}\n"
        )
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
