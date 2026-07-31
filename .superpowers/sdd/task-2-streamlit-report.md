# Task 2: ② 取り込み（merge）検証の追加 — 実施報告

## やったこと

- `docs/superpowers/plans/2026-07-24-rename-app-streamlit-ui.md` の `### Task 2:` セクション
  （および冒頭の `## Global Constraints` / `## core.py が提供する既存インターフェース`）を読み、
  そこに書かれたコードを**そのまま**使用。
- `rename_app/verify_app.py` に、① の入力変更無効化ブロック
  (`# ---- ① 入力変更でプレビュー無効化 ----`) の後・最終 `print()` の直前に、
  ② merge のプレビュー→実行を検証するブロックを挿入した（プラン記載のコード verbatim）。
  - ① で `RENAMED`（=B）に作られた5枚の画像ファイル名（stem）に対応する `.txt` を
    `LABELS`（=C）に作成（1件だけ空txt、残りは中身あり）。
  - `mode=merge` で `merge_img=RENAMED`, `merge_lbl=LABELS`, `dataset_dir=DS` を設定し、
    プレビュー（例外なし・エラーなし・実行ボタンあり・空txt警告1件）と
    実行（成功メッセージ・B/Cが空になる・dataset合計5枚）を確認する7チェックを追加。
- `rename_app/app.py` の変更は**不要だった**（Task 1 実装済みの `merge` 分岐がそのまま
  プランの期待通りに動作したため、修正なし）。

## 実行コマンドと結果

```
venv/Scripts/python.exe rename_app/verify_app.py
```

出力（末尾）:

```
ALL CHECKS PASSED (15)
```

全15チェック（① 8件 + ② 7件）がOK。コンソール上の日本語チェック名は
Windows コンソールのコードページの都合で文字化けして表示されたが、
`checks` リストの内容自体（対応する `check(...)` の第1引数の文字列）はプラン記載どおりであり、
`FAILED` は出力されず `ALL CHECKS PASSED (15)` で終了（exit code 0）。

## 差分

`rename_app/verify_app.py` のみ変更（プラン Step 1 のコードを verbatim 挿入）。
`rename_app/app.py` は無変更。

## コミット

対象: `rename_app/verify_app.py` のみ（`app.py` は変更なしのため対象外、
`.superpowers/sdd/progress.md` や `rename_app/app_verify_work/` 等は明示的に対象外）。

メッセージ:
```
test(rename_app): Streamlit UI ②取り込み(merge)の検証を追加
```

## 懸念事項

特になし。プラン通りに verbatim 挿入し、app.py の修正なしで期待通り
`ALL CHECKS PASSED (15)` が得られた。
