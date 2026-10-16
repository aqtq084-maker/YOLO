"""
評価器の共通インターフェース

シルエットスコア(教師なし)・線形プルーブ/k-NN(教師あり)のように、
性質の大きく異なる評価手法を、main.py から同じ形で呼び出せるようにするための
抽象基底クラス。

拡張性のポイント:
    新しい評価手法(Davies-Bouldin指数、Calinski-Harabasz指数、
    別の分類器など)を追加する場合は、BaseEvaluatorを継承して
    evaluate(X, y, out_dir) を実装するだけでよい。
    評価手法ごとに必要な出力(レポートの中身/画像の種類)が異なっても構わない
    ―― 各evaluatorが自分の責任で出力を完結させる設計にしているため、
    main.py側は「evaluate()を呼んでサマリーを表示する」だけで済む。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

import numpy as np


class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, X: np.ndarray, y: List[str], out_dir: Path) -> str:
        """
        特徴量Xとラベルyを評価する。

        - out_dir 配下に、この評価手法に必要なレポート・画像を保存する
          (何を保存するかは評価手法ごとに自由でよい)
        - コンソールに表示するためのサマリーテキストを返す
        """
        raise NotImplementedError
