import os
from ultralytics import YOLO

# ==========================================
# 1. あなたの学習済みモデル（best.pt）を指定
# ==========================================
# 前回の学習結果が入っているフォルダを確認して、パスを書き換えてください。
# 例: 'E:\program\AI figure learn\runs\detect\train8\weights\best.pt'
model_path = r'E:\program\AI figure learn\yolo\runs\detect\clover_retry_v32\weights\best.pt'

model = YOLO(model_path)

# ==========================================
# 2. 設定（フォルダやROI）
# ==========================================
# 自動ラベリングしたい新しい画像のフォルダ
input_dir = r"E:\program\AI figure learn\yolo\dataset\HL2images" 

# ラベル(.txt)の保存先
output_dir = r"E:\program\AI figure learn\yolo\dataset\HL2labels"

# ★★★ ROI（探索範囲）の設定 ★★★
# ここで指定した四角形の中にあるクローバーだけをラベリングします。
# もし「画像全体」から探してほしい場合は、このリストを空にするか、ロジックを外します。
rois = [
    [0, 0, 640, 640],  # 例: 画像全体を探索範囲にする場合（必要に応じて書き換えてください）
    # [50, 50, 300, 300], 
]

# フォルダ作成
os.makedirs(output_dir, exist_ok=True)

# ==========================================
# 3. 推論と保存の実行ループ
# ==========================================
print(f"モデル {model_path} を使用して自動ラベリングを開始します...")

files = os.listdir(input_dir)
count = 0

for filename in files:
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        image_path = os.path.join(input_dir, filename)
        
        # 推論を実行
        # conf=0.25: 確信度が25%以上あれば枠を作る（下書きなので甘めでOK）
        results = model.predict(image_path, conf=0.25, verbose=False)

        label_filename = os.path.splitext(filename)[0] + ".txt"
        label_path = os.path.join(output_dir, label_filename)

        with open(label_path, 'w') as f:
            for box in results[0].boxes:
                # 座標を取得
                xyxy = box.xyxy[0].cpu().numpy()
                obj_center_x = (xyxy[0] + xyxy[2]) / 2
                obj_center_y = (xyxy[1] + xyxy[3]) / 2

                # --- ROI判定ロジック ---
                is_in_roi = False
                
                # もしROIリストが空なら「制限なし（全部OK）」とする場合：
                if not rois:
                    is_in_roi = True
                else:
                    for roi in rois:
                        rx1, ry1, rx2, ry2 = roi
                        if (rx1 < obj_center_x < rx2) and (ry1 < obj_center_y < ry2):
                            is_in_roi = True
                            break 
                
                # ROI内、かつクラスIDが0（クローバー）なら書き込み
                if is_in_roi:
                    # YOLO形式の座標 (x_center, y_center, width, height) 0~1正規化
                    xywhn = box.xywhn[0].cpu().numpy()
                    
                    # クラスIDは 0 (clover) に固定
                    f.write(f"0 {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f}\n")
        
        count += 1
        if count % 10 == 0:
            print(f"{count}枚目の処理完了: {filename}")

print("すべての自動ラベリングが完了しました。")