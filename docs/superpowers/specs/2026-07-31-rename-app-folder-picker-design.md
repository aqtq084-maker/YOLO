# 設計: rename_app Streamlit UI のフォルダ選択ダイアログ化

日付: 2026-07-31
対象: `rename_app/app.py` の全フォルダ入力欄

## 背景・目的

`rename_app/app.py`（[2026-07-24 設計](2026-07-24-rename-app-streamlit-ui-design.md)で追加）は、
データセットフォルダや届いた画像/txtフォルダなどを全て `st.text_input` でのパス手入力にしている。
パスをコピー＆ペーストする手間や打ち間違いを減らすため、テキスト欄の横に「フォルダを開く」ボタンを
追加し、OSネイティブのフォルダ選択ダイアログでパスを入力できるようにする。

## スコープ

`render_inputs()` 内の全フォルダ入力欄を対象にする（①②③の全モード共通）:

| モード | 対象欄 |
|---|---|
| 共通 | データセットのフォルダ (`dataset_dir`) |
| ① リネーム | 新しい画像のフォルダ (`rename_img`) |
| ② 取り込み | リネーム済み画像のフォルダ B (`merge_img`) / アノテーション txt のフォルダ C (`merge_lbl`) |
| ③ 直接投入 | 届いた画像のフォルダ (`import_img`) / 届いた txt のフォルダ (`import_lbl`) |

「野菜名 (prefix)」欄はフォルダパスではないため対象外。

### 非スコープ

- ブラウザ経由のファイル/フォルダアップロード化（ブラウザの `<input type=file>` はフルパスを
  返さないため不採用。今回はローカルPCで `streamlit run` する前提を維持）
- `core.py` の変更
- `requirements.txt` の変更（`tkinter` は標準ライブラリのため追加不要）
- モード選択・プレビュー/実行フローなど、フォルダ選択以外のUI挙動

## アーキテクチャ

`app.py` に以下を追加する（`core.py` は無変更）:

```python
import tkinter as tk
from tkinter import filedialog

def _pick_folder(initial_dir):
    """OSネイティブのフォルダ選択ダイアログを開き、選ばれた絶対パスを返す。
    キャンセル時は空文字列。ダイアログを開けない環境では TclError 等を送出する。"""
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
            except Exception as e:  # noqa: BLE001  (tkinter未対応環境などのフォールバック)
                st.error(f"フォルダ選択ダイアログを開けませんでした: {e}"
                         "（テキスト欄に直接入力してください）")
            else:
                if picked:
                    st.session_state[key] = picked
                    st.rerun()
    return value
```

`render_inputs()` 内の対象欄を、既存の `st.text_input(...)` 呼び出しから
`folder_input(...)` 呼び出しに差し替える（引数は同じ `label, default, key`）。

## 状態管理

- ボタン押下時にダイアログで選んだパスを `st.session_state[key]` へ書き込んでから
  `st.rerun()` する（Streamlitの「ウィジェット生成前に session_state を更新する」正規パターン）。
- 次の実行で `text_input` が同じ `key` を持つため、書き込んだパスが初期値として自動的に反映される。
- ダイアログをキャンセルした場合（`picked == ""`）は何もせず、既存のテキスト欄の値をそのまま保持する。

## エラーハンドリング

- ディスプレイのない環境やtkinter未対応環境で `_pick_folder` が例外（`TclError` 等）を送出した場合、
  `st.error` でメッセージを表示し、テキスト欄は従来通り手入力で使い続けられる。
- ファイルシステムへの書き込みは発生しない（フォルダを選ぶだけ）ため、既存の
  「`core.py` 無変更・実データは壊さない」という前提に影響しない。

## テスト

- 既存の `streamlit.testing.v1.AppTest` スモークテストは「📁」ボタンをクリックしないため、
  tkinterのGUI呼び出しは実行時に発生せず、そのまま通る想定。
- 新規に `folder_input()` 単体のロジックテストは、tkinterのモーダルダイアログをテスト環境で
  自動操作するのが困難なため追加しない。`_pick_folder` を直接呼ばず `st.session_state[key]` を
  外から差し込んだ状態で `folder_input()` がその値を初期値として使うことだけ、
  `AppTest` 経由で確認する（ボタン押下はしない）。
- 最終確認として `streamlit run rename_app\app.py` を実行し、①②③すべてのフォルダ欄で
  ボタンからOSダイアログが開き、選んだパスがテキスト欄に反映されることを目視確認する。

## 受け入れ条件

- ①②③全モードの全フォルダ入力欄に「📁」ボタンがあり、押すとOSのフォルダ選択ダイアログが開く
- 選んだフォルダの絶対パスがテキスト欄に反映される
- テキスト欄への直接入力・編集は従来通り可能
- ダイアログを開けない環境でもエラー表示のみでクラッシュせず、手入力で続行できる
- 既存の `AppTest` スモークテストが全て通る
- `core.py` は無変更
