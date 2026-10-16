"""
評価手法レジストリ

main.py が --method 引数(文字列)から、対応する
Config クラスと evaluator を組み立てる関数を引けるようにする。

拡張性のポイント:
    新しい評価手法(例: 線形SVM)を追加する場合:
        1. evaluators/linear_svm_evaluator.py に
           LinearSVMConfig と build_linear_svm_evaluator() を定義
        2. 下の METHOD_REGISTRY に1行追加
    これだけで main.py --method linear_svm として使えるようになる。
"""

from __future__ import annotations

from typing import Dict, Tuple, Type

from .base import EvalResult, SklearnCVEvaluator
from .knn_evaluator import KNNConfig, build_knn_evaluator
from .linear_probe_evaluator import LinearProbeConfig, build_linear_probe_evaluator

# 手法名 -> (Configクラス, 評価器を組み立てる関数)
METHOD_REGISTRY: Dict[str, Tuple[Type, callable]] = {
    "linear_probe": (LinearProbeConfig, build_linear_probe_evaluator),
    "knn": (KNNConfig, build_knn_evaluator),
}


def list_methods():
    return sorted(METHOD_REGISTRY.keys())


def get_config_class(method: str) -> Type:
    if method not in METHOD_REGISTRY:
        raise ValueError(f"未知の評価手法です: {method} (利用可能: {list_methods()})")
    return METHOD_REGISTRY[method][0]


def build_evaluator(method: str, config) -> SklearnCVEvaluator:
    if method not in METHOD_REGISTRY:
        raise ValueError(f"未知の評価手法です: {method} (利用可能: {list_methods()})")
    _, builder = METHOD_REGISTRY[method]
    return builder(config)
