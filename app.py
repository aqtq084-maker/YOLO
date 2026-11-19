"""Run with: python -m streamlit run app.py"""

from collections import Counter
import hashlib
from pathlib import Path
from threading import Lock
import warnings

import streamlit as st
from PIL import Image, UnidentifiedImageError

from vegetable_detector import (
    MODEL_DIR, annotate_image, csv_bytes, detection_rows, discover_models,
    png_bytes, read_image,
)

st.set_page_config(page_title="野菜の判定", page_icon="🥬", layout="wide")


@st.cache_resource(max_entries=2, show_spinner=False)
def load_model(path: str, modified_ns: int, size: int):
    # File metadata invalidates the cache when weights are replaced in place.
    from ultralytics import YOLO

    model = YOLO(path, task="detect")
    if model.task != "detect":
        raise ValueError("物体検出用のモデル（detect）の .pt ファイルを選択してください。")
    return model, Lock()


def main():
    st.title("🥬 野菜の判定")
    st.write("写真を選んで、野菜の種類と個数を確認しましょう。")
    st.caption("判定対象は選択したモデルの学習クラスです。信頼度は正解の確率を保証する値ではありません。")

    with st.sidebar:
        st.header("判定設定")
        st.button("モデル一覧を再読み込み", width="stretch")
        try:
            models = discover_models()
        except OSError as error:
            st.error(f"モデル一覧を取得できませんでした: {error}")
            st.stop()
        if not models:
            st.info("モデルを配置すると判定を始められます。")
            st.code(str(MODEL_DIR / "vegetables" / "weights" / "best.pt"), language=None)
            st.caption("runs\\detect の直下・サブフォルダにある .pt ファイルを自動で探します。")
            st.stop()
        selected_path = st.selectbox(
            "使用するモデル", [str(model.path) for model in models],
            format_func=lambda value: str(Path(value).relative_to(MODEL_DIR)),
        )
        selected = next(model for model in models if str(model.path) == selected_path)
        st.caption("best.pt を優先し、同じ種類では更新日時の新しい順に表示します。")
        confidence = st.slider("検出する信頼度の下限 (%)", 5, 95, 40, 5)
        device = st.selectbox("実行環境", ["cpu", "auto"],
                              format_func=lambda value: "CPU" if value == "cpu" else "自動（GPUがあれば使用）")
        st.caption("モデルを追加・上書きしたら、一覧を再読み込みしてください。")

    try:
        with st.spinner("モデルを読み込んでいます…"):
            model, model_lock = load_model(str(selected.path), selected.modified_ns, selected.size)
        with st.expander("このモデルが判定できるクラス"):
            names = model.names
            st.write("、".join(str(name) for name in (names.values() if isinstance(names, dict) else names)))
    except Exception as error:
        st.error("モデルを読み込めませんでした。学習済みの物体検出モデルを選択してください。")
        st.code(str(error), language=None)
        st.stop()

    source = st.radio("画像の入力方法", ["画像をアップロード", "カメラで撮影"], horizontal=True)
    if source == "画像をアップロード":
        image_file = st.file_uploader("野菜の写真を選択", type=["jpg", "jpeg", "png", "webp"],
                                      help="JPEG・PNG・WebP、20MB以下、2,400万画素以下")
    else:
        image_file = st.camera_input("野菜を撮影してください")
    if image_file is None:
        st.info("写真を用意して「野菜を判定する」を押してください。")
        return
    if image_file.size > 20 * 1024 * 1024:
        st.error("画像は20MB以下にしてください。")
        return
    data = image_file.getvalue()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = read_image(data)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        st.error(f"画像を開けませんでした。別の画像を選んでください。 {error}")
        return

    request_key = (str(selected.path), selected.modified_ns, selected.size, confidence, device,
                   hashlib.sha256(data).hexdigest())
    if st.session_state.get("request_key") != request_key:
        st.session_state.pop("prediction", None)
        st.session_state["request_key"] = request_key
    if st.button("野菜を判定する", type="primary", width="stretch"):
        st.session_state.pop("prediction", None)
        try:
            with st.spinner("画像を判定しています…"):
                with model_lock:
                    result = model.predict(source=image, conf=confidence / 100,
                                           device="cpu" if device == "cpu" else None,
                                           save=False, verbose=False)[0]
                    rows = detection_rows(result)
                annotated = annotate_image(image, rows)
            st.session_state["prediction"] = {"rows": rows, "png": png_bytes(annotated)}
        except Exception as error:
            st.error("判定に失敗しました。モデルと画像を確認してください。GPUで失敗する場合はCPUを選んでください。")
            st.code(str(error), language=None)

    prediction = st.session_state.get("prediction")
    if prediction is None:
        st.image(image, caption="判定する画像", width="stretch")
        return
    rows = prediction["rows"]
    counts = Counter(row["クラス"] for row in rows)
    total, kinds = st.columns(2)
    total.metric("検出した個数", f"{len(rows)} 個")
    kinds.metric("検出した種類", f"{len(counts)} 種類")
    original_col, result_col = st.columns(2)
    original_col.image(image, caption="元の画像", width="stretch")
    result_col.image(prediction["png"], caption="判定結果", width="stretch")
    if rows:
        st.subheader("種類ごとの個数")
        st.dataframe([{"クラス": name, "個数": count} for name, count in counts.items()],
                     hide_index=True, width="stretch")
        with st.expander("検出の詳細"):
            st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.warning("対象を検出できませんでした。写真やモデルを変えるか、信頼度の下限を下げてお試しください。")
    image_download, csv_download = st.columns(2)
    image_download.download_button("結果画像を保存", prediction["png"],
                                   file_name="vegetable_result.png", mime="image/png")
    csv_download.download_button("検出一覧をCSVで保存", csv_bytes(rows),
                                 file_name="vegetable_detections.csv", mime="text/csv")


if __name__ == "__main__":
    main()
