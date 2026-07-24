"""リネーム機能のロジック本体。

「計画を立てる(build_*_plan)」と「実行する(execute_*_plan)」を分離してある。
build 系はファイルシステムに一切書き込まない。実行系だけが copy/move する。
CLI (rename_new_images.py / merge_to_dataset.py) や将来の Streamlit UI はここを呼ぶだけ。
"""
import os
import re
import random
import shutil
from datetime import datetime

# ==========================================
# パス定数（rename_app フォルダ基準）
# ==========================================
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)  # リポジトリのルート（yolo フォルダ）
STAGING_DIR = os.path.join(APP_DIR, "data_staging")

NEW_DIR = os.path.join(STAGING_DIR, "1_new")                             # パターン1: 自分で集めた画像
RECEIVED_IMAGES_DIR = os.path.join(STAGING_DIR, "received", "images")    # パターン2: 届いた画像
RECEIVED_LABELS_DIR = os.path.join(STAGING_DIR, "received", "labels")    # パターン2: 届いたtxt
RENAMED_DIR = os.path.join(STAGING_DIR, "2_renamed")   # 出力先（画像）
LABELS_DIR = os.path.join(STAGING_DIR, "3_labels")     # 出力先（txt）
DATASETS_ROOT = os.path.join(ROOT_DIR, "datasets")  # 野菜ごとのデータセット置き場（ルート直下）
DEFAULT_VEG_NAME = "daikon"

TRAIN_RATIO = 0.8   # train:val = 8:2
IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".webp"]
PROCESSED_DIR_NAME = "processed"  # リネーム済みの元ファイルの退避先（入力フォルダの中に作る）
LOG_FILE = os.path.join(STAGING_DIR, "rename_log.txt")


# ==========================================
# 共通ヘルパー
# ==========================================
def default_dataset_dir(veg_name):
    """野菜名から取り込み先データセットフォルダ（datasets/<野菜名>）を導出する"""
    return os.path.join(DATASETS_ROOT, veg_name)


def scan_max_numbers(veg_name, dirs):
    """既存の {野菜名}_{train|val}_{番号} を走査して split ごとの最大番号を返す"""
    pat = re.compile(rf"^{re.escape(veg_name)}_(train|val)_(\d+)$")
    max_num = {"train": 0, "val": 0}
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            stem, _ = os.path.splitext(fname)
            m = pat.match(stem)
            if m:
                split, num = m.group(1), int(m.group(2))
                if num > max_num[split]:
                    max_num[split] = num
    return max_num


def unique_path(directory, fname):
    """同名ファイルがあれば (2), (3)... を付けて衝突しない移動先を返す"""
    target = os.path.join(directory, fname)
    if not os.path.exists(target):
        return target
    stem, ext = os.path.splitext(fname)
    n = 2
    while os.path.exists(os.path.join(directory, f"{stem} ({n}){ext}")):
        n += 1
    return os.path.join(directory, f"{stem} ({n}){ext}")


def list_files(directory, exts):
    """指定拡張子のファイル一覧と、それ以外（無視分）を返す"""
    hits, ignored = [], []
    for fname in sorted(os.listdir(directory)):
        if not os.path.isfile(os.path.join(directory, fname)):
            continue  # processed/ などのフォルダは無視
        if os.path.splitext(fname)[1].lower() in exts:
            hits.append(fname)
        else:
            ignored.append(fname)
    return hits, ignored


def _append_log(log_file, lines):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _pair_by_stem(images, txts, result):
    """画像と txt を stem（拡張子を除いた名前）でペアリングして検証する。

    完全にペアになっていれば [(元画像名, 元txt名), ...] を stem 名前順で返す。
    片方でも欠けていれば result["problems"] に追記して None を返す。
    """
    img_by_stem = {os.path.splitext(f)[0]: f for f in images}
    txt_by_stem = {os.path.splitext(f)[0]: f for f in txts}
    for stem, img in img_by_stem.items():
        if stem not in txt_by_stem:
            result["problems"].append(
                f"txt がありません: {img} に対応する {stem}.txt が見つかりません")
    for stem, txt in txt_by_stem.items():
        if stem not in img_by_stem:
            result["problems"].append(
                f"画像がありません: {txt} に対応する画像が見つかりません")
    if result["problems"]:
        return None
    return [(img, txt_by_stem[stem]) for stem, img in sorted(img_by_stem.items())]


def _assign_split_numbers(items, veg_name, scan_dirs):
    """items を train/val へ 8:2 で振り分け、既存の続き番号で採番する計画を作る。

    items: [(元画像名, 元txt名 or None), ...]（元の順序を保持）
    scan_dirs: 既存の最大番号を調べるフォルダ群（データセット + staging）
    戻り値: (assignments, max_num, n_train)
      assignments = [(元画像名, 元txt名, split, 新stem), ...]（items と同じ順序）
      新stem は "{veg_name}_{split}_{番号3桁}"（拡張子なし）
    """
    max_num = scan_max_numbers(veg_name, scan_dirs)
    n_train = round(len(items) * TRAIN_RATIO)
    shuffled = items[:]
    random.shuffle(shuffled)
    train_set = {img for img, _ in shuffled[:n_train]}

    counters = {"train": max_num["train"], "val": max_num["val"]}
    assignments = []
    for img, txt in items:
        split = "train" if img in train_set else "val"
        counters[split] += 1
        new_stem = f"{veg_name}_{split}_{counters[split]:03d}"
        assignments.append((img, txt, split, new_stem))
    return assignments, max_num, n_train


# ==========================================
# 新規データのリネーム（続き番号 + train/val 振り分け）
# ==========================================
def build_rename_plan(mode, img_in_dir, lbl_in_dir, dataset_dir, veg_name,
                      out_images_dir=None, out_labels_dir=None):
    """リネーム計画を立てる。ファイルには一切書き込まない。

    mode: "1"（画像のみ） or "2"（画像 + txt のペア）
    戻り値 dict:
      problems : 実行を止める問題（空なら実行可。1件でもあれば plan は空にする）
      ignored  : 無視した対象外ファイル名のリスト
      plan     : [(元画像名, 元txt名 or None, 新画像名, 新txt名 or None), ...]
      n_train / n_val : 振り分け数
      max_num  : 既存の最大番号 {"train": int, "val": int}
    """
    out_images_dir = out_images_dir or RENAMED_DIR
    out_labels_dir = out_labels_dir or LABELS_DIR
    result = {"problems": [], "ignored": [], "plan": [],
              "n_train": 0, "n_val": 0, "max_num": {"train": 0, "val": 0}}

    if not os.path.isdir(img_in_dir):
        result["problems"].append(f"画像フォルダがありません: {img_in_dir}")
        return result
    if mode == "2" and (lbl_in_dir is None or not os.path.isdir(lbl_in_dir)):
        result["problems"].append(f"txt フォルダがありません: {lbl_in_dir}")
        return result

    images, ignored = list_files(img_in_dir, IMAGE_EXTS)
    result["ignored"].extend(ignored)

    if mode == "1":
        items = [(img, None) for img in images]
    else:
        txts, ignored_l = list_files(lbl_in_dir, [".txt"])
        result["ignored"].extend(ignored_l)
        items = _pair_by_stem(images, txts, result)
        if items is None:
            return result

    if not items:
        result["problems"].append("リネームする新しいファイルがありません。")
        return result

    # 既存の番号を調べて続きから採番（データセット + 未取り込みの staging 分）
    scan_dirs = [
        os.path.join(dataset_dir, "train", "images"),
        os.path.join(dataset_dir, "train", "labels"),
        os.path.join(dataset_dir, "val", "images"),
        os.path.join(dataset_dir, "val", "labels"),
        out_images_dir,
        out_labels_dir,
    ]
    assignments, max_num, n_train = _assign_split_numbers(items, veg_name, scan_dirs)
    result["max_num"] = max_num

    for img, txt, split, new_stem in assignments:
        ext = os.path.splitext(img)[1].lower()
        result["plan"].append(
            (img, txt, new_stem + ext, new_stem + ".txt" if txt else None))

    # 出力先との衝突チェック（念のため）
    for _, _, new_img, new_txt in result["plan"]:
        if os.path.exists(os.path.join(out_images_dir, new_img)):
            result["problems"].append(f"出力先に既に存在: {new_img}")
        if new_txt and os.path.exists(os.path.join(out_labels_dir, new_txt)):
            result["problems"].append(f"出力先に既に存在: {new_txt}")
    if result["problems"]:
        result["plan"] = []
        return result

    result["n_train"] = n_train
    result["n_val"] = len(result["plan"]) - n_train
    return result


def execute_rename_plan(plan, mode, img_in_dir, lbl_in_dir,
                        out_images_dir=None, out_labels_dir=None, log_file=None):
    """リネーム計画を実行する。

    画像（と txt）を新しい名前で出力先へコピーし、元ファイルは入力フォルダ内の
    processed/ へ退避（二重リネーム防止）、ログに追記する。
    戻り値: 実行内容の文字列リスト（1件1行、CLI がそのまま表示できる形式）
    """
    out_images_dir = out_images_dir or RENAMED_DIR
    out_labels_dir = out_labels_dir or LABELS_DIR
    log_file = log_file or LOG_FILE

    os.makedirs(out_images_dir, exist_ok=True)
    img_done_dir = os.path.join(img_in_dir, PROCESSED_DIR_NAME)
    os.makedirs(img_done_dir, exist_ok=True)
    if mode == "2":
        os.makedirs(out_labels_dir, exist_ok=True)
        lbl_done_dir = os.path.join(lbl_in_dir, PROCESSED_DIR_NAME)
        os.makedirs(lbl_done_dir, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tag = "rename" if mode == "1" else "pair-rename"
    done, log_lines = [], []
    for img, txt, new_img, new_txt in plan:
        shutil.copy2(os.path.join(img_in_dir, img), os.path.join(out_images_dir, new_img))
        shutil.move(os.path.join(img_in_dir, img), unique_path(img_done_dir, img))
        if txt:
            shutil.copy2(os.path.join(lbl_in_dir, txt), os.path.join(out_labels_dir, new_txt))
            shutil.move(os.path.join(lbl_in_dir, txt), unique_path(lbl_done_dir, txt))
            line = f"{img} + {txt} -> {new_img} + {new_txt}"
        else:
            line = f"{img} -> {new_img}"
        log_lines.append(f"{stamp} | {tag} | {line}")
        done.append(line)

    _append_log(log_file, log_lines)
    return done


# ==========================================
# データセットへの取り込み（B + C → dataset）
# ==========================================
def build_merge_plan(images_dir, labels_dir, dataset_dir, veg_name):
    """取り込み計画を立てる。ファイルには一切書き込まない。

    戻り値 dict:
      problems  : 実行を止める問題（1件でもあれば plan は空）
      ignored   : 無視した対象外ファイル（"B: 名前" / "C: 名前" 形式）
      plan      : [(split, 画像ファイル名, txtファイル名), ...]
      n_train / n_val : 取り込み数
      empty_txts: 中身が空の txt（背景画像扱いになる警告用）
    """
    result = {"problems": [], "ignored": [], "plan": [],
              "n_train": 0, "n_val": 0, "empty_txts": []}

    if not os.path.isdir(images_dir):
        result["problems"].append(f"画像フォルダがありません: {images_dir}")
        return result
    if not os.path.isdir(labels_dir):
        result["problems"].append(f"txt フォルダがありません: {labels_dir}")
        return result

    pat = re.compile(rf"^{re.escape(veg_name)}_(train|val)_(\d+)$")

    images, labels = {}, {}  # stem -> ファイル名
    for fname in sorted(os.listdir(images_dir)):
        if not os.path.isfile(os.path.join(images_dir, fname)):
            continue
        stem, ext = os.path.splitext(fname)
        if ext.lower() in IMAGE_EXTS:
            images[stem] = fname
        else:
            result["ignored"].append(f"B: {fname}")
    for fname in sorted(os.listdir(labels_dir)):
        if not os.path.isfile(os.path.join(labels_dir, fname)):
            continue
        stem, ext = os.path.splitext(fname)
        if ext.lower() == ".txt":
            labels[stem] = fname
        else:
            result["ignored"].append(f"C: {fname}")

    if not images and not labels:
        result["problems"].append("取り込むファイルがありません。")
        return result

    # 取り込み前の全件検証（1件でも問題があれば何もしない）
    plan = []
    for stem, img in images.items():
        m = pat.match(stem)
        if not m:
            result["problems"].append(
                f"名前の形式が違う画像: {img}（先に rename_new_images.py でリネームしてください）")
            continue
        if stem not in labels:
            result["problems"].append(
                f"ラベル付け忘れ: {img} に対応する {stem}.txt が C にありません")
            continue
        plan.append((m.group(1), img, labels[stem]))
    for stem, lbl in labels.items():
        if stem not in images:
            result["problems"].append(
                f"画像がない txt: {lbl} に対応する画像が B にありません")
    for split, img, lbl in plan:
        for sub, fname in (("images", img), ("labels", lbl)):
            target = os.path.join(dataset_dir, split, sub, fname)
            if os.path.exists(target):
                result["problems"].append(f"データセットに同名ファイルが既にあります: {target}")

    if result["problems"]:
        return result

    for split, img, lbl in plan:
        with open(os.path.join(labels_dir, lbl), encoding="utf-8") as f:
            if f.read().strip() == "":
                result["empty_txts"].append(lbl)

    result["plan"] = plan
    result["n_train"] = sum(1 for split, _, _ in plan if split == "train")
    result["n_val"] = len(plan) - result["n_train"]
    return result


def execute_merge_plan(plan, images_dir, labels_dir, dataset_dir, log_file=None):
    """取り込み計画を実行する（B と C から dataset へ「移動」）。

    戻り値: 実行内容の文字列リスト（1件1行）
    """
    log_file = log_file or LOG_FILE
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    done, log_lines = [], []
    for split, img, lbl in plan:
        img_out = os.path.join(dataset_dir, split, "images")
        lbl_out = os.path.join(dataset_dir, split, "labels")
        os.makedirs(img_out, exist_ok=True)
        os.makedirs(lbl_out, exist_ok=True)
        shutil.move(os.path.join(images_dir, img), os.path.join(img_out, img))
        shutil.move(os.path.join(labels_dir, lbl), os.path.join(lbl_out, lbl))
        line = f"{img} + {lbl} -> {split}/"
        log_lines.append(f"{stamp} | merge | {line}")
        done.append(line)

    _append_log(log_file, log_lines)
    return done


def count_dataset_images(dataset_dir):
    """データセットの train/val それぞれの画像枚数を返す（存在する split のみ）"""
    counts = {}
    for split in ("train", "val"):
        d = os.path.join(dataset_dir, split, "images")
        if os.path.isdir(d):
            counts[split] = sum(1 for f in os.listdir(d)
                                if os.path.splitext(f)[1].lower() in IMAGE_EXTS)
    return counts


# ==========================================
# パターン2: リネームして dataset へ直接投入
# ==========================================
def build_import_plan(images_dir, labels_dir, dataset_dir, veg_name,
                      staging_images_dir=None, staging_labels_dir=None):
    """アノテーション済みペア（画像 + txt）をリネームして dataset へ直接投入する計画。

    番号は dataset と staging（未取り込みのパターン1分）の両方を走査して続きから振る。
    ファイルには一切書き込まない。
    戻り値 dict:
      problems  : 実行を止める問題（1件でもあれば plan は空）
      ignored   : 無視した対象外ファイル名のリスト
      plan      : [(元画像名, 元txt名, 新画像名, 新txt名, split), ...]
      n_train / n_val : 振り分け数
      max_num   : 既存の最大番号 {"train": int, "val": int}
      empty_txts: 中身が空の txt（背景画像扱いになる警告用。元ファイル名）
    """
    staging_images_dir = staging_images_dir or RENAMED_DIR
    staging_labels_dir = staging_labels_dir or LABELS_DIR
    result = {"problems": [], "ignored": [], "plan": [],
              "n_train": 0, "n_val": 0,
              "max_num": {"train": 0, "val": 0}, "empty_txts": []}

    if not os.path.isdir(images_dir):
        result["problems"].append(f"画像フォルダがありません: {images_dir}")
        return result
    if not os.path.isdir(labels_dir):
        result["problems"].append(f"txt フォルダがありません: {labels_dir}")
        return result

    images, ignored = list_files(images_dir, IMAGE_EXTS)
    result["ignored"].extend(ignored)
    txts, ignored_l = list_files(labels_dir, [".txt"])
    result["ignored"].extend(ignored_l)

    items = _pair_by_stem(images, txts, result)
    if items is None:
        return result
    if not items:
        result["problems"].append("取り込むファイルがありません。")
        return result

    # 既存の番号を調べて続きから採番（dataset + 未取り込みの staging 分）
    scan_dirs = [
        os.path.join(dataset_dir, "train", "images"),
        os.path.join(dataset_dir, "train", "labels"),
        os.path.join(dataset_dir, "val", "images"),
        os.path.join(dataset_dir, "val", "labels"),
        staging_images_dir,
        staging_labels_dir,
    ]
    assignments, max_num, n_train = _assign_split_numbers(items, veg_name, scan_dirs)
    result["max_num"] = max_num

    for img, txt, split, new_stem in assignments:
        ext = os.path.splitext(img)[1].lower()
        result["plan"].append((img, txt, new_stem + ext, new_stem + ".txt", split))

    # dataset 側との衝突チェック（念のため）
    for _, _, new_img, new_txt, split in result["plan"]:
        for sub, fname in (("images", new_img), ("labels", new_txt)):
            target = os.path.join(dataset_dir, split, sub, fname)
            if os.path.exists(target):
                result["problems"].append(f"データセットに同名ファイルが既にあります: {target}")
    if result["problems"]:
        result["plan"] = []
        return result

    # 中身が空の txt を検出（背景画像として扱われる警告用）
    for img, txt, _, _, _ in result["plan"]:
        with open(os.path.join(labels_dir, txt), encoding="utf-8") as f:
            if f.read().strip() == "":
                result["empty_txts"].append(txt)

    result["n_train"] = n_train
    result["n_val"] = len(result["plan"]) - n_train
    return result


def execute_import_plan(plan, images_dir, labels_dir, dataset_dir, log_file=None):
    """直接投入を実行する。

    新しい名前で dataset へコピーし、元ファイルは各入力フォルダ内の processed/ へ
    退避（二重取り込み防止）、ログに追記する。
    戻り値: 実行内容の文字列リスト（1件1行）
    """
    log_file = log_file or LOG_FILE
    img_done_dir = os.path.join(images_dir, PROCESSED_DIR_NAME)
    lbl_done_dir = os.path.join(labels_dir, PROCESSED_DIR_NAME)
    os.makedirs(img_done_dir, exist_ok=True)
    os.makedirs(lbl_done_dir, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    done, log_lines = [], []
    for img, txt, new_img, new_txt, split in plan:
        img_out = os.path.join(dataset_dir, split, "images")
        lbl_out = os.path.join(dataset_dir, split, "labels")
        os.makedirs(img_out, exist_ok=True)
        os.makedirs(lbl_out, exist_ok=True)
        shutil.copy2(os.path.join(images_dir, img), os.path.join(img_out, new_img))
        shutil.move(os.path.join(images_dir, img), unique_path(img_done_dir, img))
        shutil.copy2(os.path.join(labels_dir, txt), os.path.join(lbl_out, new_txt))
        shutil.move(os.path.join(labels_dir, txt), unique_path(lbl_done_dir, txt))
        line = f"{img} + {txt} -> {split}/{new_img} + {new_txt}"
        log_lines.append(f"{stamp} | import | {line}")
        done.append(line)

    _append_log(log_file, log_lines)
    return done
