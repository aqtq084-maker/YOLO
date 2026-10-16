"""
特徴量加工モジュール

DINOv2から得られる cls トークン (形状: (D,) や (1, D)) と
patch トークン群 (形状: (N, D) や (1, N, D)) を、
k-NN分類に使える1次元ベクトルへ変換するための「戦略」を定義する。

拡張性のポイント:
    - 新しい特徴量の合成方法を増やしたい場合は、
      @register_strategy("名前") を付けた関数を1つ追加するだけでよい。
      main.py 側は文字列(戦略名)を指定するだけで新しい戦略を使える。
    - 例えば将来 "patch_max" と "cls" を重み付き結合したい、
      DINOv2のregisterトークンを使いたい、といった要望にも
      この形式で追加していける。
"""

from __future__ import annotations

from typing import Callable, Dict, List

import numpy as np

from data_loader import Sample

_STRATEGY_REGISTRY: Dict[str, Callable[[Sample], np.ndarray]] = {}


def register_strategy(name: str):
    """特徴量合成戦略を登録するデコレータ"""

    def decorator(func: Callable[[Sample], np.ndarray]):
        _STRATEGY_REGISTRY[name] = func
        return func

    return decorator


def list_strategies() -> List[str]:
    return sorted(_STRATEGY_REGISTRY.keys())


def build_feature_vector(sample: Sample, strategy: str) -> np.ndarray:
    if strategy not in _STRATEGY_REGISTRY:
        raise ValueError(
            f"未知の特徴量戦略です: {strategy} (利用可能: {list_strategies()})"
        )
    return _STRATEGY_REGISTRY[strategy](sample)


def _require(sample: Sample, key: str) -> np.ndarray:
    if key not in sample.features:
        raise KeyError(f"'{key}'トークンが存在しません: {sample.sample_id}")
    return np.asarray(sample.features[key])


def _to_1d(x: np.ndarray) -> np.ndarray:
    """(D,) や (1, D) など、余分な次元を落として1次元にする"""
    return x.reshape(-1)


def _to_2d(x: np.ndarray) -> np.ndarray:
    """(N, D) や (1, N, D) など、余分な先頭次元を落として (N, D) にする"""
    if x.ndim > 2:
        x = x.reshape(-1, x.shape[-1])
    return x


@register_strategy("cls")
def _cls_only(sample: Sample) -> np.ndarray:
    """cls トークンのみを使用する（最もシンプルなベースライン）"""
    return _to_1d(_require(sample, "cls"))


@register_strategy("patch_mean")
def _patch_mean(sample: Sample) -> np.ndarray:
    """patch トークン群を平均プーリングして使用する"""
    p = _to_2d(_require(sample, "patch"))
    return p.mean(axis=0)


@register_strategy("patch_max")
def _patch_max(sample: Sample) -> np.ndarray:
    """patch トークン群を最大値プーリングして使用する"""
    p = _to_2d(_require(sample, "patch"))
    return p.max(axis=0)


@register_strategy("cls_patch_mean_concat")
def _cls_patch_mean_concat(sample: Sample) -> np.ndarray:
    """cls トークンと patch平均プーリングを連結して使用する"""
    return np.concatenate([_cls_only(sample), _patch_mean(sample)], axis=0)


@register_strategy("cls_patch_maxmean_concat")
def _cls_patch_maxmean_concat(sample: Sample) -> np.ndarray:
    """cls + patch平均 + patch最大 をすべて連結する（情報量重視）"""
    return np.concatenate(
        [_cls_only(sample), _patch_mean(sample), _patch_max(sample)], axis=0
    )
