"""
DINOv2特徴量を使った野菜分類ツール (学習・テスト・実判定)
============================================================
run_dinov2_rtx5080.py で抽出した features/カテゴリ名/xxx_cls.npy を使って、
「本当に野菜を当てられるか」を2段階でテストします。

  [1] train_test モード
      手持ちの画像の特徴量を「学習用」「テスト用」にランダム分割し、
      学習用だけで分類器を訓練 → テスト用(モデルが見ていない画像)で
      正解率を測定します。これがモデルの素の実力です。
      その後、全データを使って「本番用モデル」を再学習し保存します。

  [2] predict モード
      [1]で保存した本番用モデルを使い、新しい画像(1枚 or フォルダ)を
      DINOv2で特徴抽出 → 分類器で「どの野菜か」を判定し、
      各カテゴリの確信度(確率)付きで表示します。

■ 使い方
--------------------------------------------------------------
  # (1) 学習+テストで正解率を確認し、本番用モデルを保存
  python classify_vegetables.py train_test --features_dir features --model_dir model

  # (2) 新しい1枚の画像を判定
  python classify_vegetables.py predict --model_dir model --image new_photo.jpg

  # (2') 新しい画像フォルダをまとめて判定(フォルダ名がカテゴリ名なら正解率も表示)
  python classify_vegetables.py predict --model_dir model --image_dir new_images_test
"""

import argparse
import pickle
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for _font_name in ("Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "MS Gothic"):
    if any(_font_name in f.name for f in font_manager.fontManager.ttflist):
        matplotlib.rcParams["font.family"] = _font_name
        break
matplotlib.rcParams["axes.unicode_minus"] = False

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)

MODEL_MAP = {
    "dinov2-small": "facebook/dinov2-small",
    "dinov2-base": "facebook/dinov2-base",
    "dinov2-large": "facebook/dinov2-large",
    "dinov2-giant": "facebook/dinov2-giant",
}


# ------------------------------------------------------------------
# 特徴量の読み込み(train_testモード用: 既に抽出済みの.npyを読む)
# ------------------------------------------------------------------
def load_features(features_dir: Path):
    paths = sorted(features_dir.rglob("*_cls.npy"))
    if not paths:
        raise FileNotFoundError(
            f"{features_dir} 以下に *_cls.npy が見つかりません。"
            f"run_dinov2_rtx5080.py で先に特徴量を抽出してください。"
        )
    X, y, names = [], [], []
    for p in paths:
        X.append(np.load(p).reshape(-1))
        y.append(p.parent.name)  # 親フォルダ名 = カテゴリ名
        names.append(p.stem.replace("_cls", ""))
    return np.array(X), np.array(y), names


def make_classifier(kind: str, knn_k: int):
    if kind == "knn":
        return KNeighborsClassifier(n_neighbors=knn_k, metric="cosine")
    return LogisticRegression(max_iter=2000)


# ------------------------------------------------------------------
# [1] train_test モード
# ------------------------------------------------------------------
def cmd_train_test(args):
    features_dir = Path(args.features_dir)
    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    X, y, names = load_features(features_dir)
    counts = Counter(y)
    print(f"[情報] 読み込み: {len(X)}枚 / {len(counts)}カテゴリ")
    for label, n in sorted(counts.items()):
        print(f"  {label}: {n}枚")

    min_count = min(counts.values())
    if min_count < 2:
        raise ValueError(
            "テスト分割を行うには、各カテゴリに最低2枚以上の画像が必要です。"
            f"(現在最少カテゴリ: {min_count}枚)"
        )

    # 学習用/テスト用に分割(カテゴリの比率を保ったまま分割 = stratify)
    X_train, X_test, y_train, y_test, names_train, names_test = train_test_split(
        X, y, names,
        test_size=args.test_size,
        stratify=y,
        random_state=42,
    )
    print(f"\n[情報] 学習用 {len(X_train)}枚 / テスト用(未知データ扱い) {len(X_test)}枚 に分割しました")

    # --- 学習用データだけで分類器を訓練 ---
    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_test_s = scaler.transform(X_test)

    clf = make_classifier(args.classifier, args.knn_k)
    clf.fit(X_train_s, y_train)

    # --- テスト用データ(学習時に見ていない画像)で正解率を測定 ---
    y_pred = clf.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)

    print(f"\n{'='*60}\n[テスト結果] 未知画像に対する正解率\n{'='*60}")
    print(f"正解率(Accuracy): {acc:.4f}  ({int(acc*len(y_test))}/{len(y_test)}枚 正解)")
    print("\nカテゴリ別レポート:")
    print(classification_report(y_test, y_pred, zero_division=0))

    print("画像ごとの判定結果:")
    for name, true_label, pred_label in zip(names_test, y_test, y_pred):
        mark = "OK" if true_label == pred_label else "NG"
        print(f"  [{mark}] {name}: 正解={true_label} / 予測={pred_label}")

    labels_sorted = sorted(set(y))
    cm = confusion_matrix(y_test, y_pred, labels=labels_sorted)
    fig, ax = plt.subplots(figsize=(max(6, len(labels_sorted) * 0.8), max(5, len(labels_sorted) * 0.8)))
    ConfusionMatrixDisplay(cm, display_labels=labels_sorted).plot(ax=ax, cmap="Blues", xticks_rotation=45)
    plt.title(f"テストデータでの混同行列 (正解率={acc:.2%})")
    plt.tight_layout()
    cm_path = model_dir / "test_confusion_matrix.png"
    plt.savefig(cm_path, dpi=150)
    plt.close(fig)
    print(f"\n[保存] {cm_path}")

    # --- 本番用モデル: 全データ(学習+テスト)で再学習して保存 ---
    scaler_final = StandardScaler().fit(X)
    X_all_s = scaler_final.transform(X)
    clf_final = make_classifier(args.classifier, args.knn_k)
    clf_final.fit(X_all_s, y)

    bundle = {
        "classifier": clf_final,
        "scaler": scaler_final,
        "labels": sorted(set(y)),
        "classifier_kind": args.classifier,
        "knn_k": args.knn_k,
        "dino_model": args.dino_model,
        "test_accuracy": acc,  # 参考値として、分割テストでの正解率も保存
    }
    model_path = model_dir / "classifier.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(bundle, f)

    print(f"\n{'='*60}\n[まとめ]\n{'='*60}")
    print(f"未知画像に対する推定正解率: {acc:.2%} (テスト分割 {len(X_test)}枚での結果)")
    print(f"本番用モデルを保存しました: {model_path}")
    print("この本番用モデルは全データで再学習済みのため、上記の正解率よりわずかに")
    print("実力が高いか同等と考えられます(データが多いほど分類器は強くなるため)。")
    print(f"\n新しい画像を判定するには:")
    print(f"  python {Path(__file__).name} predict --model_dir {model_dir} --image path/to/photo.jpg")


# ------------------------------------------------------------------
# [2] predict モード (新しい画像に対してDINOv2特徴抽出→分類)
# ------------------------------------------------------------------
def load_dino(model_name: str):
    import torch
    from transformers import AutoImageProcessor, AutoModel

    if torch.cuda.is_available():
        device = torch.device("cuda:0")
        print(f"[情報] 使用GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        print("[警告] CUDAが利用できません。CPUで実行します(低速)。")

    hf_name = MODEL_MAP[model_name]
    print(f"[情報] モデルをロード中: {hf_name}")
    processor = AutoImageProcessor.from_pretrained(hf_name)
    model = AutoModel.from_pretrained(hf_name)
    model.eval().to(device)
    if device.type == "cuda":
        model = model.to(dtype=torch.bfloat16)
    return processor, model, device


def extract_cls_feature(image_path: Path, processor, model, device):
    import torch
    from PIL import Image

    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)
    if device.type == "cuda":
        inputs = {k: v.to(dtype=torch.bfloat16) if v.dtype.is_floating_point else v
                   for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    cls_token = outputs.last_hidden_state[:, 0, :]
    return cls_token.float().cpu().numpy().reshape(-1)


def predict_one(feat, bundle):
    """1枚の特徴ベクトルからカテゴリを予測し、確信度付きの候補一覧を返す"""
    clf = bundle["classifier"]
    scaler = bundle["scaler"]
    labels = bundle["labels"]

    feat_s = scaler.transform(feat.reshape(1, -1))

    if hasattr(clf, "predict_proba"):
        proba = clf.predict_proba(feat_s)[0]
    else:
        # k-NNなど predict_proba が無い/信頼性が低い場合は近傍距離から簡易スコアを作る
        proba = clf.predict_proba(feat_s)[0] if hasattr(clf, "predict_proba") else None

    order = np.argsort(proba)[::-1]
    ranking = [(clf.classes_[i], proba[i]) for i in order]
    pred_label = ranking[0][0]
    return pred_label, ranking


def cmd_predict(args):
    model_path = Path(args.model_dir) / "classifier.pkl"
    if not model_path.exists():
        raise FileNotFoundError(
            f"{model_path} が見つかりません。先に train_test モードでモデルを学習・保存してください。"
        )
    with open(model_path, "rb") as f:
        bundle = pickle.load(f)

    dino_model_name = args.dino_model or bundle["dino_model"]
    processor, model, device = load_dino(dino_model_name)

    if args.image:
        targets = [(Path(args.image), None)]
    elif args.image_dir:
        image_dir = Path(args.image_dir)
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
        paths = sorted(p for p in image_dir.rglob("*") if p.suffix.lower() in exts)
        # サブフォルダ名があれば正解ラベルとして扱う(精度確認用)
        targets = [(p, p.parent.name if p.parent != image_dir else None) for p in paths]
    else:
        raise ValueError("--image か --image_dir のいずれかを指定してください")

    print(f"\n{'='*60}\n[判定結果]\n{'='*60}")
    correct, total_with_label = 0, 0
    for path, true_label in targets:
        feat = extract_cls_feature(path, processor, model, device)
        pred_label, ranking = predict_one(feat, bundle)

        top3 = ", ".join(f"{label}:{prob:.1%}" for label, prob in ranking[:3])
        print(f"\n{path.name}")
        print(f"  → 判定: {pred_label}  (候補: {top3})")

        if true_label is not None and true_label in bundle["labels"]:
            total_with_label += 1
            mark = "正解" if true_label == pred_label else "不正解"
            if true_label == pred_label:
                correct += 1
            print(f"  (フォルダ名からの正解ラベル: {true_label} → {mark})")

    if total_with_label > 0:
        print(f"\n{'='*60}")
        print(f"[まとめ] フォルダ名を正解ラベルとみなした場合の正解率: "
              f"{correct}/{total_with_label} = {correct/total_with_label:.2%}")


def main():
    parser = argparse.ArgumentParser(description="DINOv2特徴量による野菜分類(学習・テスト・実判定)")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_tt = sub.add_parser("train_test", help="学習/テスト分割で正解率を測定し、本番用モデルを保存")
    p_tt.add_argument("--features_dir", type=str, default="features")
    p_tt.add_argument("--model_dir", type=str, default="model")
    p_tt.add_argument("--test_size", type=float, default=0.3, help="テスト用に回す割合(0〜1)")
    p_tt.add_argument("--classifier", type=str, default="logreg", choices=["logreg", "knn"])
    p_tt.add_argument("--knn_k", type=int, default=5)
    p_tt.add_argument("--dino_model", type=str, default="dinov2-base", choices=list(MODEL_MAP.keys()),
                       help="predictモードで新規画像の特徴抽出に使うDINOv2モデル(学習時の特徴量と揃える)")

    p_pred = sub.add_parser("predict", help="新しい画像を判定")
    p_pred.add_argument("--model_dir", type=str, default="model")
    p_pred.add_argument("--image", type=str, default=None)
    p_pred.add_argument("--image_dir", type=str, default=None)
    p_pred.add_argument("--dino_model", type=str, default=None, choices=list(MODEL_MAP.keys()),
                         help="省略時は学習時に使ったモデルを自動的に使用")

    args = parser.parse_args()
    if args.mode == "train_test":
        cmd_train_test(args)
    else:
        cmd_predict(args)


if __name__ == "__main__":
    main()