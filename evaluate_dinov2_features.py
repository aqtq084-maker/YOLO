"""
DINOv2特徴量の「精度」を評価するスクリプト
============================================================
run_dinov2_rtx5080.py で出力した features/カテゴリ名/xxx_cls.npy を読み込み、
カテゴリ別サブフォルダ名を疑似ラベルとして使い、以下の観点で特徴量の質を評価します。

DINOv2は自己教師あり学習のため「正解/不正解」という意味での精度はありません。
代わりに、「同じカテゴリの画像が特徴空間で近くに集まっているか」を
分類・クラスタリングの指標で定量化します。

■ 評価指標
--------------------------------------------------------------
1. k-NN分類 (層化K分割交差検証)
   → 近傍の画像が同じカテゴリかどうか。特徴量ベースの検索性能に直結。
2. 線形プローブ (ロジスティック回帰, 層化K分割交差検証)
   → 特徴が線形分離可能かどうか。DINOv2論文でも使われる標準的な評価方法。
3. シルエットスコア (教師なし)
   → ラベルを分類に使わず、クラスタとしてのまとまり具合を測る (-1〜1、高いほど良い)
4. クラス内 / クラス間 コサイン類似度
   → 同じカテゴリ同士がどれだけ似ていて、違うカテゴリとどれだけ離れているか
5. 混同行列・PCA散布図を画像として出力

■ 使い方
--------------------------------------------------------------
  # 基本 (features/ フォルダを評価)
  python evaluate_dinov2_features.py --features_dir features

  # 分割数やk-NNのkを変更
  python evaluate_dinov2_features.py --features_dir features --cv 5 --knn_k 3

  # パッチトークン(局所特徴量)を平均プーリングして評価したい場合
  python evaluate_dinov2_features.py --features_dir features --feature_type patch
"""

import argparse
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use("Agg")  # 画面なし環境でも画像保存できるように
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 日本語ラベルが文字化けしないよう、環境にあるCJKフォントを優先的に使う
for _font_name in ("Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "MS Gothic"):
    if any(_font_name in f.name for f in font_manager.fontManager.ttflist):
        matplotlib.rcParams["font.family"] = _font_name
        break
matplotlib.rcParams["axes.unicode_minus"] = False

from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    silhouette_score,
)
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity


def load_features(features_dir: Path, feature_type: str):
    """features/カテゴリ名/xxx_cls.npy (または _patch.npy) を読み込み、
    特徴ベクトルの配列とラベル配列、画像ファイル名一覧を返す。"""
    suffix = "_cls.npy" if feature_type == "cls" else "_patch.npy"
    paths = sorted(features_dir.rglob(f"*{suffix}"))

    if not paths:
        raise FileNotFoundError(
            f"{features_dir} 以下に *{suffix} が見つかりません。"
            f"run_dinov2_rtx5080.py の --output_dir を確認してください。"
        )

    X, y, names = [], [], []
    for p in paths:
        arr = np.load(p)  # cls: (1, hidden_dim) / patch: (1, num_patches, hidden_dim)
        if feature_type == "cls":
            vec = arr.reshape(-1)
        else:
            # パッチトークンは平均プーリングして画像全体の1本のベクトルにする
            vec = arr.reshape(-1, arr.shape[-1]).mean(axis=0)

        label = p.parent.name  # 親フォルダ名 = カテゴリ名 (例: だいこん)
        X.append(vec)
        y.append(label)
        names.append(p.stem.replace(suffix.replace(".npy", ""), ""))

    return np.array(X), np.array(y), names


def check_label_balance(y: np.ndarray):
    counts = Counter(y)
    print("\n[情報] カテゴリ別サンプル数:")
    for label, n in sorted(counts.items()):
        print(f"  {label}: {n}枚")

    min_count = min(counts.values())
    if min_count < 2:
        print("[警告] サンプル数が1枚しかないカテゴリがあります。交差検証には最低2枚以上必要です。")
    return min_count


def evaluate_knn(X, y, cv_splits, k):
    print(f"\n{'='*60}\n[評価1] k-NN分類 (k={k}, {cv_splits}分割交差検証)\n{'='*60}")
    skf = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    clf = KNeighborsClassifier(n_neighbors=k, metric="cosine")
    y_pred = cross_val_predict(clf, X, y, cv=skf)
    acc = accuracy_score(y, y_pred)
    print(f"全体の交差検証精度(Accuracy): {acc:.4f}")
    print("\nカテゴリ別レポート:")
    print(classification_report(y, y_pred, zero_division=0))
    return y_pred, acc


def evaluate_linear_probe(X, y, cv_splits):
    print(f"\n{'='*60}\n[評価2] 線形プローブ (ロジスティック回帰, {cv_splits}分割交差検証)\n{'='*60}")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    skf = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    clf = LogisticRegression(max_iter=2000)
    y_pred = cross_val_predict(clf, X_scaled, y, cv=skf)
    acc = accuracy_score(y, y_pred)
    print(f"全体の交差検証精度(Accuracy): {acc:.4f}")
    print("\nカテゴリ別レポート:")
    print(classification_report(y, y_pred, zero_division=0))
    return y_pred, acc


def evaluate_silhouette(X, y):
    print(f"\n{'='*60}\n[評価3] シルエットスコア (教師なしクラスタ品質)\n{'='*60}")
    if len(set(y)) < 2:
        print("カテゴリが1種類しかないため計算をスキップします。")
        return None
    score = silhouette_score(X, y, metric="cosine")
    print(f"シルエットスコア: {score:.4f}  (範囲: -1〜1、高いほどカテゴリ同士が分離できている)")
    return score


def evaluate_intra_inter_similarity(X, y):
    print(f"\n{'='*60}\n[評価4] クラス内 / クラス間 コサイン類似度\n{'='*60}")
    sim = cosine_similarity(X)
    labels = np.array(y)
    intra_sims, inter_sims = [], []

    n = len(labels)
    for i in range(n):
        for j in range(i + 1, n):
            if labels[i] == labels[j]:
                intra_sims.append(sim[i, j])
            else:
                inter_sims.append(sim[i, j])

    intra_mean = np.mean(intra_sims) if intra_sims else float("nan")
    inter_mean = np.mean(inter_sims) if inter_sims else float("nan")
    print(f"クラス内平均類似度(同じカテゴリ同士): {intra_mean:.4f}")
    print(f"クラス間平均類似度(違うカテゴリ同士): {inter_mean:.4f}")
    print(f"差分(大きいほど特徴量がカテゴリをよく分離できている): {intra_mean - inter_mean:.4f}")
    return intra_mean, inter_mean


def save_confusion_matrix(y_true, y_pred, labels, output_dir: Path, name: str):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.8), max(5, len(labels) * 0.8)))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
    disp.plot(ax=ax, xticks_rotation=45, cmap="Blues", colorbar=True)
    plt.title(f"混同行列 ({name})")
    plt.tight_layout()
    out_path = output_dir / f"confusion_matrix_{name}.png"
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[保存] {out_path}")


def save_pca_scatter(X, y, output_dir: Path):
    pca = PCA(n_components=2)
    X_2d = pca.fit_transform(X)
    labels = sorted(set(y))

    fig, ax = plt.subplots(figsize=(8, 6))
    cmap = plt.get_cmap("tab10")
    for i, label in enumerate(labels):
        mask = np.array(y) == label
        ax.scatter(X_2d[mask, 0], X_2d[mask, 1], label=label, color=cmap(i % 10), alpha=0.8, s=60)

    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    ax.set_title("DINOv2特徴量のPCA散布図 (カテゴリ別)")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    out_path = output_dir / "pca_scatter.png"
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[保存] {out_path}")


def main():
    parser = argparse.ArgumentParser(description="DINOv2特徴量の精度(分類性能・クラスタ品質)評価")
    parser.add_argument("--features_dir", type=str, default="features", help="特徴量(.npy)が入ったディレクトリ")
    parser.add_argument("--output_dir", type=str, default="eval_results", help="評価結果(画像等)の保存先")
    parser.add_argument("--feature_type", type=str, default="cls", choices=["cls", "patch"],
                         help="cls: CLSトークン(推奨) / patch: パッチトークンを平均プーリング")
    parser.add_argument("--cv", type=int, default=5, help="交差検証の分割数")
    parser.add_argument("--knn_k", type=int, default=5, help="k-NNの近傍数")
    args = parser.parse_args()

    features_dir = Path(args.features_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[情報] {features_dir} から特徴量を読み込み中 (feature_type={args.feature_type})...")
    X, y, names = load_features(features_dir, args.feature_type)
    print(f"[情報] 読み込み完了: {len(X)}枚, 次元数={X.shape[1]}")

    min_count = check_label_balance(y)
    cv_splits = min(args.cv, min_count) if min_count >= 2 else 2
    if cv_splits != args.cv:
        print(f"[警告] 最小カテゴリ数に合わせて交差検証の分割数を {cv_splits} に調整しました。")

    if min_count >= 2 and len(set(y)) >= 2:
        y_pred_knn, acc_knn = evaluate_knn(X, y, cv_splits, args.knn_k)
        y_pred_lin, acc_lin = evaluate_linear_probe(X, y, cv_splits)
        labels_sorted = sorted(set(y))
        save_confusion_matrix(y, y_pred_knn, labels_sorted, output_dir, "knn")
        save_confusion_matrix(y, y_pred_lin, labels_sorted, output_dir, "linear_probe")
    else:
        print("\n[警告] 分類評価にはカテゴリごとに最低2枚以上、かつ2カテゴリ以上が必要です。分類評価をスキップします。")
        acc_knn = acc_lin = None

    sil_score = evaluate_silhouette(X, y)
    intra_mean, inter_mean = evaluate_intra_inter_similarity(X, y)

    if len(X) >= 3:
        save_pca_scatter(X, y, output_dir)

    print(f"\n{'='*60}\n[まとめ]\n{'='*60}")
    print(f"サンプル数: {len(X)}枚 / カテゴリ数: {len(set(y))}")
    if acc_knn is not None:
        print(f"k-NN分類精度      : {acc_knn:.4f}")
        print(f"線形プローブ精度   : {acc_lin:.4f}")
    if sil_score is not None:
        print(f"シルエットスコア   : {sil_score:.4f}")
    print(f"クラス内類似度     : {intra_mean:.4f}")
    print(f"クラス間類似度     : {inter_mean:.4f}")
    print(f"\n結果画像は {output_dir} に保存しました。")


if __name__ == "__main__":
    main()