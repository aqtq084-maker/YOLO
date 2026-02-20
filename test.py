<<<<<<< HEAD
import cv2
import os

# ==========================================
# 設定（あなたの環境に合わせてパスを修正してください）
# ==========================================
# 画像が入っているフォルダ
input_dir = r"E:\program\AI figure learn\yolo\clover_images"

# ROIの設定（あなたのコードと同じもの）
rois = [
    [100, 150, 500, 400],  # ROI 1
    [600, 200, 800, 300]   # ROI 2
]

# 確認用画像を保存するフォルダ（自動作成します）
output_viz_dir = r"E:\program\AI figure learn\yolo\roi_check_output"
# ==========================================

os.makedirs(output_viz_dir, exist_ok=True)

# フォルダ内の最初の画像ファイルを探す
image_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
if not image_files:
    print("エラー: 指定されたフォルダに画像が見つかりませんでした。")
    exit()

# 最初の1枚だけを使って確認する
target_filename = image_files[0]
image_path = os.path.join(input_dir, target_filename)
print(f"確認に使用する画像: {image_path}")

# 画像を読み込む (OpenCVを使用)
img = cv2.imread(image_path)
if img is None:
    print("エラー: 画像の読み込みに失敗しました。")
    exit()

# 画像の高さ(h)と幅(w)を取得
h, w, _ = img.shape

# --- 座標系の説明を描画（赤色） ---
# 左上 (0,0) に赤い点を描画
cv2.circle(img, (0, 0), 15, (0, 0, 255), -1)
cv2.putText(img, "(0,0) Origin", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

# 右下 (最大座標) に赤い点を描画
cv2.circle(img, (w-1, h-1), 15, (0, 0, 255), -1)
text_max = f"Max X:{w}, Y:{h}"
# テキストが画面外に出ないように位置を調整
text_size = cv2.getTextSize(text_max, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
cv2.putText(img, text_max, (w - text_size[0] - 20, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

# --- 設定したROIを描画（緑色） ---
for i, roi in enumerate(rois):
    x1, y1, x2, y2 = roi
    # 長方形を描画 (画像, 左上座標, 右下座標, 色(B,G,R), 線の太さ)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
    # ROIの番号と座標を描画
    label = f"ROI {i+1}: [{x1},{y1}] to [{x2},{y2}]"
    cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

# 結果の画像を保存
output_path = os.path.join(output_viz_dir, "visualized_" + target_filename)
cv2.imwrite(output_path, img)

print("-" * 30)
print("確認用画像の作成が完了しました！")
print(f"以下のファイルを開いて、ROIの位置と座標系を確認してください:\n{output_path}")
print("-" * 30)
=======
import os
from ultralytics import YOLO

# ==========================================
# 1. 賢くなった最新モデル（v3）を指定
# ==========================================
# ★ここが重要！ v2 ではなく v3 の best.pt を使います
model_path = r'E:\program\AI figure learn\runs\detect\clover_retry_v22\weights\best.pt'

model = YOLO(model_path)

# ==========================================
# 2. 設定（読み込む場所と保存する場所）
# ==========================================
# 自動ラベリングしたい新しい画像が入っているフォルダ
input_dir = r"E:\program\AI figure learn\yolo\dataset\HLimages" 

# AIが作ったラベル(.txt)を保存するフォルダ
output_dir = r"E:\program\AI figure learn\yolo\dataset\HLlabels"


# ==========================================
# 3. 自動ラベリング実行
# ==========================================
print(f"モデル {model_path} を読み込みました。")
print("自動ラベリングを開始します...")

files = os.listdir(input_dir)
count = 0
hit_count = 0

for filename in files:
    # 画像ファイルだけ処理
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        image_path = os.path.join(input_dir, filename)
        
        # 推論を実行（conf=0.25：確信度25%以上なら枠を作る）
        results = model.predict(image_path, conf=0.25, verbose=False)

        # ラベルファイルのパスを作成
        label_filename = os.path.splitext(filename)[0] + ".txt"
        label_path = os.path.join(output_dir, label_filename)

        # 検出された枠があれば書き込む
        if len(results[0].boxes) > 0:
            hit_count += 1
            with open(label_path, 'w') as f:
                for box in results[0].boxes:
                    # YOLO形式の座標を取得 (0~1正規化)
                    xywhn = box.xywhn[0].cpu().numpy()
                    
                    # クラスID 0 (clover) で書き込み
                    # 形式: class_id x_center y_center width height
                    f.write(f"0 {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f}\n")
        
        count += 1
        if count % 10 == 0:
            print(f"{count}枚 処理完了...")

print(f"完了！ 合計 {count} 枚中、{hit_count} 枚からクローバーが見つかりました。")
print(f"作成されたラベルは {output_dir} に保存されました。")
>>>>>>> origin/main
