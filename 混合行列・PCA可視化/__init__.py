"""
評価手法レジストリ

main.py が --method 引数(文字列)から、対応する
Config クラスと評価器を組み立てる関数を引けるようにする。

拡張性のポイント:
    新しい評価手法を追加する場合:
        1. evaluators/xxx_evaluator.py に
           XxxConfig と build_xxx_evaluator() を定義し、
           BaseEvaluator を継承したクラスとして実装する
        2. 下の METHOD_REGISTRY に1行追加
    これだけで main.py --method xxx として使えるようになる。
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple, Type

from .base import BaseEvaluator
from .classification_evaluator import (
    KNNConfig,
    LinearProbeConfig,
    build_knn_evaluator,
    build_linear_probe_evaluator,
)
from .confusion_pca_evaluator import ConfusionPCAConfig, build_confusion_pca_evaluator
from .intra_inter_cosine_evaluator import (
    IntraInterCosineConfig,
    build_intra_inter_cosine_evaluator,
)
from .silhouette_evaluator import SilhouetteConfig, build_silhouette_evaluator

# 手法名 -> (Configクラス, 評価器を組み立てる関数)
METHOD_REGISTRY: Dict[str, Tuple[Type, Callable[..., BaseEvaluator]]] = {
    "confusion_pca": (ConfusionPCAConfig, build_confusion_pca_evaluator),
    "intra_inter_cosine": (IntraInterCosineConfig, build_intra_inter_cosine_evaluator),
    "silhouette": (SilhouetteConfig, build_silhouette_evaluator),
    "linear_probe": (LinearProbeConfig, build_linear_probe_evaluator),
    "knn": (KNNConfig, build_knn_evaluator),
}


def list_methods():
    return sorted(METHOD_REGISTRY.keys())


def build_evaluator(method: str, config) -> BaseEvaluator:
    if method not in METHOD_REGISTRY:
        raise ValueError(f"未知の評価手法です: {method} (利用可能: {list_methods()})")
    _, builder = METHOD_REGISTRY[method]
    return builder(config)
