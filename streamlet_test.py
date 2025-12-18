import streamlit as st
import cv2 #BGR↔RGB 色の反転を防ぐ
from ultralytics import YOLO
from PIL import Image
import numpy as np
import socket
# モデルをロード
model = YOLO(r"C:\Users\lenob\.vscode\program\AI figure learn\yolov8n.pt")
#タイトル設定
st.title("クローバー判定アプリ 🍀")

# カメラまたはファイルから入力
img_file = st.camera_input("カメラで撮影して推論") or st.file_uploader(
    "画像をアップロード", type=["jpg", "png"]
)
#撮った画像を変換
if img_file:
    img = Image.open(img_file) #img_fileを開く
    results = model.predict(img) #モデルに対して推論を行う

    # 結果を画像として描画
    res_plotted = results[0].plot()

    # OpenCV → RGB変換
    res_plotted = cv2.cvtColor(res_plotted, cv2.COLOR_BGR2RGB)

    st.image(res_plotted, caption="推論結果", channels="RGB")

#限られたwifi環境のみ入れるように整備    
def get_client_ip(): #アクセスしてきた人）のIPを取得しようとする関数
    # WebSocket経由の接続情報を取得（簡易）
    try:
        return st.session_state.request.remote_ip
    except:
        return None

def is_allowed_ip(ip):#IPが特定のWi-Fiネットワークに属しているかチェック
    # wifiのIPを入力
    return ip.startswith("10.23.205.")

ip = get_client_ip()
if ip and not is_allowed_ip(ip):#許可されていなければエラーメッセージを出して処理を止める
    st.error("このWi-Fiネットワーク以外からのアクセスは許可されていません。")
    st.stop()

st.title("認証されたネットワークからのアクセスです ✅")