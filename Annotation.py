import os
from ultralytics import YOLO
from PIL import Image

# 1. 自動ラベリングに使うモデル (下書き用のAI)
model = YOLO('yolov8n.pt')

# 2. 自動ラベリングしたい画像が入ったフォルダ
input_dir = r"E:\program\AI figure learn\yolo\clover_images"

# 3. .txt ラベルの保存先フォルダ
output_dir = r"E:\program\AI figure learn\yolo\clover_labels"

# 4. ★★★ここに物体があればラベリングしたい座標（ROI）を複数指定★★★
# 形式: [x1, y1, x2, y2] (左上のX座標, 左上のY座標, 右下のX座標, 右下のY座標)
# 画像のピクセル座標で指定します。
# 例えば (100, 150) から (500, 400) までの領域と、
# (600, 200) から (800, 300) までの領域を指定する場合：
rois = [
    [100, 150, 500, 400],  # ROI 1
    [600, 200, 800, 300]   # ROI 2
    # ここに必要なだけROI（矩形）を追加できます
]

# フォルダがなければ作成
os.makedirs(output_dir, exist_ok=True)

# 5. フォルダ内の全画像に対して処理
for filename in os.listdir(input_dir):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        image_path = os.path.join(input_dir, filename)
        # 推論を実行 (confは低めに設定し、検出漏れを減らす)
        results = model.predict(image_path, conf=0.2)

        # .txtファイルへのパスを準備
        label_filename = os.path.splitext(filename)[0] + ".txt"
        label_path = os.path.join(output_dir, label_filename)

        # 6. 結果をYOLO形式で.txtファイルに書き込む
        with open(label_path, 'w') as f:
            # 検出された全てのボックスでループ
            for box in results[0].boxes:
                # 検出した物体の座標 [x1, y1, x2, y2] を取得
                xyxy = box.xyxy[0].cpu().numpy()
                # 物体の中心座標を計算
                obj_center_x = (xyxy[0] + xyxy[2]) / 2
                obj_center_y = (xyxy[1] + xyxy[3]) / 2

                # 7. ★★★中心点がROI内にあるかチェック★★★
                is_in_any_roi = False
                for roi in rois:
                    rx1, ry1, rx2, ry2 = roi
                    # 中心点が、定義したROI矩形の内部にあるか判定
                    if (rx1 < obj_center_x < rx2) and (ry1 < obj_center_y < ry2):
                        is_in_any_roi = True
                        break # 1つでもROIに入っていればOK

                # 8. もしROI内に入っていたら、その物体だけをファイルに書き込む
                if is_in_any_roi:
                    xywhn = box.xywhn[0]
                    class_id = int(box.cls[0])

                    # <class_id> <center_x> <center_y> <width> <height>
                    f.write(f"{class_id} {xywhn[0]} {xywhn[1]} {xywhn[2]} {xywhn[3]}\n")

        print(f"処理完了: {filename} -> {label_filename} (ROIフィルター適用済み)")
print("すべての画像の自動ラベリングが完了しました。")