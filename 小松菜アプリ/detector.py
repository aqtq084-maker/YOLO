from ultralytics import YOLO
import PIL.Image

class KomatsunaDetector:
    def __init__(self, model_path):
        # モデルの読み込み
        self.model = YOLO(model_path)

    def process_frame(self, image, conf_threshold):
        """
        画像を受け取り、判定結果とプロット画像を返す
        """
        # 判定実行
        results = self.model.predict(source=image, conf=conf_threshold)
        
        # 結果の描画（BGRからRGBに変換）
        res_plotted = results[0].plot()
        res_plotted_rgb = res_plotted[:, :, ::-1]
        
        # 検知数
        count = len(results[0].boxes)
        
        # 確信度のリスト作成
        conf_scores = results[0].boxes.conf.tolist()
        df_data = [{"個体番号": i+1, "確信度": f"{s*100:.1f}%"} for i, s in enumerate(conf_scores)]
        
        return res_plotted_rgb, count, df_data