# rename_app Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** リネーム機能を `rename_app/` に集約し、複数野菜対応(`datasets/<野菜名>/`)とパターン2の dataset 直接投入を実装する。

**Architecture:** core.py(計画立案 build_* / 実行 execute_* を分離、build 系は書き込みなし)+ 薄い対話式CLI。パターン1(アノテ前)は staging 経由、パターン2(アノテ済みペア)はリネームと同時に dataset へ直接投入。

**Tech Stack:** Python 3.11 (venv)、標準ライブラリのみ。

**Spec:** `docs/superpowers/specs/2026-07-17-rename-app-design.md` (v2)

**前提状態:** v1 の Task 1 で `rename_app/core.py` が spec v1 どおりに作成済み(レビュー合格)。本計画の Task 1 はそれへの改修。root の `rename_new_images.py` / `merge_to_dataset.py` / `rename_daikon2.py` / `daikon2_staging/`(空) / `dataset_daikon2/`(実データ 375ファイル) / `data_daikon2.yaml` は現存。

## Global Constraints

- 本物のデータセット(`dataset_daikon2/`、移行後は `datasets/daikon/`)の**中身**には触らない。移動は Task 5 の手順のみで行い、移動前後で件数一致を検証する。
- `rename_daikon2.py` は**無変更**で移動のみ。
- CLI の対話フロー(プロンプト方式・プレビュー・`y/N` 確認・ログ形式)は現状の方式を維持。
- pytest は導入しない。検証は使い捨てスクリプト(`.superpowers/sdd/work/`)で行う。
- **git commit / git add は行わない**(ユーザーが自分でコミットする)。
- リポジトリ(`E:\program\AI figure learn\yolo`)の外のファイルは読み書きしない。
- Windows 環境。パス結合は `os.path.join`、書き込みは `encoding="utf-8"` 明示。
- 旧 root スクリプトの削除・staging/dataset の移動は Task 5 まで行わない(検証が通るまで元を残す)。

---

### Task 1: core.py を v2 に改修

**Files:**
- Modify: `rename_app/core.py`

**Interfaces:**
- Consumes: v1 の core.py(`build_rename_plan` / `execute_rename_plan` / `build_merge_plan` / `execute_merge_plan` / `count_dataset_images` / ヘルパーは変更なしで残す)
- Produces(後続タスクが使う):
  - 変更定数: `STAGING_DIR` = `rename_app/data_staging`、`DATASETS_ROOT` = `<ルート>/datasets`(旧 `DEFAULT_DATASET_DIR` は削除)
  - `default_dataset_dir(veg_name) -> str` — `datasets/<野菜名>` を返す
  - `build_import_plan(images_dir, labels_dir, dataset_dir, veg_name, staging_images_dir=None, staging_labels_dir=None) -> dict`
    戻り値キー: `problems`, `ignored`, `plan: list[(元画像名, 元txt名, 新画像名, 新txt名, split)]`, `n_train`, `n_val`, `max_num`, `empty_txts`
  - `execute_import_plan(plan, images_dir, labels_dir, dataset_dir, log_file=None) -> list[str]`

- [ ] **Step 1: STAGING_DIR を変更する**

Edit で以下を置換(1箇所):

old:
```python
STAGING_DIR = os.path.join(APP_DIR, "daikon2_staging")
```
new:
```python
STAGING_DIR = os.path.join(APP_DIR, "data_staging")
```

- [ ] **Step 2: DEFAULT_DATASET_DIR を DATASETS_ROOT に置き換える**

Edit で以下を置換(1箇所):

old:
```python
DEFAULT_DATASET_DIR = os.path.join(ROOT_DIR, "dataset_daikon2")  # データセットはルート直下のまま
DEFAULT_VEG_NAME = "daikon"
```
new:
```python
DATASETS_ROOT = os.path.join(ROOT_DIR, "datasets")  # 野菜ごとのデータセット置き場（ルート直下）
DEFAULT_VEG_NAME = "daikon"
```

- [ ] **Step 3: default_dataset_dir ヘルパーを追加する**

Edit で以下を置換(`scan_max_numbers` の直前にヘルパーを差し込む):

old:
```python
# ==========================================
# 共通ヘルパー
# ==========================================
def scan_max_numbers(veg_name, dirs):
```
new:
```python
# ==========================================
# 共通ヘルパー
# ==========================================
def default_dataset_dir(veg_name):
    """野菜名から取り込み先データセットフォルダ（datasets/<野菜名>）を導出する"""
    return os.path.join(DATASETS_ROOT, veg_name)


def scan_max_numbers(veg_name, dirs):
```

- [ ] **Step 4: パターン2直接投入の2関数をファイル末尾に追加する**

`count_dataset_images` 関数の後(ファイル末尾)に以下を追記する:

```python


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

    # 画像と txt が完全にペアになっているか検証
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
        return result

    items = [(img, txt_by_stem[stem]) for stem, img in sorted(img_by_stem.items())]
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
    max_num = scan_max_numbers(veg_name, scan_dirs)
    result["max_num"] = max_num

    # 8:2 でランダムに train/val へ振り分け（番号そのものは名前順に振る）
    n_train = round(len(items) * TRAIN_RATIO)
    shuffled = items[:]
    random.shuffle(shuffled)
    train_set = {img for img, _ in shuffled[:n_train]}

    counters = {"train": max_num["train"], "val": max_num["val"]}
    for img, txt in items:
        split = "train" if img in train_set else "val"
        counters[split] += 1
        ext = os.path.splitext(img)[1].lower()
        new_stem = f"{veg_name}_{split}_{counters[split]:03d}"
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
```

- [ ] **Step 5: import と定数・関数を確認する**

Run(リポジトリルートで):
```bash
venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'rename_app'); import core; print(core.STAGING_DIR); print(core.DATASETS_ROOT); print(core.default_dataset_dir('daikon')); print(callable(core.build_import_plan), callable(core.execute_import_plan))"
```
Expected:
```
E:\program\AI figure learn\yolo\rename_app\data_staging
E:\program\AI figure learn\yolo\datasets
E:\program\AI figure learn\yolo\datasets\daikon
True True
```

また `DEFAULT_DATASET_DIR` が残っていないことを確認:
```bash
grep -c "DEFAULT_DATASET_DIR" rename_app/core.py
```
Expected: `0`

- [ ] **Step 6: ユーザーへ報告**(コミットしない)

---

### Task 2: rename_app/rename_new_images.py — 対話式CLI

**Files:**
- Create: `rename_app/rename_new_images.py`

**Interfaces:**
- Consumes: Task 1 の `core.build_rename_plan`, `core.execute_rename_plan`, `core.build_import_plan`, `core.execute_import_plan`, `core.default_dataset_dir`, `core.count_dataset_images`, 定数 `NEW_DIR`, `RECEIVED_IMAGES_DIR`, `RECEIVED_LABELS_DIR`, `RENAMED_DIR`, `LABELS_DIR`, `DEFAULT_VEG_NAME`, `PROCESSED_DIR_NAME`, `LOG_FILE`
- Produces: `python rename_app/rename_new_images.py` の対話式CLI(パターン1=staging行き / パターン2=dataset直接投入)

- [ ] **Step 1: CLI を作成する**

```python
"""新規データのリネーム — 対話式CLI。

パターン1: 集めた画像をリネームして staging（2_renamed）で待機させる（アノテーション前）
パターン2: アノテーション済みペアをリネームして dataset へ直接投入する
ロジックは core.py にある。ここは質問・プレビュー表示・y/N 確認だけ。
"""
import core


def ask(prompt, default):
    ans = input(f"{prompt} [{default}]: ").strip()
    return ans if ans else default


def main():
    print("=== 新規データのリネーム（続き番号 + train/val 振り分け）===")
    print("  1: 自分で集めた画像（アノテーション前・画像のみ → staging で待機）")
    print("  2: 外部から届いたアノテーション済みデータ（画像 + txt → dataset へ直接投入）")
    mode = ask("どちらのパターンですか", "1")
    if mode not in ("1", "2"):
        print(f"エラー: 1 か 2 を入力してください（入力値: {mode}）")
        return

    if mode == "1":
        img_in_dir = ask("新しい画像のフォルダ", core.NEW_DIR)
        lbl_in_dir = None
    else:
        img_in_dir = ask("届いた画像のフォルダ", core.RECEIVED_IMAGES_DIR)
        lbl_in_dir = ask("届いた txt のフォルダ", core.RECEIVED_LABELS_DIR)
    veg_name = ask("野菜名 (prefix)", core.DEFAULT_VEG_NAME)
    dataset_dir = ask("データセットのフォルダ", core.default_dataset_dir(veg_name))

    if mode == "1":
        result = core.build_rename_plan(mode, img_in_dir, lbl_in_dir, dataset_dir, veg_name)
    else:
        result = core.build_import_plan(img_in_dir, lbl_in_dir, dataset_dir, veg_name)

    if result["ignored"]:
        print(f"※ 対象外のファイルは無視します: {', '.join(result['ignored'])}")
    if result["problems"]:
        print(f"\nエラーのため中断しました（何も変更していません）: {len(result['problems'])}件")
        for p in result["problems"]:
            print(f"  - {p}")
        return

    max_num = result["max_num"]
    print(f"\n既存の番号: train は {max_num['train']:03d} まで / val は {max_num['val']:03d} まで")

    plan = result["plan"]
    print(f"\n--- プレビュー ({len(plan)}件: train {result['n_train']} / val {result['n_val']}) ---")
    if mode == "1":
        for img, txt, new_img, new_txt in plan:
            print(f"  {img} -> {new_img}")
        print(f"\n・画像は新しい名前で {core.RENAMED_DIR} へコピーします")
        print(f"・元のファイルは各フォルダ内の {core.PROCESSED_DIR_NAME}/ へ移動します（二重リネーム防止）")
    else:
        for img, txt, new_img, new_txt, split in plan:
            print(f"  {img} + {txt} -> {split}/{new_img} + {new_txt}")
        if result["empty_txts"]:
            print(f"\n※ 中身が空の txt が {len(result['empty_txts'])}件あります（検出対象なしの背景画像として扱われます）:")
            for lbl in result["empty_txts"]:
                print(f"  - {lbl}")
        print(f"\n・{dataset_dir} へ直接投入します（画像も txt も新しい名前になります）")
        print(f"・元のファイルは各フォルダ内の {core.PROCESSED_DIR_NAME}/ へ移動します（二重取り込み防止）")

    ans = input("\n実行しますか？ [y/N]: ").strip().lower()
    if ans not in ("y", "yes"):
        print("キャンセルしました（何も変更していません）。")
        return

    if mode == "1":
        for line in core.execute_rename_plan(plan, mode, img_in_dir, lbl_in_dir):
            print(f"コピー: {line}")
        print(f"\n完了！ {len(plan)}件をリネームしました (train {result['n_train']} / val {result['n_val']})")
        print(f"記録: {core.LOG_FILE}")
        print(f"次の手順: {core.RENAMED_DIR} の画像をアノテーションして、txt を {core.LABELS_DIR} に保存してください。")
    else:
        for line in core.execute_import_plan(plan, img_in_dir, lbl_in_dir, dataset_dir):
            print(f"投入: {line}")
        print(f"\n完了！ {len(plan)}ペアを取り込みました (train {result['n_train']} / val {result['n_val']})")
        for split, total in core.count_dataset_images(dataset_dir).items():
            print(f"  {split}: 合計 {total}枚")
        print(f"記録: {core.LOG_FILE}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: N キャンセルでスモークテスト(パターン1・何も変更しないこと)**

```bash
mkdir -p ".superpowers/sdd/work/smoke/new" ".superpowers/sdd/work/smoke/dataset"
printf 'dummy' > ".superpowers/sdd/work/smoke/new/photo1.jpg"
printf '1\n.superpowers/sdd/work/smoke/new\ndaikon\n.superpowers/sdd/work/smoke/dataset\nN\n' | venv/Scripts/python.exe rename_app/rename_new_images.py
ls ".superpowers/sdd/work/smoke/new"
```
Expected:
- プレビューに `photo1.jpg -> daikon_train_001.jpg` が出る
- `キャンセルしました（何も変更していません）。`
- 最後の `ls` で `photo1.jpg` のみ(processed/ ができていない)

- [ ] **Step 3: N キャンセルでスモークテスト(パターン2)**

```bash
mkdir -p ".superpowers/sdd/work/smoke/rimg" ".superpowers/sdd/work/smoke/rlbl"
printf 'dummy' > ".superpowers/sdd/work/smoke/rimg/a.jpg"
printf '0 0.5 0.5 0.1 0.1\n' > ".superpowers/sdd/work/smoke/rlbl/a.txt"
printf '2\n.superpowers/sdd/work/smoke/rimg\n.superpowers/sdd/work/smoke/rlbl\ndaikon\n.superpowers/sdd/work/smoke/dataset\nN\n' | venv/Scripts/python.exe rename_app/rename_new_images.py
ls ".superpowers/sdd/work/smoke/dataset" 2>/dev/null; echo "exit=$?"
```
Expected:
- プレビューに `a.jpg + a.txt -> train/daikon_train_001.jpg + daikon_train_001.txt`
- `キャンセルしました（何も変更していません）。`
- dataset フォルダは空のまま

- [ ] **Step 4: ユーザーへ報告**

---

### Task 3: rename_app/merge_to_dataset.py — 対話式CLI(パターン1の取り込み)

**Files:**
- Create: `rename_app/merge_to_dataset.py`

**Interfaces:**
- Consumes: Task 1 の `core.build_merge_plan`, `core.execute_merge_plan`, `core.count_dataset_images`, `core.default_dataset_dir`, 定数 `RENAMED_DIR`, `LABELS_DIR`, `DEFAULT_VEG_NAME`, `LOG_FILE`
- Produces: `python rename_app/merge_to_dataset.py` の対話式CLI

- [ ] **Step 1: CLI を作成する**

```python
"""データセットへの取り込み（B + C → dataset）— パターン1専用の対話式CLI。

アノテーションが済んだ staging の画像+txt を検証して dataset へ移動する。
ロジックは core.py にある。ここは質問・プレビュー表示・y/N 確認だけ。
"""
import core


def ask(prompt, default):
    ans = input(f"{prompt} [{default}]: ").strip()
    return ans if ans else default


def main():
    print("=== データセットへの取り込み（B + C → dataset）===")
    images_dir = ask("リネーム済み画像のフォルダ (B)", core.RENAMED_DIR)
    labels_dir = ask("アノテーション txt のフォルダ (C)", core.LABELS_DIR)
    veg_name = ask("野菜名 (prefix)", core.DEFAULT_VEG_NAME)
    dataset_dir = ask("データセットのフォルダ", core.default_dataset_dir(veg_name))

    result = core.build_merge_plan(images_dir, labels_dir, dataset_dir, veg_name)

    if result["ignored"]:
        print(f"※ 対象外のファイルは無視します: {', '.join(result['ignored'])}")
    if result["problems"]:
        print(f"\nエラーのため中断しました（何も変更していません）: {len(result['problems'])}件")
        for p in result["problems"]:
            print(f"  - {p}")
        return

    plan = result["plan"]
    print(f"\n--- プレビュー ({len(plan)}ペア: train {result['n_train']} / val {result['n_val']}) ---")
    for split, img, lbl in plan:
        print(f"  {img} + {lbl} -> {split}/")
    if result["empty_txts"]:
        print(f"\n※ 中身が空の txt が {len(result['empty_txts'])}件あります（検出対象なしの背景画像として扱われます）:")
        for lbl in result["empty_txts"]:
            print(f"  - {lbl}")
    print(f"\n・{dataset_dir} へ「移動」します（B と C からは無くなります）")

    ans = input("\n実行しますか？ [y/N]: ").strip().lower()
    if ans not in ("y", "yes"):
        print("キャンセルしました（何も変更していません）。")
        return

    for line in core.execute_merge_plan(plan, images_dir, labels_dir, dataset_dir):
        print(f"移動: {line}")

    print(f"\n完了！ {len(plan)}ペアを取り込みました (train {result['n_train']} / val {result['n_val']})")
    for split, total in core.count_dataset_images(dataset_dir).items():
        print(f"  {split}: 合計 {total}枚")
    print(f"記録: {core.LOG_FILE}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 空フォルダでスモークテスト(安全に中断すること)**

```bash
mkdir -p ".superpowers/sdd/work/smoke/emptyB" ".superpowers/sdd/work/smoke/emptyC"
printf '.superpowers/sdd/work/smoke/emptyB\n.superpowers/sdd/work/smoke/emptyC\ndaikon\n.superpowers/sdd/work/smoke/dataset\n' | venv/Scripts/python.exe rename_app/merge_to_dataset.py
```
Expected: `エラーのため中断しました（何も変更していません）: 1件` と `取り込むファイルがありません。`

- [ ] **Step 3: ユーザーへ報告**

---

### Task 4: 通し検証(ダミーデータで一連のフローを実行)

**Files:**
- Create: `.superpowers/sdd/work/verify_rename_app.py`(使い捨て)

**Interfaces:**
- Consumes: Task 1 の core 全関数(パス引数をすべてダミーに差し替えて呼ぶ)

- [ ] **Step 1: 検証スクリプトを作成する**

```python
"""rename_app の通し検証（使い捨て）。本物の datasets/ には一切触らない。"""
import os
import shutil
import sys

sys.path.insert(0, r"E:\program\AI figure learn\yolo\rename_app")
import core

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_work")
NEW = os.path.join(BASE, "1_new")
RCV_IMG = os.path.join(BASE, "received", "images")
RCV_LBL = os.path.join(BASE, "received", "labels")
B = os.path.join(BASE, "2_renamed")
C = os.path.join(BASE, "3_labels")
DS = os.path.join(BASE, "datasets", "daikon")
LOG = os.path.join(BASE, "rename_log.txt")

checks = []

def check(name, cond):
    checks.append((name, cond))
    print(("OK  " if cond else "NG  ") + name)

def write(path, text="dummy"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

if os.path.isdir(BASE):
    shutil.rmtree(BASE)

# --- パターン1: 画像のみ 5枚をリネーム（staging 行き）---
for i in range(5):
    write(os.path.join(NEW, f"photo{i}.jpg"))
r = core.build_rename_plan("1", NEW, None, DS, "daikon",
                           out_images_dir=B, out_labels_dir=C)
check("P1: 問題なし", r["problems"] == [])
check("P1: 5件の計画", len(r["plan"]) == 5)
check("P1: train4/val1", r["n_train"] == 4 and r["n_val"] == 1)
core.execute_rename_plan(r["plan"], "1", NEW, None,
                         out_images_dir=B, out_labels_dir=C, log_file=LOG)
check("P1: B に 5枚", len(os.listdir(B)) == 5)
check("P1: 元は processed へ",
      len(os.listdir(os.path.join(NEW, "processed"))) == 5)
check("P1: 入力フォルダに画像が残っていない",
      [f for f in os.listdir(NEW) if f != "processed"] == [])

# --- アノテーション相当: B の各画像に対応する txt を C に作る（1つは空 = 背景）---
stems = [os.path.splitext(f)[0] for f in sorted(os.listdir(B))]
for i, stem in enumerate(stems):
    write(os.path.join(C, stem + ".txt"),
          "" if i == 0 else "0 0.5 0.5 0.2 0.2\n")

# --- パターン1の取り込み（merge）---
m = core.build_merge_plan(B, C, DS, "daikon")
check("M1: 問題なし", m["problems"] == [])
check("M1: 5ペア", len(m["plan"]) == 5)
check("M1: 空txtを1件検出", len(m["empty_txts"]) == 1)
core.execute_merge_plan(m["plan"], B, C, DS, log_file=LOG)
counts = core.count_dataset_images(DS)
check("M1: dataset 合計5枚", sum(counts.values()) == 5)
check("M1: B/C が空になった", os.listdir(B) == [] and os.listdir(C) == [])

# --- パターン2: 届いたペア 2組を dataset へ直接投入（続き番号になること）---
write(os.path.join(RCV_IMG, "recv_a.jpg"))
write(os.path.join(RCV_IMG, "recv_b.jpg"))
write(os.path.join(RCV_LBL, "recv_a.txt"), "0 0.5 0.5 0.1 0.1\n")
write(os.path.join(RCV_LBL, "recv_b.txt"), "")
r2 = core.build_import_plan(RCV_IMG, RCV_LBL, DS, "daikon",
                            staging_images_dir=B, staging_labels_dir=C)
check("P2: 問題なし", r2["problems"] == [])
check("P2: 2件の計画", len(r2["plan"]) == 2)
check("P2: 空txtを1件検出", r2["empty_txts"] == ["recv_b.txt"])
prev_max = r2["max_num"]
new_nums_ok = all(
    int(new_img.split("_")[-1].split(".")[0]) > prev_max[split]
    for _, _, new_img, _, split in r2["plan"])
check("P2: 番号が既存の続きから始まる", new_nums_ok)
core.execute_import_plan(r2["plan"], RCV_IMG, RCV_LBL, DS, log_file=LOG)
check("P2: dataset 合計7枚", sum(core.count_dataset_images(DS).values()) == 7)
check("P2: 元は processed へ",
      len(os.listdir(os.path.join(RCV_IMG, "processed"))) == 2
      and len(os.listdir(os.path.join(RCV_LBL, "processed"))) == 2)
lbl_files = (os.listdir(os.path.join(DS, "train", "labels"))
             + os.listdir(os.path.join(DS, "val", "labels")))
check("P2: dataset の labels も 7件", len(lbl_files) == 7)

# --- エラー系: import でペア欠け（txt なし画像）→ 全件中断 ---
write(os.path.join(RCV_IMG, "recv_c.jpg"))
r3 = core.build_import_plan(RCV_IMG, RCV_LBL, DS, "daikon",
                            staging_images_dir=B, staging_labels_dir=C)
check("E1: ペア欠けを検出して plan が空", r3["problems"] != [] and r3["plan"] == [])
os.remove(os.path.join(RCV_IMG, "recv_c.jpg"))

# --- エラー系: merge で名前形式が違う画像 ---
write(os.path.join(B, "wrongname.jpg"))
write(os.path.join(C, "wrongname.txt"), "0 0.5 0.5 0.1 0.1\n")
m4 = core.build_merge_plan(B, C, DS, "daikon")
check("E2: 名前形式の問題を検出", any("名前の形式" in p for p in m4["problems"]))
os.remove(os.path.join(B, "wrongname.jpg"))
os.remove(os.path.join(C, "wrongname.txt"))

# --- default_dataset_dir の導出 ---
check("DD: datasets/<野菜名> を返す",
      core.default_dataset_dir("komatsuna").endswith(os.path.join("datasets", "komatsuna")))

# --- ログが書かれている ---
with open(LOG, encoding="utf-8") as f:
    log_text = f.read()
check("LOG: rename/merge/import が記録されている",
      "| rename |" in log_text and "| merge |" in log_text and "| import |" in log_text)

print()
failed = [n for n, c in checks if not c]
if failed:
    print(f"FAILED: {len(failed)}/{len(checks)}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({len(checks)})")
```

- [ ] **Step 2: 実行して全チェック通過を確認する**

Run: `venv/Scripts/python.exe ".superpowers/sdd/work/verify_rename_app.py"`
Expected: 各行 `OK` で最後に `ALL CHECKS PASSED (22)`。
NG が出たら core.py / 検証スクリプトの期待値のどちらが設計とずれているかを特定して修正・再実行。

- [ ] **Step 3: ユーザーへ報告**

---

### Task 5: 実データの移行と後片付け(検証が通ってから行う)

**Files:**
- Move: `dataset_daikon2/` → `datasets/daikon/`(実データ。件数検証つき)
- Modify: `data_daikon2.yaml`(path を新しい場所に)
- Move: `rename_daikon2.py` → `rename_app/rename_daikon2.py`(無変更)
- Delete: root の `rename_new_images.py`, `merge_to_dataset.py`(置き換え済み)
- Delete: root の `daikon2_staging/`(空確認後)
- Create: `rename_app/data_staging/` 構造、`rename_app/README.md`

**Interfaces:**
- Consumes: Task 1〜4 完了・検証通過
- Produces: spec v2 の「フォルダ構成」と一致する最終状態

- [ ] **Step 1: 移動前の件数を記録する**

```bash
find dataset_daikon2 -type f | wc -l
find dataset_daikon2/train/images -type f | wc -l
find dataset_daikon2/val/images -type f | wc -l
```
Expected: `375` / `150` / `37`(1件でも違ったら**中断してユーザーに報告**。375 = 150+150+37+37+rename_map.txt)

- [ ] **Step 2: datasets/daikon へ移動して件数を確認する**

```bash
mkdir -p datasets
mv dataset_daikon2 datasets/daikon
find datasets/daikon -type f | wc -l
ls datasets/daikon
```
Expected: `375`、`ls` に `train val rename_map.txt`。件数が合わなければ**即ユーザーに報告**(mv はフォルダ単位なので通常欠損しない)。

- [ ] **Step 3: data_daikon2.yaml の path を更新する**

Edit で置換:

old:
```yaml
path: E:\program\AI figure learn\yolo\dataset_daikon2
```
new:
```yaml
path: E:\program\AI figure learn\yolo\datasets\daikon
```
(train/val/nc/names は変更しない)

- [ ] **Step 4: 旧 staging の空確認 → 片付け・新設**

```bash
find daikon2_staging -type f
```
Expected: 出力なし(ファイルが出たら**削除せず中断**、ユーザーに確認)

```bash
mv rename_daikon2.py rename_app/rename_daikon2.py
rm rename_new_images.py merge_to_dataset.py
rm -r daikon2_staging
mkdir -p rename_app/data_staging/1_new \
         rename_app/data_staging/received/images \
         rename_app/data_staging/received/labels \
         rename_app/data_staging/2_renamed \
         rename_app/data_staging/3_labels
```
(3スクリプトとも git 未追跡なので git 操作は不要。`git rm` は使わない)

- [ ] **Step 5: README.md を作成する**

`rename_app/README.md`:

````markdown
# rename_app — データセット追加用リネームツール

野菜データセット（`../datasets/<野菜名>/`）へ新しい画像を追加するときに使うツール一式。
将来は Streamlit アプリ化する予定（core.py を import して UI を足すだけ）。

## 構成

```
rename_app/
├─ core.py               # ロジック本体（計画立案と実行を分離。UIなし）
├─ rename_new_images.py  # ① リネーム（対話式CLI）
├─ merge_to_dataset.py   # ② パターン1の取り込み（対話式CLI）
├─ rename_daikon2.py     # 初回移行スクリプト（実行済み。記録として保管）
└─ data_staging/         # 作業用フォルダ
   ├─ 1_new/             #   パターン1: 自分で集めた画像を入れる
   ├─ received/          #   パターン2: 届いた画像+txtを入れる
   ├─ 2_renamed/         #   パターン1のリネーム済み画像（アノテ待ち）
   └─ 3_labels/          #   パターン1のアノテーションtxtを置く
```

データセット本体はリポジトリルートの `datasets/<野菜名>/train|val/images|labels` にある
（例: `datasets/daikon/`。旧 `dataset_daikon2` を移動したもの）。

## 使い方

リポジトリルートで venv を有効化してから実行する:

```
venv\Scripts\activate
python rename_app\rename_new_images.py
python rename_app\merge_to_dataset.py
```

### パターン1: 自分で集めた画像（アノテーション前）

1. 画像を `data_staging/1_new/` に入れる
2. `rename_new_images.py` → モード `1`（続き番号で採番、train/val 8:2、`2_renamed/` で待機）
3. `2_renamed/` の画像をアノテーションし、txt を `3_labels/` に同名で保存
4. `merge_to_dataset.py` で全件検証して `datasets/<野菜名>/` へ取り込み

### パターン2: アノテーション済みデータをもらった場合

1. 画像を `received/images/`、txt を `received/labels/` に入れる
2. `rename_new_images.py` → モード `2` — リネームと同時に `datasets/<野菜名>/` へ**直接投入**

どちらも実行前にプレビューが出て、`y` を入力するまで何も変更しない。
1件でも問題（ペア欠け・名前形式違い・同名衝突）があれば何もせず中断する。
処理履歴は `data_staging/rename_log.txt` に追記される。

取り込み後の学習はリポジトリルートの `data_daikon2.yaml`（`datasets/daikon` を指す）を `data=` に指定する。
````

- [ ] **Step 6: 最終確認**

```bash
ls rename_app rename_app/data_staging datasets/daikon
ls rename_daikon2.py rename_new_images.py merge_to_dataset.py daikon2_staging dataset_daikon2 2>&1
venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'rename_app'); import core, os; print(os.path.isdir(core.default_dataset_dir('daikon')))"
```
Expected:
- `rename_app/` に core.py, rename_new_images.py, merge_to_dataset.py, rename_daikon2.py, README.md, image.png, data_staging
- 2つ目の `ls` は 5つとも "No such file or directory"
- 3つ目は `True`(core の既定パスが移行後の実フォルダを指す)

- [ ] **Step 7: ユーザーへ報告**

移行結果(件数一致)・最終構成・「コミットはしていないこと」を報告する。

---

## Self-Review 結果

- **Spec coverage:** datasets/<野菜>構造→Task1(default_dataset_dir)+Task5(移行) / パターン2直接投入→Task1(import関数)+Task2(mode2) / パターン1 staging維持→Task2(mode1)+Task3 / staging改名→Task1+Task5 / yaml更新→Task5 Step3 / 検証→Task4。ギャップなし。
- **Placeholder scan:** TBD/TODO なし。全ステップ実コード・実コマンド・期待値あり。
- **Type consistency:** import plan のタプルは5要素(img, txt, new_img, new_txt, split)で build/execute/CLI/検証すべて一致。rename plan は4要素のまま。`default_dataset_dir` の呼び出し箇所(CLI 2本・検証)一致。
