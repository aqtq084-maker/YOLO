# Task 2 報告書: rename_app/rename_new_images.py

## 実装内容

**作成ファイル:**
- `rename_app/rename_new_images.py` (115行)

**実装内容:**
- ブリーフのコード（Step 1）をそのまま実装
- 対話式CLI（モード選択 → フォルダ指定 → プレビュー → y/N 確認）
- Mode 1: 画像のみ → RENAMED_DIR へコピー
- Mode 2: 画像+txt ペア → dataset へ直接投入
- core.py の関数（`build_rename_plan`, `execute_rename_plan`, `build_import_plan`, `execute_import_plan`）を使用

## スモークテスト実行

### Pattern 1: 画像のみ（N キャンセル）

**実行コマンド:**
```bash
mkdir -p ".superpowers/sdd/work/smoke/new" ".superpowers/sdd/work/smoke/dataset"
printf 'dummy' > ".superpowers/sdd/work/smoke/new/photo1.jpg"
printf '1\n.superpowers/sdd/work/smoke/new\ndaikon\n.superpowers/sdd/work/smoke/dataset\nN\n' | venv/Scripts/python.exe rename_app/rename_new_images.py
```

**実際の出力（抜粋）:**
```
=== 新規データのリネーム（続き番号 + train/val 振り分け）===
  1: 自分で集めた画像（アノテーション前・画像のみ → staging で待機）
  2: 外部から届いたアノテーション済みデータ（画像 + txt → dataset へ直接投入）
...
--- プレビュー (1件: train 1 / val 0) ---
  photo1.jpg -> daikon_train_001.jpg

・画像は新しい名前で E:\program\AI figure learn\yolo\rename_app\data_staging\2_renamed へコピーします
・元のファイルは各フォルダ内の processed/ へ移動します（二重リネーム防止）

実行しますか？ [y/N]: キャンセルしました（何も変更していません）。
```

**検証結果:**
```bash
ls ".superpowers/sdd/work/smoke/new"
# 出力: photo1.jpg
```

✓ プレビューに `photo1.jpg -> daikon_train_001.jpg` が表示された
✓ `キャンセルしました（何も変更していません）。` が表示された
✓ ls で `photo1.jpg` のみ（`processed/` フォルダが作成されていない）

### Pattern 2: 画像+txt ペア（N キャンセル）

**実行コマンド:**
```bash
mkdir -p ".superpowers/sdd/work/smoke/rimg" ".superpowers/sdd/work/smoke/rlbl"
printf 'dummy' > ".superpowers/sdd/work/smoke/rimg/a.jpg"
printf '0 0.5 0.5 0.1 0.1\n' > ".superpowers/sdd/work/smoke/rlbl/a.txt"
printf '2\n.superpowers/sdd/work/smoke/rimg\n.superpowers/sdd/work/smoke/rlbl\ndaikon\n.superpowers/sdd/work/smoke/dataset\nN\n' | venv/Scripts/python.exe rename_app/rename_new_images.py
```

**実際の出力（抜粋）:**
```
=== 新規データのリネーム（続き番号 + train/val 振り分け）===
  1: 自分で集めた画像（アノテーション前・画像のみ → staging で待機）
  2: 外部から届いたアノテーション済みデータ（画像 + txt → dataset へ直接投入）
...
--- プレビュー (1件: train 1 / val 0) ---
  a.jpg + a.txt -> train/daikon_train_001.jpg + daikon_train_001.txt

・.superpowers/sdd/work/smoke/dataset へ直接投入します（画像も txt も新しい名前になります）
・元のファイルは各フォルダ内の processed/ へ移動します（二重取り込み防止）

実行しますか？ [y/N]: キャンセルしました（何も変更していません）。
```

**検証結果:**
```bash
ls ".superpowers/sdd/work/smoke/dataset" 2>/dev/null; echo "exit=$?"
# 出力: exit=0
```

✓ プレビューに `a.jpg + a.txt -> train/daikon_train_001.jpg + daikon_train_001.txt` が表示された
✓ `キャンセルしました（何も変更していません）。` が表示された
✓ dataset フォルダは空のまま（ファイルが一つも投入されていない）

## セルフレビュー

**チェック項目:**

1. **コード完全性** - ✓ ブリーフのコード（Step 1）を一字一句そのまま実装
2. **Mode 1 フロー** - ✓ 質問 → プレビュー → y/N 確認 → 正常にキャンセル
3. **Mode 2 フロー** - ✓ 質問 → プレビュー → y/N 確認 → 正常にキャンセル
4. **エラーハンドリング** - ✓ 無効なモード入力時の処理
5. **core.py 連携** - ✓ build/execute 関数の呼び出し、定数の使用
6. **出力形式** - ✓ ブリーフの出力メッセージと完全に一致
7. **ファイル変更なし** - ✓ N キャンセル時に processed/ フォルダが作成されない
8. **データセット保護** - ✓ 本物のデータセット(dataset_daikon2/)に一切触れていない

**制約チェック:**
- git commit / git add: なし ✓
- リポジトリ外ファイル操作: なし ✓
- 本物データセット操作: なし ✓

## 結論

Task 2 の実装は完了しました。対話式CLI は正常に動作し、両パターン（画像のみ / 画像+txt）のスモークテストが期待値通りにパスしました。
