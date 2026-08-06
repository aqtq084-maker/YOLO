"""
DINOv2で抽出した特徴量(.npy)を使って、分類精度を評価するスクリプト

■ 前提
--------------------------------------------------------------
DINOv2自体は「特徴抽出モデル」であり、それ単体には分類精度(Accuracy)という
概念がありません。そのため本スクリプトでは、抽出した特徴量に簡単な分類器
(k近傍法 / ロジスティック回帰)を組み合わせ、交差検証(Cross Validation)で
「その特徴量がどれくらいクラス(だいこん/かぼちゃ等)を正しく区別できるか」
を評価します。

■ ラベルの取得方法
--------------------------------------------------------------
crop_yolo_annotations.py で出力したクロップ画像は
  1_000_cls0.jpg   (元画像1, ボックス0番目, クラスID=0)
のような名前になっており、run_dinov2_rtx5080.py はこのファイル名をもとに
  1_000_cls0_cls.npy    (CLSトークン特徴量)
  1_000_cls0_patch.npy  (パッチ特徴量)
を出力します。本スクリプトは "_cls.npy" で終わるファイルのみを対象にし、
ファイル名末尾の "clsN" 部分をクラスラベルとして自動抽出します。

■ 使い方
--------------------------------------------------------------
  # 基本(features フォルダ以下の *_cls.npy を対象に5分割交差検証)
  python evaluate_dinov2_classification.py --features_dir features

  # クラスIDに名前を対応付けたい場合
  python evaluate_dinov2_classification.py --features_dir features \
      --class_names "0:だいこん,1:かぼちゃ"

  # 分類器やfold数を変更したい場合
  python evaluate_dinov2_classification.py --features_dir features \
      --classifier knn --k_neighbors 3 --cv_folds 5

  # 混同行列を画像として保存したい場合
  python evaluate_dinov2_classification.py --features_dir features \
      --confusion_matrix_out confusion_matrix.png

依存パッケージ:
  pip install numpy scikit-learn matplotlib
"""

import argparse
import re
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# ファイル名末尾から "clsN" を抜き出す正規表現
# 例: "1_000_cls0_cls.npy" -> "cls0" の部分を検出してクラスID=0を取得
CLASS_ID_PATTERN = re.compile(r"_cls(\d+)_cls\.npy$")


def parse_class_id(filename: str):
    """ファイル名からクラスIDを抽出する。見つからない場合はNoneを返す"""
    match = CLASS_ID_PATTERN.search(filename)
    if match is None:
        return None
    return int(match.group(1))


def load_features(features_dir: str):
    """features_dir以下を再帰的に探索し、CLSトークン特徴量とラベルを読み込む"""
    features_dir = Path(features_dir)
    npy_files = sorted(features_dir.rglob("*_cls.npy"))

    X, y, paths = [], [], []
    skipped = 0
    for path in npy_files:
        class_id = parse_class_id(path.name)
        if class_id is None:
            skipped += 1
            continue
        vec = np.load(path).flatten()
        X.append(vec)
        y.append(class_id)
        paths.append(path)

    if skipped > 0:
        print(f"[警告] ファイル名からクラスIDを抽出できず、{skipped}件をスキップしました")
        print("       (対象は run_dinov2_rtx5080.py が出力した '*_clsN_cls.npy' 形式のファイルです)")

    if not X:
        raise ValueError(
            f"{features_dir} 以下に評価可能な特徴量ファイルが見つかりませんでした。"
            " crop_yolo_annotations.py → run_dinov2_rtx5080.py の順に実行済みか確認してください。"
        )

    return np.stack(X), np.array(y), paths


def parse_class_names(spec: str):
    """'0:だいこん,1:かぼちゃ' のような文字列を {0: 'だいこん', 1: 'かぼちゃ'} に変換"""
    if not spec:
        return {}
    mapping = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        cid_str, name = part.split(":", 1)
        mapping[int(cid_str.strip())] = name.strip()
    return mapping


def build_classifier(name: str, k_neighbors: int, knn_metric: str):
    if name == "knn":
        return KNeighborsClassifier(n_neighbors=k_neighbors, metric=knn_metric)
    if name == "logreg":
        return LogisticRegression(max_iter=2000)
    raise ValueError(f"未対応の分類器です: {name}")


def evaluate(X, y, classifier_name: str, k_neighbors: int, knn_metric: str, cv_folds: int, class_names: dict):
    label_names = [class_names.get(cid, str(cid)) for cid in sorted(set(y))]

    # クラスごとのサンプル数が cv_folds 未満だと層化分割できないため調整
    min_class_count = min(np.bincount(y))
    effective_folds = min(cv_folds, min_class_count)
    if effective_folds < cv_folds:
        print(f"[警告] 最少クラスのサンプル数({min_class_count})に合わせて "
              f"分割数を {cv_folds} → {effective_folds} に変更しました")
    if effective_folds < 2:
        raise ValueError(
            "交差検証を行うには、各クラスに最低2枚以上の画像が必要です。"
            " データ数を増やすか、--cv_folds を調整してください。"
        )

    clf = build_classifier(classifier_name, k_neighbors, knn_metric)
    skf = StratifiedKFold(n_splits=effective_folds, shuffle=True, random_state=42)

    scores = cross_val_score(clf, X, y, cv=skf)
    y_pred = cross_val_predict(clf, X, y, cv=skf)

    print("\n=== 評価結果 ===")
    print(f"分類器: {classifier_name}" + (f" (k={k_neighbors}, metric={knn_metric})" if classifier_name == "knn" else ""))
    print(f"交差検証 fold数: {effective_folds}")
    print(f"サンプル数: {len(y)} 件 / クラス数: {len(set(y))}")
    print(f"各foldの正解率: {np.round(scores, 4)}")
    print(f"平均正解率(Accuracy): {scores.mean():.4f} (±{scores.std():.4f})")

    print("\n=== クラスごとの詳細(適合率 / 再現率 / F1) ===")
    print(classification_report(y, y_pred, target_names=label_names, zero_division=0))

    cm = confusion_matrix(y, y_pred)
    print("=== 混同行列 (行=正解, 列=予測) ===")
    header = "        " + " ".join(f"{n:>8}" for n in label_names)
    print(header)
    for name, row in zip(label_names, cm):
        print(f"{name:>8}" + " ".join(f"{v:>8}" for v in row))

    return cm, label_names


def save_confusion_matrix_plot(cm, label_names, out_path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 日本語ラベルが文字化け(豆腐文字)しないよう、利用可能な日本語フォントを探して設定する。
    # 見つからない場合はデフォルトフォントのまま続行する(ラベルが四角になる可能性あり)。
    candidate_fonts = ["Noto Sans CJK JP", "IPAexGothic", "TakaoGothic", "Yu Gothic", "MS Gothic"]
    available = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
    for font_name in candidate_fonts:
        if font_name in available:
            plt.rcParams["font.family"] = font_name
            break
    else:
        print("[警告] 日本語対応フォントが見つかりませんでした。混同行列のラベルが文字化けする場合は"
              " 'sudo apt install fonts-noto-cjk' 等で日本語フォントを導入してください。")

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(label_names)))
    ax.set_yticks(range(len(label_names)))
    ax.set_xticklabels(label_names, rotation=45, ha="right")
    ax.set_yticklabels(label_names)
    ax.set_xlabel("予測クラス")
    ax.set_ylabel("正解クラス")
    ax.set_title("混同行列 (Confusion Matrix)")

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black")

    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"\n混同行列を画像として保存しました: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="DINOv2特徴量を用いた分類精度評価")
    parser.add_argument("--features_dir", default="features",
                         help="run_dinov2_rtx5080.py の出力先フォルダ。デフォルト: features")
    parser.add_argument("--classifier", choices=["knn", "logreg"], default="knn",
                         help="評価に使う分類器。デフォルト: knn")
    parser.add_argument("--k_neighbors", type=int, default=5,
                         help="--classifier knn の場合の近傍数。デフォルト: 5")
    parser.add_argument("--knn_metric", choices=["cosine", "euclidean"], default="cosine",
                         help="--classifier knn の場合の距離指標。デフォルト: cosine"
                              "(DINOv2特徴量はcosineが一般的ですが、うまく分かれない場合はeuclideanも試してください)")
    parser.add_argument("--cv_folds", type=int, default=5,
                         help="交差検証の分割数。デフォルト: 5")
    parser.add_argument("--class_names", type=str, default=None,
                         help="クラスIDと名前の対応。例: '0:だいこん,1:かぼちゃ'")
    parser.add_argument("--confusion_matrix_out", type=str, default=None,
                         help="混同行列を画像として保存するパス(省略時は保存しない)")
    args = parser.parse_args()

    class_names = parse_class_names(args.class_names)

    print(f"[情報] 特徴量を読み込み中: {args.features_dir}")
    X, y, paths = load_features(args.features_dir)
    print(f"[情報] {len(y)} 件の特徴量を読み込みました (次元数: {X.shape[1]})")

    cm, label_names = evaluate(
        X, y,
        classifier_name=args.classifier,
        k_neighbors=args.k_neighbors,
        knn_metric=args.knn_metric,
        cv_folds=args.cv_folds,
        class_names=class_names,
    )

    if args.confusion_matrix_out:
        save_confusion_matrix_plot(cm, label_names, args.confusion_matrix_out)


if __name__ == "__main__":
    main()