"""
評価器 共通基盤

線形プルーブ・k-NNなど、異なる分類手法を「同じインターフェース」で
評価できるようにするための共通処理をまとめたモジュール。

拡張性のポイント:
    - scikit-learn互換のestimator(fit/predictを持つもの)さえ用意すれば、
      SklearnCVEvaluatorにそれを渡すだけで
      交差検証・Accuracy・混同行列・クラス別レポートの生成を
      共通ロジックとして再利用できる。
    - 将来SVMなど新しい評価手法を追加する場合も、
      「evaluators/新しい評価器.py」を1つ追加するだけでよく、
      このファイルの変更は不要。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import List

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import LeaveOneOut, StratifiedKFold, cross_val_predict
from sklearn.preprocessing import LabelEncoder


@dataclass
class CVConfig:
    """交差検証の設定（評価手法によらず共通）"""

    cv_method: str = "kfold"  # "loo" または "kfold"
    n_splits: int = 5  # cv_method="kfold" のときのみ使用


@dataclass
class EvalResult:
    accuracy: float
    y_true: List[str]
    y_pred: List[str]
    confusion: np.ndarray
    class_labels: List[str]
    report_text: str


def build_cv(config: CVConfig, min_class_count: int):
    if config.cv_method == "loo":
        return LeaveOneOut()
    if config.cv_method == "kfold":
        if min_class_count < config.n_splits:
            raise ValueError(
                f"最小クラスのサンプル数({min_class_count})がn_splits({config.n_splits})未満です。"
                "n_splitsを減らすか、cv_method='loo'を使ってください。"
            )
        return StratifiedKFold(n_splits=config.n_splits, shuffle=True, random_state=42)
    raise ValueError(f"未知のcv_methodです: {config.cv_method}")


class SklearnCVEvaluator:
    """任意のscikit-learn互換estimatorを交差検証で評価する汎用評価器"""

    def __init__(self, estimator, cv_config: CVConfig):
        self.estimator = estimator
        self.cv_config = cv_config

    def evaluate(self, X: np.ndarray, y: List[str]) -> EvalResult:
        if len(X) != len(y):
            raise ValueError("Xとyのサンプル数が一致しません")

        le = LabelEncoder()
        y_enc = le.fit_transform(y)

        min_count = min(Counter(y).values())
        cv = build_cv(self.cv_config, min_count)

        y_pred_enc = cross_val_predict(self.estimator, X, y_enc, cv=cv)

        y_true = le.inverse_transform(y_enc).tolist()
        y_pred = le.inverse_transform(y_pred_enc).tolist()

        acc = accuracy_score(y_true, y_pred)
        cm = confusion_matrix(y_true, y_pred, labels=le.classes_)
        report = classification_report(
            y_true, y_pred, labels=le.classes_, zero_division=0
        )

        return EvalResult(
            accuracy=acc,
            y_true=y_true,
            y_pred=y_pred,
            confusion=cm,
            class_labels=list(le.classes_),
            report_text=report,
        )
