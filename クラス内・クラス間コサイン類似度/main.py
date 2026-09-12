"""
野菜判定AI 精度評価スクリプト (クラス内・クラス間コサイン類似度版) エントリーポイント

使い方:
    # 既定: クラス内・クラス間コサイン類似度 (教師なし, clsトークン)
    python main.py --data-dir features_photo_homu --strategy cls

    # ヒートマップを省略する / 混同しやすいペアの表示数を変える場合
    python main.py --strategy cls --no-heatmap --top-k-pairs 10

    # (拡張例) シルエットスコア/線形プルーブ/k-NNに切り替えたい場合
    python main.py --method silhouette --strategy cls
    python main.py --method linear_probe --strategy cls
    python main.py --method knn --k 5 --cv loo

主な処理の流れ:
    1. FeatureDataset で features_photo_homu 以下を読み込み
    2. feature_processor で指定した戦略に基づき特徴ベクトルを構築
    3. evaluators で指定した手法(既定: クラス内・クラス間コサイン類似度)により評価
       (各evaluatorが自分でout_dir配下にレポート・画像を保存する)
    4. コンソールにサマリーを表示
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np

from data_loader import FeatureDataset
from evaluators import build_evaluator, list_methods
from evaluators.classification_evaluator import KNNConfig, LinearProbeConfig
from evaluators.intra_inter_cosine_evaluator import IntraInterCosineConfig
from evaluators.silhouette_evaluator import SilhouetteConfig
from feature_processor import build_feature_vector, list_strategies


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="野菜判定AIの精度評価 (既定: クラス内・クラス間コサイン類似度/教師なし)"
    )
    parser.add_argument(
        "--data-dir", type=str, default="features_photo_homu",
        help="特徴量が保存されているルートディレクトリ",
    )
    parser.add_argument(
        "--strategy", type=str, default="cls", choices=list_strategies(),
        help="特徴ベクトルの構築方法",
    )
    parser.add_argument(
        "--method", type=str, default="intra_inter_cosine", choices=list_methods(),
        help="評価手法 (intra_inter_cosine=クラス内・クラス間コサイン類似度[教師なし], "
             "silhouette=シルエットスコア[教師なし], "
             "linear_probe=線形プルーブ, knn=k近傍法)",
    )
    parser.add_argument(
        "--out-dir", type=str, default="eval_results",
        help="結果の出力先ディレクトリ",
    )

    # --- クラス内・クラス間コサイン類似度用オプション ---
    parser.add_argument(
        "--no-heatmap", action="store_true",
        help="[intra_inter_cosine] クラス×クラスのヒートマップ出力を無効にする",
    )
    parser.add_argument(
        "--top-k-pairs", type=int, default=5,
        help="[intra_inter_cosine] レポートに表示する「混同しやすいクラスペア」の件数",
    )

    # --- シルエットスコア用オプション ---
    parser.add_argument(
        "--metric", type=str, default="cosine",
        help="[silhouette/knn] 距離指標 (cosine, euclidean など)",
    )
    parser.add_argument(
        "--no-pca-plot", action="store_true",
        help="[silhouette] PCA散布図の出力を無効にする",
    )

    # --- 教師あり評価(拡張例)用オプション ---
    parser.add_argument(
        "--cv", type=str, default="kfold", choices=["loo", "kfold"],
        help="[linear_probe/knn] 交差検証方法",
    )
    parser.add_argument("--n-splits", type=int, default=5, help="[linear_probe/knn] kfoldの分割数")
    parser.add_argument("--C", type=float, default=1.0, help="[linear_probe] 正則化の強さの逆数")
    parser.add_argument("--max-iter", type=int, default=2000, help="[linear_probe] 最大反復回数")
    parser.add_argument("--no-standardize", action="store_true", help="[linear_probe] 標準化を無効化")
    parser.add_argument("--class-weight", type=str, default="balanced", help="[linear_probe] クラス重み")
    parser.add_argument("--k", type=int, default=5, help="[knn] k値")
    parser.add_argument(
        "--weights", type=str, default="distance", choices=["uniform", "distance"],
        help="[knn] 重み付け方法",
    )

    return parser.parse_args()


def _build_config(args: argparse.Namespace):
    if args.method == "intra_inter_cosine":
        return IntraInterCosineConfig(
            make_heatmap=not args.no_heatmap,
            top_k_confusable_pairs=args.top_k_pairs,
        )
    if args.method == "silhouette":
        return SilhouetteConfig(metric=args.metric, make_pca_plot=not args.no_pca_plot)
    if args.method == "linear_probe":
        class_weight = None if args.class_weight.lower() == "none" else args.class_weight
        return LinearProbeConfig(
            C=args.C, max_iter=args.max_iter, standardize=not args.no_standardize,
            class_weight=class_weight, cv_method=args.cv, n_splits=args.n_splits,
        )
    if args.method == "knn":
        return KNNConfig(
            k=args.k, metric=args.metric, weights=args.weights,
            cv_method=args.cv, n_splits=args.n_splits,
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

    # 3. 評価 (既定: クラス内・クラス間コサイン類似度)
    config = _build_config(args)
    evaluator = build_evaluator(args.method, config)

    out_dir = Path(args.out_dir)
    summary = evaluator.evaluate(X, y, out_dir)

    print(f"\n=== 評価結果 (method={args.method}, strategy={args.strategy}) ===")
    print(f"設定: {config}")
    print(summary)
    print(f"\n結果を {out_dir} に保存しました。")


if __name__ == "__main__":
    main()
