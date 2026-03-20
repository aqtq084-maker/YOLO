from ultralytics import YOLO
import numpy as np
from visualizer import draw_labeled_boxes  # 👈 新しい描画関数を使います

class KomatsunaDetector:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        # モデルが知っている名前リストを取得（例: {0: 'komatsuna', 1: 'daikon'}）
        self.names = self.model.names

    def process_frame(self, image, conf_threshold):
        # 画像を強制的に RGB に変換（透明チャネル RGBA などを除去）
        image = image.convert("RGB")
        
        image_np = np.array(image)
        
        # 判定実行
        results = self.model.predict(source=image_np, conf=conf_threshold, verbose=False)
        
        # 検出結果を取り出す
        boxes = results[0].boxes.xyxy.cpu().numpy()  # 座標
        confs = results[0].boxes.conf.cpu().numpy()  # 確信度
        cls_ids = results[0].boxes.cls.cpu().numpy().astype(int) # クラスID（0, 1, 2...）

        # 検知数
        count = len(boxes)

        # 🌟 描画関数へ渡す（名前リストも一緒に渡す）
        res_img = draw_labeled_boxes(
            image_np, 
            boxes, 
            confs, 
            cls_ids, 
            self.names
        )
        
        # データ作成（表にも名前が出るようにする）
        df_data = []
        for i, (conf, cls_id) in enumerate(zip(confs, cls_ids)):
            name = self.names[cls_id] # IDから名前に変換
            df_data.append({
                "No": i+1,
                "種類": name,  # 👈 種類を追加
                "確信度": f"{conf*100:.1f}%"
            })
        
        return res_img, count, df_data