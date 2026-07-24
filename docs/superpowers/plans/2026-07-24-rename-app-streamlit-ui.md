# リネームアプリ Streamlit UI 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `rename_app/core.py` を無変更のまま、3ワークフロー（① リネーム / ② 取り込み merge / ③ 直接投入 import）を1画面のモード選択で操作できる Streamlit UI (`rename_app/app.py`) を作る。

**Architecture:** `app.py` は `core` を import する薄いUIラッパー。モードを `st.radio` で選び、モードごとの入力欄（フォルダパス）を出す。「プレビュー」ボタンで `build_*_plan`（無変更）を呼び結果を `st.session_state` に保持、問題がなければ「実行する」ボタンで `execute_*_plan` を呼ぶ。入力/モードが変わるとプレビューは自動的に無効化される。

**Tech Stack:** Python 3.11, Streamlit 1.52.1, Ultralytics（`core` 経由・UIは直接使わない）。テストは `streamlit.testing.v1.AppTest`（ブラウザ不要のヘッドレス）を素の Python スクリプトから実行（このリポジトリには pytest 等が未設定のため、既存 `verify_rename_app.py` と同じ「素のスクリプト＋assert＋OK/NG 出力」方式に合わせる）。

## Global Constraints

- `rename_app/core.py` は**一切変更しない**。
- 実データ (`datasets/`) と実 staging (`rename_app/data_staging/`) を壊さない。テストは必ずテスト専用の一時フォルダを使い、`core.RENAMED_DIR` / `core.LABELS_DIR` / `core.LOG_FILE` をテスト用に差し替えてから実行する。
- 起動コマンドは `streamlit run rename_app\app.py`（リポジトリルートで venv 有効化後）。
- Python 実行は `venv/Scripts/python.exe`。
- UI 文言は日本語。既存 CLI と同じ情報（無視ファイル・既存番号・train/val 件数・空txt警告・ログパス）を出す。
- 問題（`problems`）が1件でもあればプレビューで中断し、「実行する」ボタンを出さない＝ファイルに一切変更を入れない。
- 既存 CLI（`rename_new_images.py` / `merge_to_dataset.py`）は残す。

## core.py が提供する既存インターフェース（変更不可・参照用）

```python
# 定数
core.NEW_DIR, core.RECEIVED_IMAGES_DIR, core.RECEIVED_LABELS_DIR
core.RENAMED_DIR, core.LABELS_DIR, core.DATASETS_ROOT
core.DEFAULT_VEG_NAME  # "daikon"
core.LOG_FILE

core.default_dataset_dir(veg_name) -> str            # DATASETS_ROOT/<veg_name>
core.count_dataset_images(dataset_dir) -> {"train": int, "val": int}  # 存在する split のみ

# ① リネーム（mode="1" は画像のみ／out 先は既定で RENAMED_DIR, LABELS_DIR）
core.build_rename_plan(mode, img_in_dir, lbl_in_dir, dataset_dir, veg_name,
                       out_images_dir=None, out_labels_dir=None) -> dict
#   dict: problems[], ignored[], plan[(旧画像,旧txt or None,新画像,新txt or None)],
#         n_train, n_val, max_num{"train","val"}
core.execute_rename_plan(plan, mode, img_in_dir, lbl_in_dir,
                         out_images_dir=None, out_labels_dir=None, log_file=None) -> [str]

# ② 取り込み merge（B=画像, C=txt → dataset へ「移動」。リネームしない）
core.build_merge_plan(images_dir, labels_dir, dataset_dir, veg_name) -> dict
#   dict: problems[], ignored[], plan[(split, 画像, txt)], n_train, n_val, empty_txts[]
core.execute_merge_plan(plan, images_dir, labels_dir, dataset_dir, log_file=None) -> [str]

# ③ 直接投入 import（届いたペアをリネームして dataset へコピー投入）
core.build_import_plan(images_dir, labels_dir, dataset_dir, veg_name,
                       staging_images_dir=None, staging_labels_dir=None) -> dict
#   dict: problems[], ignored[], plan[(旧画像,旧txt,新画像,新txt,split)],
#         n_train, n_val, max_num{"train","val"}, empty_txts[]
core.execute_import_plan(plan, images_dir, labels_dir, dataset_dir, log_file=None) -> [str]
```

## ファイル構成

- Create: `rename_app/app.py` — Streamlit UI 本体
- Create: `rename_app/verify_app.py` — AppTest による通し検証スクリプト（使い捨て・実データ非対象）
- Modify: `rename_app/README.md` — 起動方法に Streamlit アプリを追記

---

### Task 1: app.py の骨組み（モード選択・入力欄・状態機構）と ① リネームのプレビュー→実行

**Files:**
- Create: `rename_app/app.py`
- Create: `rename_app/verify_app.py`

**Interfaces:**
- Consumes: `core`（上記の既存インターフェース全部）
- Produces（後続タスクが依存する `app.py` 内の関数）:
  - `render_inputs(mode: str, veg_name: str) -> dict`（`{"img_in", "lbl_in" or None, "dataset_dir"}`）
  - `build_plan(mode, veg_name, inputs) -> dict`
  - `execute_plan(mode, veg_name, inputs, plan) -> list[str]`
  - `plan_rows(mode, plan) -> list[dict]`
  - `signature(mode, veg_name, inputs) -> tuple`
  - `main() -> None`
  - モード識別子は `"rename"` / `"merge"` / `"import"`
  - ウィジェット key: `mode` / `veg` / `dataset_dir` / `rename_img` / `merge_img` / `merge_lbl` / `import_img` / `import_lbl` / `preview_btn` / `execute_btn`

- [ ] **Step 1: 検証スクリプト `verify_app.py` に ① の失敗するテストを書く**

`rename_app/verify_app.py` を新規作成（この時点で app.py が無いので失敗する）:

```python
"""app.py の通し検証（AppTest・使い捨て）。実データ・実 staging には触らない。"""
import os
import shutil
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
import core
from streamlit.testing.v1 import AppTest

BASE = os.path.join(APP_DIR, "app_verify_work")
if os.path.isdir(BASE):
    shutil.rmtree(BASE)

NEW = os.path.join(BASE, "1_new")
RENAMED = os.path.join(BASE, "2_renamed")
LABELS = os.path.join(BASE, "3_labels")
RCV_IMG = os.path.join(BASE, "received", "images")
RCV_LBL = os.path.join(BASE, "received", "labels")
DS = os.path.join(BASE, "datasets", "daikon")
LOG = os.path.join(BASE, "rename_log.txt")

# core の staging 系定数をテスト用に差し替え（実 staging / 実ログを汚さない）
core.RENAMED_DIR = RENAMED
core.LABELS_DIR = LABELS
core.LOG_FILE = LOG

APP = os.path.join(APP_DIR, "app.py")

checks = []


def check(name, cond):
    checks.append((name, cond))
    print(("OK  " if cond else "NG  ") + name)


def write(path, text="dummy"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def has_button(at, key):
    return any(b.key == key for b in at.button)


def fresh():
    return AppTest.from_file(APP, default_timeout=60)


# ---- ① rename: preview → execute ----
for i in range(5):
    write(os.path.join(NEW, f"photo{i}.jpg"))
at = fresh()
at.run()
at.radio(key="mode").set_value("rename")
at.text_input(key="veg").set_value("daikon")
at.text_input(key="dataset_dir").set_value(DS)
at.text_input(key="rename_img").set_value(NEW)
at.run()
at.button(key="preview_btn").click().run()
check("① preview: 例外なし", len(at.exception) == 0)
check("① preview: エラー表示なし", len(at.error) == 0)
check("① preview: 実行ボタンが出る", has_button(at, "execute_btn"))
at.button(key="execute_btn").click().run()
check("① execute: 例外なし", len(at.exception) == 0)
check("① execute: 成功メッセージ", len(at.success) >= 1)
check("① execute: staging に5枚コピー", len(os.listdir(RENAMED)) == 5)
check("① execute: 元は processed へ退避",
      os.path.isdir(os.path.join(NEW, "processed"))
      and len(os.listdir(os.path.join(NEW, "processed"))) == 5)

# ---- ① 入力変更でプレビュー無効化 ----
at2 = fresh()
at2.run()
at2.text_input(key="dataset_dir").set_value(DS)
at2.text_input(key="rename_img").set_value(NEW)
at2.run()
at2.button(key="preview_btn").click().run()
had = has_button(at2, "execute_btn")
at2.text_input(key="rename_img").set_value(os.path.join(BASE, "changed"))
at2.run()
check("① 入力変更前は実行ボタンあり / 変更後は消える",
      had and not has_button(at2, "execute_btn"))

print()
failed = [n for n, c in checks if not c]
if failed:
    print(f"FAILED: {len(failed)}/{len(checks)}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({len(checks)})")
```

- [ ] **Step 2: 実行して失敗を確認**

Run: `venv/Scripts/python.exe rename_app/verify_app.py`
Expected: FAIL（`app.py` が無く `AppTest.from_file` がエラー、または非ゼロ終了）

- [ ] **Step 3: `rename_app/app.py` を作成（骨組み + ① 対応の全機構）**

```python
"""データセット リネームツールの Streamlit UI。

core.py の build/execute をそのまま呼ぶ薄いラッパー。
起動: リポジトリルートで venv 有効化後 `streamlit run rename_app\app.py`
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

import streamlit as st  # noqa: E402

MODE_LABELS = {
    "rename": "① リネーム（自分で集めた画像 → staging で待機）",
    "merge": "② 取り込み（staging の画像+txt → dataset へ移動）",
    "import": "③ 直接投入（届いたアノテ済みペア → dataset へ）",
}


def render_inputs(mode, veg_name):
    """モードごとの入力欄を描画し、パス dict を返す。"""
    dataset_dir = st.text_input(
        "データセットのフォルダ", core.default_dataset_dir(veg_name),
        key="dataset_dir")
    if mode == "rename":
        img_in = st.text_input("新しい画像のフォルダ", core.NEW_DIR, key="rename_img")
        return {"img_in": img_in, "lbl_in": None, "dataset_dir": dataset_dir}
    if mode == "merge":
        img_in = st.text_input("リネーム済み画像のフォルダ (B)", core.RENAMED_DIR,
                               key="merge_img")
        lbl_in = st.text_input("アノテーション txt のフォルダ (C)", core.LABELS_DIR,
                               key="merge_lbl")
        return {"img_in": img_in, "lbl_in": lbl_in, "dataset_dir": dataset_dir}
    img_in = st.text_input("届いた画像のフォルダ", core.RECEIVED_IMAGES_DIR,
                           key="import_img")
    lbl_in = st.text_input("届いた txt のフォルダ", core.RECEIVED_LABELS_DIR,
                           key="import_lbl")
    return {"img_in": img_in, "lbl_in": lbl_in, "dataset_dir": dataset_dir}


def build_plan(mode, veg_name, inputs):
    if mode == "rename":
        return core.build_rename_plan("1", inputs["img_in"], inputs["lbl_in"],
                                      inputs["dataset_dir"], veg_name)
    if mode == "merge":
        return core.build_merge_plan(inputs["img_in"], inputs["lbl_in"],
                                     inputs["dataset_dir"], veg_name)
    return core.build_import_plan(inputs["img_in"], inputs["lbl_in"],
                                  inputs["dataset_dir"], veg_name)


def execute_plan(mode, veg_name, inputs, plan):
    if mode == "rename":
        return core.execute_rename_plan(plan, "1", inputs["img_in"],
                                        inputs["lbl_in"])
    if mode == "merge":
        return core.execute_merge_plan(plan, inputs["img_in"], inputs["lbl_in"],
                                       inputs["dataset_dir"])
    return core.execute_import_plan(plan, inputs["img_in"], inputs["lbl_in"],
                                    inputs["dataset_dir"])


def plan_rows(mode, plan):
    if mode == "rename":
        return [{"旧名": img, "新名": new_img}
                for img, txt, new_img, new_txt in plan]
    if mode == "merge":
        return [{"split": split, "画像": img, "txt": lbl}
                for split, img, lbl in plan]
    return [{"旧名": img, "split": split, "新名": new_img}
            for img, txt, new_img, new_txt, split in plan]


def signature(mode, veg_name, inputs):
    return (mode, veg_name,
            tuple(sorted((k, str(v)) for k, v in inputs.items())))


def main():
    st.title("データセット リネームツール 🥬")
    mode = st.radio("モードを選択", options=list(MODE_LABELS.keys()),
                    format_func=lambda m: MODE_LABELS[m], key="mode")
    veg_name = st.text_input("野菜名 (prefix)", core.DEFAULT_VEG_NAME, key="veg")
    inputs = render_inputs(mode, veg_name)
    sig = signature(mode, veg_name, inputs)

    if st.button("プレビュー", key="preview_btn"):
        st.session_state["preview"] = {
            "sig": sig, "result": build_plan(mode, veg_name, inputs)}

    preview = st.session_state.get("preview")
    if not preview or preview["sig"] != sig:
        st.info("入力を設定して「プレビュー」を押してください。"
                "（入力やモードを変更するとプレビューは無効になります）")
        return

    result = preview["result"]
    if result["ignored"]:
        st.info("無視した対象外ファイル: " + ", ".join(result["ignored"]))
    if result["problems"]:
        st.error(f"問題が {len(result['problems'])} 件あります（何も変更していません）:")
        for p in result["problems"]:
            st.write("- " + p)
        return

    if "max_num" in result:
        mn = result["max_num"]
        st.write(f"既存の番号: train {mn['train']:03d} まで / val {mn['val']:03d} まで")
    st.write(f"プレビュー: {len(result['plan'])} 件"
             f"（train {result['n_train']} / val {result['n_val']}）")
    st.dataframe(plan_rows(mode, result["plan"]))
    if result.get("empty_txts"):
        st.warning(f"中身が空の txt が {len(result['empty_txts'])} 件"
                   "（検出対象なしの背景画像として扱われます）: "
                   + ", ".join(result["empty_txts"]))

    if st.button("実行する", key="execute_btn"):
        try:
            done = execute_plan(mode, veg_name, inputs, result["plan"])
        except Exception as e:  # noqa: BLE001
            st.error(f"実行中にエラーが発生しました: {e}")
            return
        st.success(f"完了！ {len(done)} 件を処理しました。")
        for line in done:
            st.write("- " + line)
        if mode in ("merge", "import"):
            for split, total in core.count_dataset_images(
                    inputs["dataset_dir"]).items():
                st.write(f"{split}: 合計 {total} 枚")
        if mode == "rename":
            st.write(f"次: {core.RENAMED_DIR} をアノテして "
                     f"txt を {core.LABELS_DIR} へ保存してください。")
        st.write(f"記録: {core.LOG_FILE}")
        del st.session_state["preview"]


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 実行して ① のチェックが通ることを確認**

Run: `venv/Scripts/python.exe rename_app/verify_app.py`
Expected: PASS（`ALL CHECKS PASSED (8)`。① の 7 チェック + 状態無効化 1 チェック）

- [ ] **Step 5: コミット**

```bash
git add rename_app/app.py rename_app/verify_app.py
git commit -m "feat(rename_app): Streamlit UI の骨組みと①リネームを実装"
```

---

### Task 2: ② 取り込み（merge）のプレビュー→実行

**Files:**
- Modify: `rename_app/verify_app.py`（②のチェックを追記）
- （`app.py` は Task 1 で `merge` 分岐を実装済み。原則追加変更なし。②が通らなければ `app.py` を修正する）

**Interfaces:**
- Consumes: Task 1 の `app.py`（`merge` モード分岐、`build_merge_plan` / `execute_merge_plan`）
- Produces: なし（検証の追加）

- [ ] **Step 1: `verify_app.py` に ② の失敗するテストを追記**

`verify_app.py` の `print()` 直前（`# ---- ① 入力変更...` ブロックの後、集計の前）に以下を挿入する:

```python
# ---- ② merge: staging(B/C) → dataset へ移動 ----
# ①で RENAMED(=B) に daikon_train/val_*.jpg が5枚できている。対応する txt を C に作る
stems = [os.path.splitext(f)[0] for f in sorted(os.listdir(RENAMED))]
for i, stem in enumerate(stems):
    write(os.path.join(LABELS, stem + ".txt"),
          "" if i == 0 else "0 0.5 0.5 0.2 0.2\n")
at3 = fresh()
at3.run()
at3.radio(key="mode").set_value("merge")
at3.run()
at3.text_input(key="veg").set_value("daikon")
at3.text_input(key="dataset_dir").set_value(DS)
at3.text_input(key="merge_img").set_value(RENAMED)
at3.text_input(key="merge_lbl").set_value(LABELS)
at3.run()
at3.button(key="preview_btn").click().run()
check("② preview: 例外なし", len(at3.exception) == 0)
check("② preview: エラー表示なし", len(at3.error) == 0)
check("② preview: 実行ボタンが出る", has_button(at3, "execute_btn"))
check("② preview: 空txt警告が1件", len(at3.warning) >= 1)
at3.button(key="execute_btn").click().run()
check("② execute: 成功メッセージ", len(at3.success) >= 1)
check("② execute: B/C が空になった",
      os.listdir(RENAMED) == [] and os.listdir(LABELS) == [])
check("② execute: dataset 合計5枚",
      sum(core.count_dataset_images(DS).values()) == 5)
```

- [ ] **Step 2: 実行して ② のチェックが通ることを確認**

Run: `venv/Scripts/python.exe rename_app/verify_app.py`
Expected: PASS（`ALL CHECKS PASSED (15)`。① 8 + ② 7）。もし ② が失敗する場合は `app.py` の `merge` 分岐（`render_inputs` / `build_plan` / `execute_plan` / `plan_rows`）を Interfaces 記載のシグネチャに合わせて修正してから再実行する。

- [ ] **Step 3: コミット**

```bash
git add rename_app/verify_app.py rename_app/app.py
git commit -m "test(rename_app): Streamlit UI ②取り込み(merge)の検証を追加"
```

---

### Task 3: ③ 直接投入（import）のプレビュー→実行 と エラー系

**Files:**
- Modify: `rename_app/verify_app.py`（③と問題系のチェックを追記）
- （`app.py` は Task 1 で `import` 分岐を実装済み。原則追加変更なし）

**Interfaces:**
- Consumes: Task 1 の `app.py`（`import` モード分岐、`build_import_plan` / `execute_import_plan`）
- Produces: なし（検証の追加）

- [ ] **Step 1: `verify_app.py` に ③ と問題系の失敗するテストを追記**

Task 2 で追記した ② ブロックの後（`print()` の前）に以下を挿入する:

```python
# ---- ③ import: 届いたペアを dataset へ直接投入（②で dataset に5枚ある続き番号になる）----
write(os.path.join(RCV_IMG, "recv_a.jpg"))
write(os.path.join(RCV_IMG, "recv_b.jpg"))
write(os.path.join(RCV_LBL, "recv_a.txt"), "0 0.5 0.5 0.1 0.1\n")
write(os.path.join(RCV_LBL, "recv_b.txt"), "")
at4 = fresh()
at4.run()
at4.radio(key="mode").set_value("import")
at4.run()
at4.text_input(key="veg").set_value("daikon")
at4.text_input(key="dataset_dir").set_value(DS)
at4.text_input(key="import_img").set_value(RCV_IMG)
at4.text_input(key="import_lbl").set_value(RCV_LBL)
at4.run()
at4.button(key="preview_btn").click().run()
check("③ preview: 例外なし", len(at4.exception) == 0)
check("③ preview: 実行ボタンが出る", has_button(at4, "execute_btn"))
check("③ preview: 空txt警告あり", len(at4.warning) >= 1)
at4.button(key="execute_btn").click().run()
check("③ execute: 成功メッセージ", len(at4.success) >= 1)
check("③ execute: dataset 合計7枚",
      sum(core.count_dataset_images(DS).values()) == 7)
check("③ execute: 元は processed へ退避",
      os.path.isdir(os.path.join(RCV_IMG, "processed"))
      and os.path.isdir(os.path.join(RCV_LBL, "processed")))

# ---- 問題系: import でペア欠け（txtのない画像）→ 実行ボタンを出さない＝無変更 ----
write(os.path.join(RCV_IMG, "recv_c.jpg"))  # 対応txtなし
at5 = fresh()
at5.run()
at5.radio(key="mode").set_value("import")
at5.run()
at5.text_input(key="dataset_dir").set_value(DS)
at5.text_input(key="import_img").set_value(RCV_IMG)
at5.text_input(key="import_lbl").set_value(RCV_LBL)
at5.run()
at5.button(key="preview_btn").click().run()
check("問題系: エラー表示が出る", len(at5.error) >= 1)
check("問題系: 実行ボタンを出さない", not has_button(at5, "execute_btn"))
```

- [ ] **Step 2: 実行して全チェックが通ることを確認**

Run: `venv/Scripts/python.exe rename_app/verify_app.py`
Expected: PASS（`ALL CHECKS PASSED (23)`。① 8 + ② 7 + ③ 6 + 問題系 2）。失敗する場合は `app.py` の `import` 分岐を修正してから再実行する。

- [ ] **Step 3: コミット**

```bash
git add rename_app/verify_app.py rename_app/app.py
git commit -m "test(rename_app): Streamlit UI ③直接投入(import)とエラー系の検証を追加"
```

---

### Task 4: README への起動方法追記と手動起動確認

**Files:**
- Modify: `rename_app/README.md`

**Interfaces:**
- Consumes: `rename_app/app.py`
- Produces: なし

- [ ] **Step 1: README に Streamlit アプリの節を追記**

`rename_app/README.md` の「## 使い方」直下（`python rename_app\rename_new_images.py` などの CLI 起動例が並ぶコードブロックの後）に、次の節を挿入する:

```markdown
### Streamlit アプリ（CLIと同じ操作をGUIで）

CLI と同じ3ワークフローを1画面で操作できる GUI。ロジックは同じ `core.py`。

```
venv\Scripts\activate
streamlit run rename_app\app.py
```

上部のモード選択（① リネーム / ② 取り込み / ③ 直接投入）を切り替え、各フォルダパスと
野菜名を入力して「プレビュー」→内容を確認して「実行する」。入力やモードを変更すると
プレビューは無効になる（古い内容での実行を防ぐため）。問題が1件でもあればプレビューで
中断し、ファイルには一切変更を加えない。
```

- [ ] **Step 2: 手動で起動して目視確認（任意だが推奨）**

Run: `venv/Scripts/python.exe -m streamlit run rename_app/app.py`
Expected: ブラウザでアプリが開き、モード選択・入力欄・「プレビュー」ボタンが表示される。確認したら Ctrl+C で停止。
（ヘッドレス自動確認は Task 1-3 の `verify_app.py` で担保済みのため、この目視は省略可。）

- [ ] **Step 3: コミット**

```bash
git add rename_app/README.md
git commit -m "docs(rename_app): README に Streamlit アプリの起動方法を追記"
```

---

## テスト用一時フォルダの後片付けについて

`verify_app.py` は `rename_app/app_verify_work/` を作って使う（実行のたびに先頭で削除して作り直す）。
コミットに含めたくない場合は `.gitignore` に `rename_app/app_verify_work/` を追加してよい（任意・ユーザー判断）。
`git add` は各タスクで対象ファイルを明示しているため、明示的に add しない限りこの作業フォルダは混入しない。
