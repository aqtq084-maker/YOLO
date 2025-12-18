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