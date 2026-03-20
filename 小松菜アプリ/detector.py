from ultralytics import YOLO
import numpy as np
# 新しく作る visualizer.py から描画関数を読み込む
from visualizer import draw_semantic_mask # 👈 新しく作ったファイルを読み込む

class KomatsunaDetector:
    def __init__(self, model_path):
        # モデルの読み込み
        self.model = YOLO(model_path)

    def process_frame(self, image, conf_threshold, hsv_thresholds):
        """
        min_area_ratio: 画像全体に対して、ボックスがこれより小さかったら無視する（0.01 = 1%）
        """
        # 画像をOpenCV形式(NumPy配列)に変換
        image_np = np.array(image)
        height, width = image_np.shape[:2]
        image_area = height * width

        # 判定実行
        results = self.model.predict(source=image, conf=conf_threshold)
        
        # 検出されたボックスの座標を取得 (CPU上のnumpy配列として)
        # xyxy形式: [x_min, y_min, x_max, y_max]
        boxes = results[0].boxes.xyxy.cpu().numpy()
        confs = results[0].boxes.conf.cpu().numpy()

        # 🌟 フィルタリング処理（ここが雑草対策！）
        valid_boxes = []
        valid_confs = []

        for box, conf in zip(boxes, confs):
            x1, y1, x2, y2 = box
            box_w = x2 - x1
            box_h = y2 - y1
            box_area = box_w * box_h
            
            # 1. 面積フィルタ：画像全体の 1% 未満の小さなゴミは無視
            if (box_area / image_area) < min_area_ratio:
                continue

            # 2. 形フィルタ：極端に細長いもの（誤検知）は無視
            aspect_ratio = box_w / box_h
            if aspect_ratio > 4.0 or aspect_ratio < 0.25:
                continue

            valid_boxes.append(box)
            valid_confs.append(conf)

        # リストをNumPy配列に戻す
        valid_boxes = np.array(valid_boxes)

        # 検知数
        count = len(boxes)


        # 🌟 ここを変更：YOLOのplot()ではなく、自作の凸包描画を使う
        # 色は (Blue, Green, Red) なので (0, 255, 0) は緑
        res_img = draw_semantic_mask(
            image_np, 
            boxes, 
            hsv_thresholds, # アプリから受け取った色の設定を渡す
            color=(0, 255, 0), # 緑色で塗る
            alpha=0.6 # 透明度
        )
        
        
        
        # 確信度のリスト作成
        conf_scores = results[0].boxes.conf.cpu().numpy().tolist()
        df_data = [{"個体番号": i+1, "確信度": f"{s*100:.1f}%"} for i, s in enumerate(conf_scores)]
        
        # 🌟 修正ポイント： res_plotted_rgb ではなく res_img を返す
        return res_img, count, df_data