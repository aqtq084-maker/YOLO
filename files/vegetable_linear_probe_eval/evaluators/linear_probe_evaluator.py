"""
線形プルーブ (Linear Probe) 評価器

線形プルーブとは、DINOv2のような自己教師あり学習(SSL)モデルが
抽出した特徴量の「質」を評価する代表的な方法の一つ。

    バックボーン(DINOv2)は完全に凍結(freeze)したまま、
    その特徴量の上に単純な"線形"分類器(ロジスティック回帰)だけを学習させ、
    その精度で特徴表現の良し悪しを測る。

なぜ線形分類器を使うのか:
    - k-NNやSVM(RBFカーネル)のような複雑な決定境界を許す分類器だと、
      「分類器側の頑張り」で精度が上振れしてしまい、
      特徴量そのものがどれだけクラスごとにきれいに分かれているかが見えにくい。
    - 線形分類器しか使わないことで、「特徴空間内でクラスが線形分離可能かどうか」
      = 特徴表現そのものの質を、より素直に評価できる。

拡張性のポイント:
    - 正則化の強さ(C)、標準化の有無、クラス不均衡への対処(class_weight)
      などをLinearProbeConfigで切り替え可能。
    - 将来、線形SVM(LinearSVC)などの別の線形分類器を追加したい場合は、
      同じ形式で build_xxx_evaluator() 関数を追加すればよい。
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .base import CVConfig, SklearnCVEvaluator


@dataclass
class LinearProbeConfig:
    C: float = 1.0
    # 正則化の強さの逆数。小さいほど正則化が強く(単純なモデルに)、
    # 大きいほど正則化が弱く(訓練データに忠実に)なる。

    max_iter: int = 2000
    # ロジスティック回帰の最適化の最大反復回数。
    # 特徴次元が大きい(DINOv2は768〜1536次元程度)ので収束に時間がかかることがある。

    standardize: bool = True
    # 特徴量を平均0・分散1に標準化してから学習するか。
    # 線形モデルはスケールの影響を受けやすいため、基本的にTrue推奨。

    class_weight: str = "balanced"
    # "balanced"にすると、野菜ごとの写真枚数に偏りがあっても
    # 少数クラスを軽視しないよう自動で重み付けする。

    cv_method: str = "kfold"
    n_splits: int = 5


def build_linear_probe_evaluator(config: LinearProbeConfig) -> SklearnCVEvaluator:
    clf = LogisticRegression(
        C=config.C,
        max_iter=config.max_iter,
        class_weight=config.class_weight,
    )

    if config.standardize:
        estimator = Pipeline([("scaler", StandardScaler()), ("clf", clf)])
    else:
        estimator = clf

    cv_config = CVConfig(cv_method=config.cv_method, n_splits=config.n_splits)
    return SklearnCVEvaluator(estimator, cv_config)
