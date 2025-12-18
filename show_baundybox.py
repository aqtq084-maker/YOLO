import cv2
import os
import numpy as np

# フォルダパス (あなたの設定に合わせて変更してください)
image_dir = r"E:\桃下村塾\.vscode\program\AI figure learn\yolo\clover_images"
label_dir = r"E:\桃下村塾\.vscode\program\AI figure learn\yolo\clover_labels"

# YOLO形式の座標をピクセル座標に変換する関数
def denormalize_box(box_norm, img_w, img_h):
    # box_norm: [center_x, center_y, width, height] (規格化された値)
     
    # 規格化された座標からピクセル座標に変換
    center_x = int(box_norm[0] * img_w)
    center_y = int(box_norm[1] * img_h)
    box_w = int(box_norm[2] * img_w)
    box_h = int(box_norm[3] * img_h)
    
    # xmin, ymin, xmax, ymax を計算
    x_min = int(center_x - box_w / 2)
    y_min = int(center_y - box_h / 2)
    x_max = int(center_x + box_w / 2)
    y_max = int(center_y + box_h / 2)
    
    return [x_min, y_min, x_max, y_max]

# 最初の10枚の画像をチェック
# 変更後のコードの一部
img = cv2.imread(image_dir)
if img is None:
    print(f"警告: 画像の読み込みに失敗しました - {image_dir}") # 追加


for i, filename in enumerate(os.listdir(image_dir)):
    if i >= 10: break # 10枚チェックしたら終了
        
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        image_path = os.path.join(image_dir, filename)
        label_filename = os.path.splitext(filename)[0] + ".txt"
        label_path = os.path.join(label_dir, label_filename)

        # 1. 画像の読み込み
        img = cv2.imread(image_path)
        if img is None: continue
            
        img_h, img_w, _ = img.shape
        
        # 2. ラベルファイルの読み込みと描画
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                for line in f.readlines():
                    parts = line.strip().split()
                    if len(parts) == 5:
                        class_id = int(parts[0])
                        box_norm = [float(p) for p in parts[1:]]
                        
                        # ピクセル座標に変換
                        x_min, y_min, x_max, y_max = denormalize_box(box_norm, img_w, img_h)
                        
                        # バウンディングボックスの描画（緑色, 太さ2）
                        cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                        
                        # クラスIDのテキスト描画
                        label_text = f'clover (ID:{class_id})' 
                        cv2.putText(img, label_text, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # 3. 画像の表示
        cv2.imshow(filename, img)
        key = cv2.waitKey(0) # 何かキーを押すまで待機
        cv2.destroyAllWindows()
        
        # ESCキー(27)が押されたらループを抜ける
        if key == 27:
            break

print("確認完了。")