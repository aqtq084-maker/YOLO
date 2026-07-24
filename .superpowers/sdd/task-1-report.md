# Task 1 実装レポート

## 実施内容

`rename_app/core.py` の v2 改修を完了しました。以下の4つの変更を順に実装：

### Step 1: STAGING_DIR を変更
- **変更箇所**: 行18
- **変更内容**: `STAGING_DIR = os.path.join(APP_DIR, "daikon2_staging")` → `os.path.join(APP_DIR, "data_staging")`

### Step 2: DEFAULT_DATASET_DIR を DATASETS_ROOT に置き換える
- **変更箇所**: 行25-26
- **変更内容**: 
  - 削除: `DEFAULT_DATASET_DIR = os.path.join(ROOT_DIR, "dataset_daikon2")`
  - 追加: `DATASETS_ROOT = os.path.join(ROOT_DIR, "datasets")`

### Step 3: default_dataset_dir ヘルパー関数を追加
- **変更箇所**: scan_max_numbers 関数の直前（行37〜39）
- **実装内容**: `def default_dataset_dir(veg_name)` 関数を追加
  - 野菜名から `datasets/<野菜名>` のパスを返す

### Step 4: パターン2直接投入の2関数をファイル末尾に追加
- **変更箇所**: `count_dataset_images()` 関数の後（EOF）
- **実装内容**:
  - `build_import_plan()`: リネーム計画を立てる（ファイル書き込みなし）
  - `execute_import_plan()`: 計画を実行し、dataset へコピー + 元ファイル退避

## 検証結果

### コマンド1: 定数・関数の確認
```bash
venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'rename_app'); import core; print(core.STAGING_DIR); print(core.DATASETS_ROOT); print(core.default_dataset_dir('daikon')); print(callable(core.build_import_plan), callable(core.execute_import_plan))"
```

**実行結果**:
```
E:\program\AI figure learn\yolo\rename_app\data_staging
E:\program\AI figure learn\yolo\datasets
E:\program\AI figure learn\yolo\datasets\daikon
True True
```

**期待値との比較**: ✅ 完全一致

### コマンド2: DEFAULT_DATASET_DIR の削除確認
```bash
grep -c "DEFAULT_DATASET_DIR" rename_app/core.py
```

**実行結果**: `0`

**期待値との比較**: ✅ 完全一致

## セルフレビュー結果

| 項目 | 状態 | 備考 |
|------|------|------|
| Step 1 実装 | ✅ OK | STAGING_DIR 正確に変更 |
| Step 2 実装 | ✅ OK | DATASETS_ROOT に置き換え完了 |
| Step 3 実装 | ✅ OK | default_dataset_dir 関数正確に追加 |
| Step 4 実装 | ✅ OK | 2関数全体をブリーフ通りに追加 |
| DEFAULT_DATASET_DIR 削除 | ✅ OK | 完全に削除（grep -c = 0） |
| 既存関数の無傷性 | ✅ OK | build_rename_plan, execute_rename_plan, build_merge_plan, execute_merge_plan, count_dataset_images, ヘルパー関数すべて変更なし |
| ファイル末尾に追加 | ✅ OK | count_dataset_images の直後に build_import_plan, execute_import_plan を追加 |

## 変更ファイル一覧

- `rename_app/core.py`: 
  - 行18: STAGING_DIR パス変更
  - 行25: DEFAULT_DATASET_DIR → DATASETS_ROOT
  - 行37-39: default_dataset_dir 関数追加
  - 行337-468: build_import_plan, execute_import_plan 関数追加

## 実装上の注意点

- 2つの新関数（`build_import_plan`, `execute_import_plan`）は、ブリーフ内の記述を一字一句そのまま転写
- パス結合は `os.path.join` で Windows 対応
- ファイル書き込みは `encoding="utf-8"` を明示
- 既存の4つの rename/merge 関数および全ヘルパーは完全に変更なし
- git commit/add は実行していない

---

**Status**: ✅ DONE
