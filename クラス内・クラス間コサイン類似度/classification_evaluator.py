"""
[拡張例] 教師ありの分類ベース評価器 (k-NN / 線形プルーブ)

silhouette_evaluator.py が「教師なし」で特徴空間の分かれ方を直接見るのに対し、
こちらは「実際に分類器を学習させて交差検証で正解率を測る」教師あり評価。
比較用・拡張の実例として同梱している。

新しい分類ベースの評価手法(線形SVMなど)を追加したい場合は、
build_xxx_evaluator() のような関数をここに1つ追加し、
evaluators/__init__.py の METHOD_REGISTRY に登録するだけでよい。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import LeaveOneOut, StratifiedKFold, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from .base import BaseEvaluator


@dataclass
class KNNConfig:
    k: int = 5
    metric: str = "cosine"
    weights: str = "distance"
    cv_method: str = "loo"
    n_splits: int = 5


@dataclass
class LinearProbeConfig:
    C: float = 1.0
    max_iter: int = 2000
    standardize: bool = True
    class_weight: str = "balanced"
    cv_method: str = "kfold"
    n_splits: int = 5


class ClassificationCVEvaluator(BaseEvaluator):
    """任意のscikit-learn互換estimatorを交差検証で評価する汎用評価器"""

    def __init__(self, estimator, cv_method: str, n_splits: int, method_label: str):
        self.estimator = estimator
        self.cv_method = cv_method
        self.n_splits = n_splits
        self.method_label = method_label

    def evaluate(self, X: np.ndarray, y: List[str], out_dir: Path) -> str:
        le = LabelEncoder()
        y_enc = le.fit_transform(y)

        min_count = min(Counter(y).values())
        if self.cv_method == "loo":
            cv = LeaveOneOut()
        elif self.cv_method == "kfold":
            if min_count < self.n_splits:
                raise ValueError(
                    f"最小クラスのサンプル数({min_count})がn_splits({self.n_splits})未満です"
                )
            cv = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=42)
        else:
            raise ValueError(f"未知のcv_methodです: {self.cv_method}")

        y_pred_enc = cross_val_predict(self.estimator, X, y_enc, cv=cv)
        y_true = le.inverse_transform(y_enc).tolist()
        y_pred = le.inverse_transform(y_pred_enc).tolist()

        acc = accuracy_score(y_true, y_pred)
        cm = confusion_matrix(y_true, y_pred, labels=le.classes_)
        report = classification_report(y_true, y_pred, labels=le.classes_, zero_division=0)

        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "report.txt", "w", encoding="utf-8") as f:
            f.write(f"method={self.method_label}, cv={self.cv_method}\n")
            f.write(f"Accuracy: {acc:.4f}\n\n")
            f.write(report)

        self._plot_confusion_matrix(cm, list(le.classes_), out_dir / "confusion_matrix.png")

        return f"Accuracy: {acc:.4f}\n\n{report}"

    @staticmethod
    def _plot_confusion_matrix(cm, labels, save_path: Path) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        n = len(labels)
        fig, ax = plt.subplots(figsize=(max(6, n * 0.6), max(5, n * 0.6)))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_yticklabels(labels)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title("Confusion Matrix")
        thresh = cm.max() / 2 if cm.max() > 0 else 0
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(
                    j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black",
                )
        fig.colorbar(im, ax=ax)
        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)


def build_knn_evaluator(config: KNNConfig) -> ClassificationCVEvaluator:
    estimator = KNeighborsClassifier(
        n_neighbors=config.k, metric=config.metric, weights=config.weights
    )
    return ClassificationCVEvaluator(estimator, config.cv_method, config.n_splits, "knn")


def build_linear_probe_evaluator(config: LinearProbeConfig) -> ClassificationCVEvaluator:
    clf = LogisticRegression(
        C=config.C, max_iter=config.max_iter, class_weight=config.class_weight
    )
    estimator = (
        Pipeline([("scaler", StandardScaler()), ("clf", clf)])
        if config.standardize
        else clf
    )
    return ClassificationCVEvaluator(estimator, config.cv_method, config.n_splits, "linear_probe")
