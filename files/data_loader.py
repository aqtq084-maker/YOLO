"""
データローダー

features_photo_homu 以下のディレクトリ構造から
DINOv2特徴量(.npyファイル)を読み込み、ラベル付きサンプルとして返す。

想定ディレクトリ構造:
    features_photo_homu/
        かぼちゃ/
            001_cls.npy
            001_patch.npy
            002_cls.npy
            002_patch.npy
            ...
        さといも/
            001_cls.npy
            001_patch.npy
            ...
        じゃがいも/
            ...

拡張性のポイント:
    - サブディレクトリ名がそのままラベルになるので、
      野菜を追加したい場合はディレクトリを追加するだけでよい。
    - "_cls.npy" / "_patch.npy" 以外の接尾辞(例: "_reg.npy" など、
      将来DINOv2のregisterトークン等を保存したくなった場合)にも
      自動的に対応できるように、接尾辞ごとにグルーピングして保持する。
      → 新しい接尾辞を追加しても、このファイルを変更する必要はない。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Union

import numpy as np

logger = logging.getLogger(__name__)

# ファイル名パターン: <連番>_<接尾辞>.npy  例: 001_cls.npy, 012_patch.npy
FILENAME_PATTERN = re.compile(r"^(?P<index>\d+)_(?P<suffix>[a-zA-Z0-9]+)\.npy$")


@dataclass
class Sample:
    """1枚の写真に対応する特徴量サンプル"""

    label: str  # 野菜名 (ディレクトリ名)
    index: str  # 連番 (例: "001")
    features: Dict[str, np.ndarray] = field(default_factory=dict)
    # features例: {"cls": (D,) ndarray, "patch": (N, D) ndarray}

    @property
    def sample_id(self) -> str:
        return f"{self.label}/{self.index}"


class FeatureDataset:
    """features_photo_homu 配下を走査してサンプル一覧を構築するクラス"""

    def __init__(self, root_dir: Union[str, Path]):
        self.root_dir = Path(root_dir)
        if not self.root_dir.exists():
            raise FileNotFoundError(f"データディレクトリが見つかりません: {self.root_dir}")
        self.samples: List[Sample] = []
        self._load()

    def _load(self) -> None:
        vegetable_dirs = sorted(d for d in self.root_dir.iterdir() if d.is_dir())
        if not vegetable_dirs:
            raise RuntimeError(f"{self.root_dir} 配下に野菜ディレクトリが見つかりません")

        for veg_dir in vegetable_dirs:
            label = veg_dir.name
            grouped: Dict[str, Dict[str, Path]] = {}

            for f in sorted(veg_dir.glob("*.npy")):
                m = FILENAME_PATTERN.match(f.name)
                if not m:
                    logger.warning("命名規則に合わないファイルをスキップ: %s", f)
                    continue
                idx = m.group("index")
                suffix = m.group("suffix")
                grouped.setdefault(idx, {})[suffix] = f

            for idx, suffix_map in sorted(grouped.items()):
                features: Dict[str, np.ndarray] = {}
                for suffix, path in suffix_map.items():
                    try:
                        features[suffix] = np.load(path)
                    except Exception as e:  # 壊れたファイル等をスキップして継続
                        logger.warning("読み込み失敗のためスキップ: %s (%s)", path, e)
                if not features:
                    continue
                self.samples.append(Sample(label=label, index=idx, features=features))

        logger.info(
            "読み込み完了: %d サンプル, %d クラス", len(self.samples), len(self.labels)
        )

    @property
    def labels(self) -> List[str]:
        return sorted({s.label for s in self.samples})

    def available_suffixes(self) -> List[str]:
        """データセット内に存在する特徴量の種類 (cls, patch, ...) を返す"""
        suffixes = set()
        for s in self.samples:
            suffixes.update(s.features.keys())
        return sorted(suffixes)

    def summary(self) -> Dict[str, int]:
        """クラスごとのサンプル数を返す (データの偏り確認用)"""
        counts: Dict[str, int] = {}
        for s in self.samples:
            counts[s.label] = counts.get(s.label, 0) + 1
        return counts
