"""
混同行列 + PCA可視化 評価器

実際に分類器を交差検証で学習・評価し、以下の2つを組み合わせて評価する。

    1. 混同行列 (Confusion Matrix):
       「かぼちゃ を さといも と間違えた枚数」のように、
       どの野菜がどの野菜に間違われやすいかを数値で確認できる。

    2. PCA可視化 (PCA scatter):
       DINOv2特徴量を2次元に圧縮して散布図に描画し、
       誤分類されたサンプルに印を付けることで、
       間違えたサンプルが特徴空間上のどこに位置するか
       (クラスの境界付近なのか、外れ値なのか)を視覚的に確認できる。

混同行列だけでは「何枚間違えたか」という数値情報しか得られないが、
PCA可視化と組み合わせることで「なぜ間違えたのか(特徴が似ていたから、
それとも外れ値だったから)」を推測する手がかりが得られる。

分類器はデフォルトでk-NNを使うが、線形プルーブ(ロジスティック回帰)
にも切り替え可能。

拡張性のポイント:
    - classifier: "knn" または "linear_probe" を切り替え可能。
      内部的にはscikit-learn互換のestimatorを組み立てているだけなので、
      将来SVMなど別の分類器を追加したい場合は
      _build_estimator() に分岐を1つ増やすだけでよい。
    - highlight_misclassified を False にすれば、
      通常のクラス分布確認用のPCA散布図としても使える。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import LeaveOneOut, StratifiedKFold, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from .base import BaseEvaluator


@dataclass
class ConfusionPCAConfig:
    classifier: str = "knn"  # "knn" または "linear_probe"
    cv_method: str = "loo"  # "loo" または "kfold"
    n_splits: int = 5

    # --- k-NN用 (classifier="knn"のとき使用) ---
    k: int = 5
    metric: str = "cosine"
    weights: str = "distance"

    # --- 線形プルーブ用 (classifier="linear_probe"のとき使用) ---
    C: float = 1.0
    max_iter: int = 2000
    standardize: bool = True
    class_weight: str = "balanced"

    # --- PCA可視化用 ---
    highlight_misclassified: bool = True
    # PCA散布図上で、誤分類されたサンプルを赤丸で強調するか


class ConfusionPCAEvaluator(BaseEvaluator):
    def __init__(self, config: ConfusionPCAConfig):
        self.config = config

    def _build_estimator(self):
        c = self.config
        if c.classifier == "knn":
            return KNeighborsClassifier(n_neighbors=c.k, metric=c.metric, weights=c.weights)
        if c.classifier == "linear_probe":
            clf = LogisticRegression(C=c.C, max_iter=c.max_iter, class_weight=c.class_weight)
            if c.standardize:
                return Pipeline([("scaler", StandardScaler()), ("clf", clf)])
            return clf
        raise ValueError(
            f"未知のclassifierです: {c.classifier} (利用可能: 'knn', 'linear_probe')"
        )

    def _build_cv(self, y: List[str]):
        c = self.config
        if c.cv_method == "loo":
            return LeaveOneOut()
        if c.cv_method == "kfold":
            min_count = min(Counter(y).values())
            if min_count < c.n_splits:
                raise ValueError(
                    f"最小クラスのサンプル数({min_count})がn_splits({c.n_splits})未満です。"
                    "n_splitsを減らすか、cv_method='loo'を使ってください。"
                )
            return StratifiedKFold(n_splits=c.n_splits, shuffle=True, random_state=42)
        raise ValueError(f"未知のcv_methodです: {c.cv_method}")

    def evaluate(self, X: np.ndarray, y: List[str], out_dir: Path) -> str:
        le = LabelEncoder()
        y_enc = le.fit_transform(y)

        estimator = self._build_estimator()
        cv = self._build_cv(y)

        # 交差検証で「全サンプル分」の予測を得る
        y_pred_enc = cross_val_predict(estimator, X, y_enc, cv=cv)
        y_true = le.inverse_transform(y_enc)
        y_pred = le.inverse_transform(y_pred_enc)

        acc = accuracy_score(y_true, y_pred)
        cm = confusion_matrix(y_true, y_pred, labels=le.classes_)
        report = classification_report(
            y_true, y_pred, labels=le.classes_, zero_division=0
        )

        out_dir.mkdir(parents=True, exist_ok=True)

        with open(out_dir / "report.txt", "w", encoding="utf-8") as f:
            f.write(f"classifier={self.config.classifier}, cv={self.config.cv_method}\n")
            f.write(f"Accuracy: {acc:.4f}\n\n")
            f.write(report)
            f.write("\n\n誤分類したサンプル一覧 (正解 -> 予測):\n")
            n_wrong = 0
            for t, p in zip(y_true, y_pred):
                if t != p:
                    f.write(f"  {t} -> {p}\n")
                    n_wrong += 1
            if n_wrong == 0:
                f.write("  (誤分類なし)\n")

        self._plot_confusion_matrix(cm, list(le.classes_), out_dir / "confusion_matrix.png")
        self._plot_pca(X, y_true, y_pred, out_dir / "pca_scatter.png")

        return f"Accuracy: {acc:.4f}\n\n{report}"

    @staticmethod
    def _plot_confusion_matrix(cm: np.ndarray, labels: List[str], save_path: Path) -> None:
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

    def _plot_pca(self, X: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray, save_path: Path) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        reducer = PCA(n_components=2, random_state=42)
        X_2d = reducer.fit_transform(X)

        classes = sorted(set(y_true.tolist()))
        fig, ax = plt.subplots(figsize=(7, 6))

        for c in classes:
            mask = y_true == c
            ax.scatter(X_2d[mask, 0], X_2d[mask, 1], label=str(c), alpha=0.7, s=40)

        if self.config.highlight_misclassified:
            wrong = y_true != y_pred
            if wrong.any():
                ax.scatter(
                    X_2d[wrong, 0],
                    X_2d[wrong, 1],
                    facecolors="none",
                    edgecolors="red",
                    s=150,
                    linewidths=1.8,
                    label="misclassified",
                )

        var_ratio = reducer.explained_variance_ratio_
        ax.set_xlabel(f"PC1 ({var_ratio[0] * 100:.1f}%)")
        ax.set_ylabel(f"PC2 ({var_ratio[1] * 100:.1f}%)")
        title = "PCA Projection of DINOv2 Features"
        if self.config.highlight_misclassified:
            title += "\n(red circle = misclassified)"
        ax.set_title(title)
        ax.legend(loc="best", fontsize=8)
        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)


def build_confusion_pca_evaluator(config: ConfusionPCAConfig) -> ConfusionPCAEvaluator:
    return ConfusionPCAEvaluator(config)
