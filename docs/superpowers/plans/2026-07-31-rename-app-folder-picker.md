# rename_app フォルダ選択ダイアログ化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `rename_app/app.py` の全フォルダ入力欄（①②③の全モード共通）に「📁 フォルダを開く」ボタンを追加し、OSネイティブのフォルダ選択ダイアログ（tkinter）でパスを入力できるようにする。

**Architecture:** `app.py` に `_pick_folder(initial_dir)`（tkinterダイアログを開いて選択パスを返す）と `folder_input(label, default, key)`（テキスト欄＋ボタンを横並びで描画するヘルパー）を追加し、`render_inputs()` 内の6箇所の `st.text_input(...)` 呼び出しを `folder_input(...)` に置き換える。ボタン押下→ダイアログ→`st.session_state[key]` 書き込み→`st.rerun()` という、Streamlitの「ウィジェット生成前に session_state を更新する」正規パターンを使う。

**Tech Stack:** Python 3.11 / Streamlit / tkinter（標準ライブラリ、追加インストール不要）

## Global Constraints

- `core.py` は無変更（設計書の非スコープ）
- `requirements.txt` は変更しない（tkinterは標準ライブラリ）
- 対象は `rename_app/app.py` の `render_inputs()` 内の全フォルダ欄のみ。「野菜名」欄は対象外
- 既存の `AppTest` スモークテスト（`rename_app/verify_app.py`）が壊れないこと。この検証ハーネスは pytest ではなく「実行して print/exit code で判定する」使い捨てスクリプトなので、新規チェックも同じ `check(name, cond)` 方式で追加する
- ダイアログを開けない環境（`TclError` 等）でもクラッシュせず、`st.error` 表示のみでテキスト欄は手入力継続できること

---

### Task 1: フォルダ選択ボタンの追加とテキスト欄の置き換え

**Files:**
- Modify: `rename_app/app.py`（先頭の import、`render_inputs()` 手前にヘルパー追加、`render_inputs()` 内の6箇所を置き換え）
- Modify: `rename_app/verify_app.py`（末尾に新規チェックを追加）

**Interfaces:**
- Consumes: `core.default_dataset_dir(veg_name)`, `core.NEW_DIR`, `core.RENAMED_DIR`, `core.LABELS_DIR`, `core.RECEIVED_IMAGES_DIR`, `core.RECEIVED_LABELS_DIR`（既存、`app.py` から既に参照済み）
- Produces: `folder_input(label: str, default: str, key: str) -> str`（他のUIコードから呼べる。戻り値は現在のテキスト欄の値）。ボタンの `key` は常に `f"{key}_browse"`（例: `dataset_dir` の欄なら `dataset_dir_browse`）— Task内・テスト側の両方でこの命名を使う。

- [ ] **Step 1: `verify_app.py` に新規チェックを追加する（実装より先に書く）**

`rename_app/verify_app.py` の末尾（`print()` の直前、`failed = [...]` より前）に以下を追加する:

```python
# ---- 📁 ボタン: 各モードの全フォルダ欄にボタンがある ----
FOLDER_KEYS_BY_MODE = {
    "rename": ["dataset_dir", "rename_img"],
    "merge": ["dataset_dir", "merge_img", "merge_lbl"],
    "import": ["dataset_dir", "import_img", "import_lbl"],
}
for mode, keys in FOLDER_KEYS_BY_MODE.items():
    at6 = fresh()
    at6.run()
    at6.radio(key="mode").set_value(mode)
    at6.run()
    for key in keys:
        check(f"{mode}: {key} に\U0001F4C1ボタンがある",
              has_button(at6, f"{key}_browse"))

# ---- 📁 選択後の値が反映される（tkinterダイアログを介さず session_state 経由で模擬）----
at7 = fresh()
at7.run()
at7.radio(key="mode").set_value("import")
at7.run()
picked = os.path.join(BASE, "picked_by_dialog")
at7.session_state["import_img"] = picked
at7.run()
check("\U0001F4C1 選択後の値がテキスト欄に反映される（session_state経由の模擬）",
      at7.text_input(key="import_img").value == picked)
```

（`\U0001F4C1` は 📁 のエスケープ表記。実際にファイルへ書く際はそのまま絵文字文字として書いてよい。）

- [ ] **Step 2: 実行して失敗することを確認する**

Run: `& "venv\Scripts\python.exe" rename_app\verify_app.py`（PowerShellから。venv未有効化でも直接パス指定で動く）
Expected: 新しく追加したチェック（`dataset_dir に📁ボタンがある` 等、計 3モード×フォルダ欄数 + 1件）が `NG` になり、`FAILED: N/...` で終了コード1。既存チェックは引き続き `OK`。

- [ ] **Step 3: `app.py` に `_pick_folder` と `folder_input` を実装する**

`rename_app/app.py` の先頭 import 部分を以下のように変更する（`import os` / `import sys` の下、`sys.path.insert` の前後はそのまま）:

```python
import os
import sys
import tkinter as tk
from tkinter import filedialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

import streamlit as st  # noqa: E402
```

`MODE_LABELS = {...}` の直後、`def render_inputs(...)` の直前に以下を追加する:

```python
def _pick_folder(initial_dir):
    """OSネイティブのフォルダ選択ダイアログを開き、選ばれた絶対パスを返す。
    キャンセル時は空文字列。ダイアログを開けない環境では例外を送出する。"""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askdirectory(initialdir=initial_dir or None)
    root.destroy()
    return path


def folder_input(label, default, key):
    """テキスト欄＋「フォルダを開く」ボタンを横並びで描画し、現在値を返す。"""
    col_text, col_btn = st.columns([5, 1])
    with col_text:
        value = st.text_input(label, st.session_state.get(key, default), key=key)
    with col_btn:
        if st.button("📁", key=f"{key}_browse", help="フォルダを開く"):
            try:
                picked = _pick_folder(st.session_state.get(key, default))
            except Exception as e:  # noqa: BLE001 (tkinter未対応環境などのフォールバック)
                st.error(f"フォルダ選択ダイアログを開けませんでした: {e}"
                         "（テキスト欄に直接入力してください）")
            else:
                if picked:
                    st.session_state[key] = picked
                    st.rerun()
    return value
```

- [ ] **Step 4: `render_inputs()` 内の6箇所を `folder_input(...)` に置き換える**

既存の `render_inputs()` を以下に置き換える（ロジックは変えず、`st.text_input` → `folder_input` の置き換えのみ）:

```python
def render_inputs(mode, veg_name):
    """モードごとの入力欄を描画し、パス dict を返す。"""
    dataset_dir = folder_input(
        "データセットのフォルダ", core.default_dataset_dir(veg_name), "dataset_dir")
    if mode == "rename":
        img_in = folder_input("新しい画像のフォルダ", core.NEW_DIR, "rename_img")
        return {"img_in": img_in, "lbl_in": None, "dataset_dir": dataset_dir}
    if mode == "merge":
        img_in = folder_input("リネーム済み画像のフォルダ (B)", core.RENAMED_DIR, "merge_img")
        lbl_in = folder_input("アノテーション txt のフォルダ (C)", core.LABELS_DIR, "merge_lbl")
        return {"img_in": img_in, "lbl_in": lbl_in, "dataset_dir": dataset_dir}
    img_in = folder_input("届いた画像のフォルダ", core.RECEIVED_IMAGES_DIR, "import_img")
    lbl_in = folder_input("届いた txt のフォルダ", core.RECEIVED_LABELS_DIR, "import_lbl")
    return {"img_in": img_in, "lbl_in": lbl_in, "dataset_dir": dataset_dir}
```

- [ ] **Step 5: 実行してすべて通ることを確認する**

Run: `& "venv\Scripts\python.exe" rename_app\verify_app.py`
Expected: `ALL CHECKS PASSED (N)`、終了コード0。Step 1 で追加したチェックも含め全件 `OK`。

- [ ] **Step 6: 手動スモークテスト（tkinterダイアログの実物確認）**

`AppTest` はGUI操作を自動化できないため、最後に人手で1回確認する:

1. リポジトリルートで venv を有効化: `venv\Scripts\activate`
2. `streamlit run rename_app\app.py`
3. ①②③それぞれのモードで、各フォルダ欄の「📁」ボタンを押し、OSのフォルダ選択ダイアログが最前面に開くこと、選んだフォルダの絶対パスがテキスト欄に反映されることを確認する
4. ダイアログでキャンセルした場合、テキスト欄の値が変わらないことを確認する
5. 反映されたパスのままプレビュー→実行の一往復が従来通り動くことを確認する（`datasets/` の実データではなく、テスト用の空フォルダなどで確認すること）

- [ ] **Step 7: コミット**

```bash
git add rename_app/app.py rename_app/verify_app.py
git commit -m "$(cat <<'EOF'
feat(rename_app): フォルダ入力欄にOSダイアログ選択ボタンを追加

各フォルダ欄にtkinterのフォルダ選択ダイアログを開く📁ボタンを追加し、
手入力に加えてOSネイティブダイアログからもパスを指定できるようにする。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage:** 設計書の「対象欄」表（dataset_dir / rename_img / merge_img / merge_lbl / import_img / import_lbl）は Step 4 の置き換えで全てカバー。「野菜名」欄は対象外のまま `st.text_input` を維持（変更していない）。エラーハンドリング（tkinter未対応環境）は Step 3 の `try/except` でカバー。テスト方針（ボタンクリックはしない・session_state先行セットで模擬）は Step 1 でカバー。手動確認は Step 6 でカバー。
- **Placeholder scan:** 実コードのみで「TODO」「後で」等の記述なし。
- **Type consistency:** `folder_input` の戻り値は `str`、呼び出し側の `img_in`/`lbl_in`/`dataset_dir` はいずれも既存コードと同じ変数名・同じ dict キーに代入しており、`build_plan`/`execute_plan`/`plan_rows` など後続関数のインターフェースは無変更。
