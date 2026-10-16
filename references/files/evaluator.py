"""
k-NN による評価器

特徴量ベクトルとラベルを受け取り、k-NN分類器の精度を
交差検証 (Leave-One-Out または Stratified K-Fold) で評価する。

野菜判定AIのように「クラスごとの写真枚数が少ない」タスクでは、
学習データとテストデータを固定で分割するより、
交差検証で全サンプルを漏れなく評価したほうが精度の見積もりが安定する。

拡張性のポイント:
    - k値・距離指標(metric)・交差検証方法をEvalConfigで切り替え可能。
    - 将来的にk-NN以外の分類器(SVM, ロジスティック回帰など)を
      比較したくなった場合は、同じ evaluate(X, y) インターフェースを持つ
      クラスを追加すれば main.py 側はほぼそのまま流用できる。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import LeaveOneOut, StratifiedKFold, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder


@dataclass
class EvalConfig:
    k: int = 5
    metric: str = "cosine"  # "cosine", "euclidean", "manhattan" など
    cv_method: str = "loo"  # "loo" または "kfold"
    n_splits: int = 5  # cv_method="kfold" のときのみ使用
    weights: str = "distance"  # "uniform" または "distance"


@dataclass
class EvalResult:
    accuracy: float
    y_true: List[str]
    y_pred: List[str]
    confusion: np.ndarray
    class_labels: List[str]
    report_text: str


class KNNEvaluator:
    def __init__(self, config: Optional[EvalConfig] = None):
        self.config = config or EvalConfig()

    def evaluate(self, X: np.ndarray, y: List[str]) -> EvalResult:
        self._validate(X, y)

        le = LabelEncoder()
        y_enc = le.fit_transform(y)

        clf = KNeighborsClassifier(
            n_neighbors=self.config.k,
            metric=self.config.metric,
            weights=self.config.weights,
        )

        cv = self._build_cv()
        y_pred_enc = cross_val_predict(clf, X, y_enc, cv=cv)

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

    def _build_cv(self):
        if self.config.cv_method == "loo":
            return LeaveOneOut()
        if self.config.cv_method == "kfold":
            return StratifiedKFold(
                n_splits=self.config.n_splits, shuffle=True, random_state=42
            )
        raise ValueError(f"未知のcv_methodです: {self.config.cv_method}")

    def _validate(self, X: np.ndarray, y: List[str]) -> None:
        if len(X) != len(y):
            raise ValueError("Xとyのサンプル数が一致しません")

        from collections import Counter

        counts = Counter(y)
        min_count = min(counts.values())

        if self.config.cv_method == "kfold" and min_count < self.config.n_splits:
            raise ValueError(
                f"最小クラスのサンプル数({min_count})がn_splits({self.config.n_splits})未満です。"
                "n_splitsを減らすか、cv_method='loo'を使ってください。"
            )
        if self.config.k >= len(X):
            raise ValueError(
                f"k({self.config.k})がサンプル総数({len(X)})以上です。kを減らしてください。"
            )
