"""
[拡張用モジュール] DINOv2特徴量抽出

現在の評価スクリプト(main.py)は事前に抽出済みの .npy ファイル
(features_photo_homu/<野菜名>/<連番>_cls.npy, <連番>_patch.npy) を前提としている。

このモジュールは、将来「新しい写真を撮ったその場でDINOv2特徴量を抽出し、
既存のデータセットに追加したい」というニーズのために用意した拡張ポイント。
評価ロジック本体(data_loader / feature_processor / evaluator)には一切依存しないため、
使わない場合は無視してよい。

必要なライブラリ (通常のnumpy/scikit-learn/matplotlibとは別に必要):
    pip install torch torchvision transformers pillow

使い方の例:
    from dinov2_extractor import DINOv2Extractor

    extractor = DINOv2Extractor(model_name="facebook/dinov2-base")
    extractor.extract_and_save(
        image_path="new_photos/kabocha_010.jpg",
        out_dir="features_photo_homu/かぼちゃ",
        index="010",
    )
    # -> features_photo_homu/かぼちゃ/010_cls.npy
    # -> features_photo_homu/かぼちゃ/010_patch.npy
    # が生成され、そのままmain.pyの評価対象に追加できる。
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, Union

import numpy as np


class DINOv2Extractor:
    def __init__(self, model_name: str = "facebook/dinov2-base", device: str = None):
        # 依存ライブラリはこのクラスを実際に使うときだけ必要になるよう、
        # あえてモジュール直下ではなく__init__内でimportしている。
        import torch
        from transformers import AutoImageProcessor, AutoModel

        self._torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device).eval()

    def extract(self, image_path: Union[str, Path]) -> Tuple[np.ndarray, np.ndarray]:
        """1枚の画像から (cls_token, patch_tokens) を抽出する"""
        from PIL import Image

        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with self._torch.no_grad():
            outputs = self.model(**inputs)

        last_hidden = outputs.last_hidden_state[0]  # (1 + N_patches, D)
        cls_token = last_hidden[0].cpu().numpy()  # (D,)
        patch_tokens = last_hidden[1:].cpu().numpy()  # (N_patches, D)
        return cls_token, patch_tokens

    def extract_and_save(
        self, image_path: Union[str, Path], out_dir: Union[str, Path], index: str
    ) -> None:
        """features_photo_homu の命名規則に沿って .npy を2つ保存する"""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        cls_token, patch_tokens = self.extract(image_path)
        np.save(out_dir / f"{index}_cls.npy", cls_token)
        np.save(out_dir / f"{index}_patch.npy", patch_tokens)
