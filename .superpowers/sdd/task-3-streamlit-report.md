# Task 3: rename_app Streamlit UI — ③ import + error-case verification

## What was done

Read `docs/superpowers/plans/2026-07-24-rename-app-streamlit-ui.md`, section `### Task 3:` (up to
`### Task 4:`), plus `## Global Constraints` and `## core.py が提供する既存インターフェース`.

Read the current `rename_app/verify_app.py` to find the anchor: the ② merge block ends with the
`check("② execute: dataset 合計5枚", ...)` line, immediately followed by the final `print()` /
summary block.

Inserted the plan's verbatim code for:
- ③ import block: builds two received image/label pairs (`recv_a` with a real bbox, `recv_b` with
  an empty txt), runs preview (asserts no exception, execute button present, empty-txt warning
  present) then execute (asserts success message, dataset now totals 7 images, originals moved to
  `processed/` in both the received-images and received-labels dirs).
- 問題系 (error case) block: adds `recv_c.jpg` with no matching txt (missing pair), runs preview on
  a fresh AppTest, and asserts an error is shown and the execute button is NOT present (i.e. no
  files get changed).

Both blocks were inserted after the ② block and before the final `print()`, exactly as specified
in the plan, with no modifications to the code itself.

No changes to `rename_app/app.py` were needed — the existing `import` mode branch (implemented in
Task 1) already satisfies all ③ and error-case checks without modification.

## Exact command run

```
venv/Scripts/python.exe rename_app/verify_app.py
```

## Full test output

```
2026-07-24 16:55:42.070 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-07-24 16:55:42.710 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-07-24 16:55:42.749 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-07-24 16:55:42.842 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-07-24 16:55:42.913 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
OK  ① preview: 例外なし
OK  ① preview: エラー表示なし
OK  ① preview: 実行ボタンが出る
OK  ① execute: 例外なし
OK  ① execute: 成功メッセージ
OK  ① execute: staging に5枚コピー
OK  ① execute: 元は processed へ退避
OK  ① 入力変更前は実行ボタンあり / 変更後は消える
OK  ② preview: 例外なし
OK  ② preview: エラー表示なし
OK  ② preview: 実行ボタンが出る
OK  ② preview: 空txt警告が1件
OK  ② execute: 成功メッセージ
OK  ② execute: B/C が空になった
OK  ② execute: dataset 合計5枚
OK  ③ preview: 例外なし
OK  ③ preview: 実行ボタンが出る
OK  ③ preview: 空txt警告あり
OK  ③ execute: 成功メッセージ
OK  ③ execute: dataset 合計7枚
OK  ③ execute: 元は processed へ退避
OK  問題系: エラー表示が出る
OK  問題系: 実行ボタンを出さない

ALL CHECKS PASSED (23)
```

(Console rendered the Japanese labels as mojibake due to PowerShell/cp936 codepage display — the
raw output captured above via the Bash tool shows correct UTF-8 text; all 23 checks are `OK` and
the terminal summary line is exactly `ALL CHECKS PASSED (23)` as required.)

## Constraints observed

- `rename_app/core.py` not touched.
- No real data (`datasets/`) or real staging touched — all test paths under
  `rename_app/app_verify_work/` (temp dir, recreated each run), with `core.RENAMED_DIR` /
  `core.LABELS_DIR` / `core.LOG_FILE` reassigned to test paths (unchanged from prior tasks).
- Only `rename_app/verify_app.py` staged for commit; `app.py` unchanged so not added;
  `rename_app/app_verify_work/` not added.
- No push/reset/rebase/amend performed.

## Commit

```
git add rename_app/verify_app.py
git commit -m "test(rename_app): Streamlit UI ③直接投入(import)とエラー系の検証を追加"
```
