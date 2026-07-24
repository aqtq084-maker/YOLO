# Task 4: 通し検証結果

## 概要

- 検証スクリプト: `.superpowers/sdd/work/verify_rename_app.py`(ブリーフのコードをそのまま作成、修正なし)
- 実行コマンド: `venv/Scripts/python.exe ".superpowers/sdd/work/verify_rename_app.py"`
- 実行環境: Windows / Git Bash / venv
- 対象データ: すべてダミー(`.superpowers/sdd/work/verify_work/` 配下、実行のたびに削除・再作成)。`dataset_daikon2/`・`datasets/` 等の本物データには一切アクセスしていない。
- 結果: **22件中22件 OK — ALL CHECKS PASSED (22)**(期待どおり)

補足: Git Bash のデフォルトコンソールエンコーディング(Shift-JIS 系)のままだと日本語チェック名が文字化けして表示されたが、`PYTHONIOENCODING=utf-8` を付けて再実行し、内容が正しいことを確認した。スクリプト自体の出力・ロジックには問題なし(表示上の文字コードの話のみ)。

## 実行出力全文(PYTHONIOENCODING=utf-8 での再実行)

```
OK  P1: 問題なし
OK  P1: 5件の計画
OK  P1: train4/val1
OK  P1: B に 5枚
OK  P1: 元は processed へ
OK  P1: 入力フォルダに画像が残っていない
OK  M1: 問題なし
OK  M1: 5ペア
OK  M1: 空txtを1件検出
OK  M1: dataset 合計5枚
OK  M1: B/C が空になった
OK  P2: 問題なし
OK  P2: 2件の計画
OK  P2: 空txtを1件検出
OK  P2: 番号が既存の続きから始まる
OK  P2: dataset 合計7枚
OK  P2: 元は processed へ
OK  P2: dataset の labels も 7件
OK  E1: ペア欠けを検出して plan が空
OK  E2: 名前形式の問題を検出
OK  DD: datasets/<野菜名> を返す
OK  LOG: rename/merge/import が記録されている

ALL CHECKS PASSED (22)
```

## 検証した内容

1. **パターン1(自分で集めた画像 → リネーム → アノテ相当 → merge)**
   - 画像5枚のみを `build_rename_plan("1", ...)` → 問題なし・5件計画・train4/val1 に振り分け。
   - `execute_rename_plan` 実行後、staging(`2_renamed`)に5枚コピーされ、元の入力フォルダ(`1_new`)は `processed/` に退避され、入力フォルダ本体には画像が残らないことを確認。
   - `2_renamed` の各画像に対応する txt(うち1件は空 = 背景画像)を `3_labels` に用意し、`build_merge_plan` → 問題なし・5ペア・空txt1件検出。
   - `execute_merge_plan` 実行後、`datasets/daikon` 合計5枚、staging(B/C)が空になることを確認。

2. **パターン2(届いたペアを直接 dataset へ投入)**
   - 届いた画像2枚+txt2枚(うち1件は空)を `build_import_plan` → 問題なし・2件計画・空txt1件検出。
   - 新しい採番が既存最大番号(パターン1で入った分)の続きから始まることを確認(`new_nums_ok`)。
   - `execute_import_plan` 実行後、dataset 合計7枚、受信元フォルダの画像・txt がそれぞれ `processed/` に退避、dataset の labels も7件であることを確認。

3. **エラー系**
   - import でペア欠け(txt のない画像)がある場合、`problems` が非空になり `plan` が空になる(全件中断)ことを確認。
   - merge で命名規則(`<veg>_<split>_<num>`)に合わない画像がある場合、「名前の形式」を含む問題メッセージが出ることを確認。

4. **その他**
   - `default_dataset_dir("komatsuna")` が `datasets/komatsuna` で終わるパスを返すことを確認。
   - `rename_log.txt` に `| rename |`・`| merge |`・`| import |` の3種のログ行がすべて記録されていることを確認。

## 結論

- core.py 側の欠陥は見つからず、BLOCKED 事項なし。
- 検証スクリプトはブリーフのコードをそのまま使用し、転写ミスによる修正は不要だった。
- `verify_work/` はダミーデータのみで完結しており、`rename_app/` のコード(core.py・CLI)は一切変更していない。
- git commit / git add は実施していない。
