import cv2
import numpy as np
from ultralytics import YOLO
from visualizer import draw_semantic_mask

# --- 設定 ---
MODEL_PATH = r'C:\YOLO_New_Project\runs\detect\komatsuna_third_train\weights\best.pt'
CONF_THRESHOLD = 0.5

# 色の設定（app.pyのスライダーで決めたいい感じの値をここに入れてください）
HSV_SETTINGS = {
    'h_min': 35, 'h_max': 85,
    's_min': 40, 's_max': 255,
    'v_min': 50, 'v_max': 255
}

def main():
    # モデル読み込み
    print("モデルを読み込んでいます...")
    model = YOLO(MODEL_PATH)
    
    # カメラ起動（0番はPC内蔵、1番はUSBカメラ）
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("カメラが見つかりませんでした。")
        return

    print("カメラを起動しました。「q」キーを押すと終了します。")

    while True:
        # 1フレーム読み込み
        ret, frame = cap.read()
        if not ret:
            break

        # OpenCVはBGR、YOLO/VisualizerはRGBを想定しているので変換
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 判定実行
        results = model.predict(source=frame_rgb, conf=CONF_THRESHOLD, verbose=False)
        boxes = results[0].boxes.xyxy.cpu().numpy()

        # 🌟 雑草フィルタ（面積が小さすぎるものは除外）
        h, w = frame.shape[:2]
        img_area = h * w
        valid_boxes = []
        for box in boxes:
            x1, y1, x2, y2 = box
            area = (x2 - x1) * (y2 - y1)
            # 画面の0.5%より大きいものだけ採用
            if (area / img_area) > 0.005:
                valid_boxes.append(box)

        # 描画（緑色の領域表示）
        # draw_semantic_mask は RGBを返すので受け取る
        result_rgb = draw_semantic_mask(
            frame_rgb, 
            np.array(valid_boxes), 
            HSV_SETTINGS, 
            color=(0, 255, 0), 
            alpha=0.5
        )

        # 表示用にBGRに戻す
        result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)

        # 文字を書く
        count = len(valid_boxes)
        cv2.putText(result_bgr, f"Komatsuna: {count}", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # 画面に表示
        cv2.imshow('Real-time Komatsuna Detector', result_bgr)

        # 'q' キーで終了
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()