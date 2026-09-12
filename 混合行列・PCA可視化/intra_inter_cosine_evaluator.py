"""
クラス内・クラス間 コサイン類似度 評価器 — 教師なし評価

分類器を一切学習させずに、DINOv2特徴空間上で
「同じ野菜同士がどれだけ似ているか(クラス内類似度)」と
「異なる野菜同士がどれだけ似ていないか(クラス間類似度)」を
直接測定する評価指標。

    クラス内類似度 (intra-class similarity):
        同じ野菜のサンプル同士のコサイン類似度の平均。
        1に近いほど、同じ野菜の写真はどれも似た特徴を持つ(理想的)。

    クラス間類似度 (inter-class similarity):
        異なる野菜のサンプル同士のコサイン類似度の平均。
        低い値に近いほど、違う野菜どうしがきちんと区別できている(理想的)。

    分離マージン (margin) = クラス内類似度 - クラス間類似度
        大きいほど「同じ野菜は似ていて、違う野菜とは似ていない」
        = 特徴量として良い性質を持つことを意味する。

シルエットスコアが「最も近い別クラスとの距離」だけを見るのに対し、
こちらは「すべてのクラスペアとの類似度」を網羅的に算出・可視化するため、
「どの野菜とどの野菜が特に混同されやすいか」をピンポイントで特定しやすい。

拡張性のポイント:
    - 距離指標は現状コサイン類似度に固定しているが、将来ユークリッド距離
      ベースの同種の指標(クラス内平均距離/クラス間平均距離)を追加したい
      場合は、同じBaseEvaluatorインターフェースで新しいファイルを
      追加すればよい。
    - サンプル数が非常に多い場合の計算量に配慮し、必要なら将来的に
      サブサンプリングオプション(max_samples_per_class等)を
      追加できるようConfigをdataclassにしてある。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .base import BaseEvaluator


@dataclass
class IntraInterCosineConfig:
    make_heatmap: bool = True
    # クラス×クラスの類似度行列をヒートマップとして保存するか
    # (対角=クラス内類似度, 非対角=クラス間類似度)

    top_k_confusable_pairs: int = 5
    # レポートに「特に類似度が高く混同されやすいクラスペア」を
    # 何件表示するか


class IntraInterCosineEvaluator(BaseEvaluator):
    def __init__(self, config: IntraInterCosineConfig):
        self.config = config

    def evaluate(self, X: np.ndarray, y: List[str], out_dir: Path) -> str:
        labels = np.asarray(y)
        classes = sorted(set(y))

        if len(classes) < 2:
            raise ValueError("クラス内・クラス間比較には2クラス以上が必要です")

        # (n, n) の全ペアコサイン類似度行列を一度だけ計算し、使い回す
        sim_matrix = cosine_similarity(X)

        intra_scores: Dict[str, float] = {}
        for c in classes:
            idx = np.where(labels == c)[0]
            if len(idx) < 2:
                # サンプルが1枚しかないクラスは「クラス内」の比較対象がない
                intra_scores[c] = float("nan")
                continue
            sub = sim_matrix[np.ix_(idx, idx)]
            n = len(idx)
            # 対角成分(自分自身との類似度=1.0)を除いた平均
            off_diag_sum = sub.sum() - np.trace(sub)
            intra_scores[c] = float(off_diag_sum / (n * (n - 1)))

        inter_scores: Dict[Tuple[str, str], float] = {}
        for i, c1 in enumerate(classes):
            idx1 = np.where(labels == c1)[0]
            for c2 in classes[i + 1:]:
                idx2 = np.where(labels == c2)[0]
                sub = sim_matrix[np.ix_(idx1, idx2)]
                inter_scores[(c1, c2)] = float(sub.mean())

        # クラス x クラス 行列を構築 (対角=クラス内類似度, 非対角=クラス間類似度)
        class_matrix = np.zeros((len(classes), len(classes)))
        for i, c in enumerate(classes):
            class_matrix[i, i] = intra_scores[c]
        for (c1, c2), v in inter_scores.items():
            i, j = classes.index(c1), classes.index(c2)
            class_matrix[i, j] = v
            class_matrix[j, i] = v

        valid_intra = [v for v in intra_scores.values() if not np.isnan(v)]
        overall_intra = float(np.mean(valid_intra)) if valid_intra else float("nan")
        overall_inter = float(np.mean(list(inter_scores.values()))) if inter_scores else float("nan")
        margin = overall_intra - overall_inter

        # クラスごとのマージン: (自分のクラス内類似度) - (他クラスとの平均類似度)
        # マージンが小さい/負のクラスほど、他の野菜と混同されやすい可能性が高い
        per_class_margin: Dict[str, float] = {}
        for c in classes:
            other_inter = [v for (c1, c2), v in inter_scores.items() if c in (c1, c2)]
            mean_other = float(np.mean(other_inter)) if other_inter else float("nan")
            per_class_margin[c] = intra_scores[c] - mean_other

        out_dir.mkdir(parents=True, exist_ok=True)

        # --- レポート ---
        lines = [
            f"Overall Intra-class Similarity (avg): {overall_intra:.4f}",
            f"Overall Inter-class Similarity (avg): {overall_inter:.4f}",
            f"Separation Margin (intra - inter): {margin:.4f}",
            "",
            "クラスごとのクラス内類似度・マージン (マージンが大きいほど他の野菜と混同されにくい):",
        ]
        for c, m in sorted(per_class_margin.items(), key=lambda kv: -kv[1]):
            lines.append(f"  {c}: intra={intra_scores[c]:.4f}, margin={m:.4f}")

        lines.append("")
        k = self.config.top_k_confusable_pairs
        lines.append(f"特に類似度が高い(=混同しやすい可能性のある)クラスペア Top{k}:")
        for (c1, c2), v in sorted(inter_scores.items(), key=lambda kv: -kv[1])[:k]:
            lines.append(f"  {c1} - {c2}: {v:.4f}")

        report_text = "\n".join(lines)
        with open(out_dir / "report.txt", "w", encoding="utf-8") as f:
            f.write(report_text)

        if self.config.make_heatmap:
            self._plot_heatmap(class_matrix, classes, out_dir / "cosine_heatmap.png")

        return report_text

    @staticmethod
    def _plot_heatmap(matrix: np.ndarray, classes: List[str], save_path: Path) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        n = len(classes)
        fig, ax = plt.subplots(figsize=(max(6, n * 0.8), max(5, n * 0.8)))
        im = ax.imshow(matrix, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(classes, rotation=45, ha="right")
        ax.set_yticklabels(classes)
        ax.set_title(
            "Intra/Inter-class Cosine Similarity\n"
            "(diagonal = intra-class, off-diagonal = inter-class)"
        )

        for i in range(n):
            for j in range(n):
                val = matrix[i, j]
                ax.text(
                    j,
                    i,
                    f"{val:.2f}",
                    ha="center",
                    va="center",
                    color="white" if abs(val) > 0.5 else "black",
                    fontweight="bold" if i == j else "normal",
                )

        fig.colorbar(im, ax=ax, label="Cosine Similarity")
        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)


def build_intra_inter_cosine_evaluator(
    config: IntraInterCosineConfig,
) -> IntraInterCosineEvaluator:
    return IntraInterCosineEvaluator(config)
