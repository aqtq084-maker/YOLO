"""
シルエットスコア (Silhouette Score) 評価器 — 教師なし評価

シルエットスコアは、分類器を一切学習させずに、
特徴空間上での「クラスタ(=野菜の種類)のまとまりの良さ」を測る指標。

    各サンプル i について:
        a(i) = 同じクラス内の他サンプルとの平均距離   (凝集度: 小さいほど良い)
        b(i) = 最も近い「別クラス」との平均距離        (分離度: 大きいほど良い)
        s(i) = (b(i) - a(i)) / max(a(i), b(i))

    s(i) は -1〜1 の範囲を取り、
        +1に近い : 同じ野菜同士は近く、他の野菜とは離れている(理想的)
         0付近   : クラス境界上にあり紛らわしい
        -1に近い : 別の野菜のクラスタに紛れ込んでいる

線形プルーブやk-NNが「分類器を学習させた上での正解率」を測るのに対し、
シルエットスコアは分類器そのものを介さず、
「DINOv2の特徴空間上で、野菜ごとの写真がそもそもきれいに分かれているか」
を直接評価できるのが特徴。学習が要らないため、
1クラスあたりの写真枚数が少なくても計算できる。

拡張性のポイント:
    - 距離指標(metric)を切り替え可能 (cosine, euclidean など)
    - PCA散布図の出力有無を切替可能
    - 将来 Davies-Bouldin指数やCalinski-Harabasz指数など、
      他の教師なしクラスタ評価指標を追加したい場合も、
      同じ BaseEvaluator.evaluate(X, y, out_dir) を実装するだけで
      main.py側の変更なく追加できる。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
from sklearn.metrics import silhouette_samples, silhouette_score

from .base import BaseEvaluator


@dataclass
class SilhouetteConfig:
    metric: str = "cosine"
    # サンプル間距離の測り方。DINOv2特徴量はcosine類似度で比較されることが多いためcosineを既定に。
    # ユークリッド距離を試したい場合は "euclidean" を指定。

    make_pca_plot: bool = True
    # 特徴量をPCAで2次元に圧縮した散布図も保存するか。
    # シルエットスコアの数値だけでなく、視覚的にクラスの分かれ方を確認したい場合に有用。


class SilhouetteEvaluator(BaseEvaluator):
    def __init__(self, config: SilhouetteConfig):
        self.config = config

    def evaluate(self, X: np.ndarray, y: List[str], out_dir: Path) -> str:
        labels = np.asarray(y)
        classes = sorted(set(y))

        if len(classes) < 2:
            raise ValueError("シルエットスコアの計算には2クラス以上が必要です")
        if len(X) <= len(classes):
            raise ValueError("サンプル数がクラス数以下のため計算できません")

        overall_score = silhouette_score(X, labels, metric=self.config.metric)
        sample_scores = silhouette_samples(X, labels, metric=self.config.metric)

        per_class_scores = {
            c: float(sample_scores[labels == c].mean()) for c in classes
        }
        per_class_counts = {c: int((labels == c).sum()) for c in classes}

        out_dir.mkdir(parents=True, exist_ok=True)

        # --- レポート保存 ---
        report_lines = [
            f"metric={self.config.metric}",
            f"Overall Silhouette Score: {overall_score:.4f}",
            "",
            "クラスごとの平均シルエットスコア (高いほど、他の野菜と混同されにくい):",
        ]
        for c, s in sorted(per_class_scores.items(), key=lambda kv: -kv[1]):
            report_lines.append(f"  {c}: {s:.4f}  (n={per_class_counts[c]})")

        report_text = "\n".join(report_lines)
        with open(out_dir / "report.txt", "w", encoding="utf-8") as f:
            f.write(report_text)

        # --- 可視化 ---
        self._plot_silhouette(
            sample_scores, labels, classes, overall_score,
            out_dir / "silhouette_plot.png",
        )
        if self.config.make_pca_plot:
            self._plot_pca(X, labels, classes, out_dir / "pca_scatter.png")

        summary = (
            f"Overall Silhouette Score: {overall_score:.4f}\n\n"
            "クラスごとの平均シルエットスコア:\n"
            + "\n".join(
                f"  {c}: {s:.4f}  (n={per_class_counts[c]})"
                for c, s in sorted(per_class_scores.items(), key=lambda kv: -kv[1])
            )
        )
        return summary

    @staticmethod
    def _plot_silhouette(sample_scores, labels, classes, overall_score, save_path: Path) -> None:
        """クラスごとにサンプルのシルエット値を昇順で並べた古典的なシルエットプロット"""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.cm as cm
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, max(4, len(classes) * 1.2)))
        y_lower = 10
        colors = cm.get_cmap("tab10")(np.linspace(0, 1, len(classes)))

        for i, c in enumerate(classes):
            cluster_scores = np.sort(sample_scores[labels == c])
            size = len(cluster_scores)
            y_upper = y_lower + size
            ax.fill_betweenx(
                np.arange(y_lower, y_upper),
                0,
                cluster_scores,
                facecolor=colors[i],
                edgecolor=colors[i],
                alpha=0.8,
            )
            ax.text(-0.05, y_lower + 0.5 * size, str(c), ha="right", va="center", fontsize=9)
            y_lower = y_upper + 10

        ax.axvline(x=overall_score, color="red", linestyle="--", label=f"average: {overall_score:.3f}")
        ax.set_xlabel("Silhouette Score")
        ax.set_ylabel("Samples grouped by class")
        ax.set_yticks([])
        ax.set_title("Silhouette Plot")
        ax.legend(loc="best")
        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)

    @staticmethod
    def _plot_pca(X, labels, classes, save_path: Path) -> None:
        """特徴量を2次元PCAに圧縮し、クラスごとに色分けした散布図"""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.decomposition import PCA

        reducer = PCA(n_components=2, random_state=42)
        X_2d = reducer.fit_transform(X)

        fig, ax = plt.subplots(figsize=(7, 6))
        for c in classes:
            mask = labels == c
            ax.scatter(X_2d[mask, 0], X_2d[mask, 1], label=str(c), alpha=0.7, s=40)

        var_ratio = reducer.explained_variance_ratio_
        ax.set_xlabel(f"PC1 ({var_ratio[0] * 100:.1f}%)")
        ax.set_ylabel(f"PC2 ({var_ratio[1] * 100:.1f}%)")
        ax.set_title("PCA Projection of DINOv2 Features")
        ax.legend(loc="best", fontsize=8)
        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)


def build_silhouette_evaluator(config: SilhouetteConfig) -> SilhouetteEvaluator:
    return SilhouetteEvaluator(config)
