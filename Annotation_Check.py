import cv2
import os

# --- 設定 ---
# 1. 画像とラベルがあるフォルダ
img_dir = r"E:\program\AI figure learn\yolo\clover_images"
lbl_dir = r"E:\program\AI figure learn\yolo\clover_labels"

# 2. 確認用画像を保存するフォルダ（自動作成されます）
output_dir = r"E:\program\AI figure learn\yolo\check_result"
os.makedirs(output_dir, exist_ok=True)
# -----------

print("確認画像の生成を開始します...")

# 画像フォルダ内のファイルをループ
for filename in os.listdir(img_dir):
    if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue

    # パスの生成
    img_path = os.path.join(img_dir, filename)
    txt_filename = os.path.splitext(filename)[0] + ".txt"
    txt_path = os.path.join(lbl_dir, txt_filename)

    # 画像読み込み
    img = cv2.imread(img_path)
    if img is None:
        continue
    h, w, _ = img.shape

    # 対応するラベルファイルがあれば読み込んで描画
    if os.path.exists(txt_path):
        with open(txt_path, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            parts = line.strip().split()
            class_id = int(parts[0])
            
            # YOLO形式 (center_x, center_y, w, h) は 0~1 の相対値
            x_center, y_center = float(parts[1]), float(parts[2])
            wd, ht = float(parts[3]), float(parts[4])

            # ピクセル座標に変換
            x1 = int((x_center - wd / 2) * w)
            y1 = int((y_center - ht / 2) * h)
            x2 = int((x_center + wd / 2) * w)
            y2 = int((y_center + ht / 2) * h)

            # 四角を描画 (緑色, 太さ2)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # クラスIDと座標を表示
            text = f"ID:{class_id}"
            cv2.putText(img, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # 画像を保存（表示はしない）
    save_path = os.path.join(output_dir, "check_" + filename)
    cv2.imwrite(save_path, img)

print(f"完了しました。以下のフォルダを確認してください:\n{output_dir}")