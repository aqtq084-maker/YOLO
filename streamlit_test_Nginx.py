import streamlit as st
import cv2 #BGR↔RGB 色の反転を防ぐ
from ultralytics import YOLO
from PIL import Image
import numpy as np
# import socket  <-- 不要になります

# モデルをロード
model = YOLO(r"E:\program\AI figure learn\yolo\Clover_CAVT_test\clover_v12\weights\last.pt")
#タイトル設定
st.title("クローバー判定アプリ 🍀")

# カメラまたはファイルから入力
img_file = st.camera_input("カメラで撮影して推論") or st.file_uploader(
    "画像をアップロード", type=["jpg", "png"]
)
#撮った画像を変換
if img_file:
    img = Image.open(img_file) #img_fileを開く
    
    # 1. 信頼度の閾値を設定 (例: 0.4 = 40%)
    results = model.predict(img, conf=0.4) 

    # --- ↓↓↓ ここから修正 ↓↓↓ ---
    
    # 2. 検出された物体の数をチェック
    if len(results[0]) == 0:
        # 検出数が0の場合（何も検出されなかった場合）
        
        # 検出不可のメッセージを出力
        st.warning("何も検出できませんでした。")
        
        # 元の画像（推論前）を表示
        st.image(img, caption="元の画像")

    else:
        # 検出数が1以上の場合（元の処理）
        
        # 3. 結果を画像として描画
        res_plotted = results[0].plot(
            labels=True,  # "clover" のようなラベル名を表示
            conf=True     # "0.95" のような信頼度スコアを表示
        )

        # 4. OpenCV → RGB変換
        res_plotted = cv2.cvtColor(res_plotted, cv2.COLOR_BGR2RGB)
        
        # 5. 結果画像を表示
        st.image(res_plotted, caption="推論結果", channels="RGB")