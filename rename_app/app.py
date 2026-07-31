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


def _pick_folder(initial_dir):
    """OSネイティブのフォルダ選択ダイアログを開き、選ばれた絶対パスを返す。
    キャンセル時は空文字列。ダイアログを開けない環境では例外を送出する。"""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    try:
        root.withdraw()
        root.attributes("-topmost", True)
        return filedialog.askdirectory(initialdir=initial_dir or None)
    finally:
        root.destroy()


def folder_input(label, default, key):
    """テキスト欄＋「フォルダを開く」ボタンを横並びで描画し、現在値を返す。

    ボタンの click 処理（session_state 書き込み・rerun）は、同じ key を持つ
    text_input がこのスクリプト実行内でまだ生成されていない時点で行う必要が
    ある（Streamlitは「同一run内で既に生成済みのwidgetのkeyへの書き込み」を
    例外にするため）。そのため col_btn の処理を先に、col_text の
    st.text_input を後に実行する（表示上の左右の並びは st.columns の列の
    順序で決まり、コードの実行順序とは無関係）。
    """
    if key not in st.session_state:
        st.session_state[key] = default
    col_text, col_btn = st.columns([5, 1], vertical_alignment="bottom")
    with col_btn:
        clicked = st.button("📁", key=f"{key}_browse", help="フォルダを開く")
    if clicked:
        try:
            picked = _pick_folder(st.session_state.get(key, default))
        except Exception as e:  # noqa: BLE001 (tkinter未対応環境などのフォールバック)
            st.error(f"フォルダ選択ダイアログを開けませんでした: {e}"
                     "（テキスト欄に直接入力してください）")
        else:
            if picked:
                st.session_state[key] = picked
                st.rerun()
    with col_text:
        value = st.text_input(label, key=key)
    return value


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
