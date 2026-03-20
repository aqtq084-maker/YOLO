import streamlit as st
from PIL import Image
import io
from detector import KomatsunaDetector  # 作成したファイルを読み込む

# --- 1. 初期設定 ---
MODEL_PATH = r'C:\YOLO_New_Project\3vegetables\best.pt'

# 判定エンジンの起動
if 'detector' not in st.session_state:
    st.session_state.detector = KomatsunaDetector(MODEL_PATH)

st.set_page_config(page_title="野菜検知アプリ", layout="wide")
st.title("🥬 野菜（小松菜・大根・ラディッシュ）判定アプリ")

# --- 2. サイドバーメニュー ---
st.sidebar.header("メニュー")
mode = st.sidebar.selectbox("入力方法を選択", ["アルバムから選ぶ", "カメラで撮影"])
conf_threshold = st.sidebar.slider("確信度のしきい値", 0.0, 1.0, 0.4, 0.05)

# 入力ソースの決定
input_file = None
if mode == "アルバムから選ぶ":
    input_file = st.file_uploader("判別したい画像を選んでください...", type=['jpg', 'jpeg', 'png'])
else:
    input_file = st.camera_input("対象の野菜を撮影してください")

# --- 3. メイン処理 ---
if input_file is not None:
    image = Image.open(input_file)

    # シンプルに画像と確信度だけ渡す
    # 分離したdetectorを使って判定
    res_img, count, df_data = st.session_state.detector.process_frame(image, conf_threshold)

    # レイアウト表示
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📸 元画像")
        st.image(image, use_container_width=True)
    with col2:
        st.subheader("🔍 AI判定結果")
        st.image(res_img, caption=f"検知数: {count} 株", use_container_width=True)

    # 診断レポート
    st.divider()
    st.subheader(f"📊 診断レポート: 合計 {count} 株")
    if count > 0:
        st.table(df_data)
    else:
        st.warning("対象の野菜が見つかりませんでした。")

    # ダウンロード機能
    res_pil = Image.fromarray(res_img)
    buf = io.BytesIO()
    res_pil.save(buf, format="PNG")
    st.download_button("📥 判定結果をダウンロード", buf.getvalue(), "result.png", "image/png")