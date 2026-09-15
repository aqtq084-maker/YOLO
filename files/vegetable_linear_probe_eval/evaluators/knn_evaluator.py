"""
k-NN評価器 (拡張例)

線形プルーブとの比較用に、以前作成したk-NN評価器を
同じ共通基盤(SklearnCVEvaluator)の上に載せ直したもの。

「評価手法を追加するときはこのファイルのような形で1つ追加するだけでよい」
という拡張性の実例でもある。main.py側では --method knn を指定するだけで
線形プルーブとk-NNを同じ土俵で比較できる。
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.neighbors import KNeighborsClassifier

from .base import CVConfig, SklearnCVEvaluator


@dataclass
class KNNConfig:
    k: int = 5
    metric: str = "cosine"
    weights: str = "distance"
    cv_method: str = "loo"
    n_splits: int = 5


def build_knn_evaluator(config: KNNConfig) -> SklearnCVEvaluator:
    estimator = KNeighborsClassifier(
        n_neighbors=config.k, metric=config.metric, weights=config.weights
    )
    cv_config = CVConfig(cv_method=config.cv_method, n_splits=config.n_splits)
    return SklearnCVEvaluator(estimator, cv_config)
