import streamlit as st
from PIL import Image
import io
# detectorからクラスを読み込む（detector内部でvisualizerを使う）
from detector import KomatsunaDetector  # 作成したファイルを読み込む

# --- 1. 初期設定 ---
# ここはあなたの環境に合わせてください
MODEL_PATH = r'C:\YOLO_New_Project\3vegetables\best.pt'

# 判定エンジンの起動
if 'detector' not in st.session_state:
    st.session_state.detector = KomatsunaDetector(MODEL_PATH)

st.set_page_config(page_title="小松菜検知アプリ", layout="wide")
st.title("🥬 小松菜カウント & 診断アプリ")

# --- 2. サイドバーメニュー ---
st.sidebar.header("メニュー")
mode = st.sidebar.selectbox("入力方法を選択", ["アルバムから選ぶ", "カメラで撮影"])
conf_threshold = st.sidebar.slider("確信度のしきい値", 0.0, 1.0, 0.4, 0.05)

# 🌟 小松菜の色（緑色）の判定調整を追加
st.sidebar.subheader("小松菜の色の判定調整")
st.sidebar.caption("ほかの植物が混ざる場合は設定を調整してください。")

with st.sidebar.expander("詳細な色の設定 (HSV)", expanded=True):
    h_min = st.slider("色相(H)の下限", 0, 180, 30) # 黄緑〜
    h_max = st.slider("色相(H)の上限", 0, 180, 85) # 〜深緑
    s_min = st.slider("飽和度(S)の下限", 0, 255, 30) # くすんだ緑も含む
    v_min = st.slider("明度(V)の下限", 0, 255, 40) # 影になった葉を含む 👈 ここ大事
    
    # 閾値を辞書にまとめる
    hsv_thresholds = {
        'h_min': h_min, 'h_max': h_max,
        's_min': s_min, 's_max': 255, # 上限はMAXで固定
        'v_min': v_min, 'v_max': 255  # 上限はMAXで固定
    }
    
# 入力ソースの決定
input_file = None
if mode == "アルバムから選ぶ":
    input_file = st.file_uploader("判別したい画像を選んでください...", type=['jpg', 'jpeg', 'png'])
else:
    input_file = st.camera_input("小松菜を撮影してください")

# --- 3. メイン処理 ---
if input_file is not None:
    image = Image.open(input_file)
    
    # 分離したdetectorを使って判定
    # 🌟 引数に hsv_thresholds を追加して呼び出す
    res_img, count, df_data = st.session_state.detector.process_frame(
        image, conf_threshold, hsv_thresholds
    )

    # レイアウト表示
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📸 元画像")
        st.image(image, use_container_width=True)
    with col2:
        st.subheader("🔍 AI判定結果")
        # res_img はOpenCV形式(numpy)なので、st.imageでそのまま表示可能
        st.image(res_img, caption=f"検知数: {count} 株（領域表示）", use_container_width=True, channels="RGB")

    # 診断レポート
    st.divider()
    st.subheader(f"📊 診断レポート: 合計 {count} 株")
    if count > 0:
        st.table(df_data)
    else:
        st.warning("小松菜が見つかりませんでした。")

    # ダウンロード機能
    res_pil = Image.fromarray(res_img)
    buf = io.BytesIO()
    res_pil.save(buf, format="PNG")
    st.download_button("📥 判定結果をダウンロード", buf.getvalue(), "result.png", "image/png")