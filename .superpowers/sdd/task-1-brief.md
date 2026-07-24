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

