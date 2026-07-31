import cv2
import os

# --- 設定 ---
# 1. 切り出したい動画のパス
video_path = r"E:\program\movie_data\daikon\M_daikon4.mp4"


# 2. 切り出した画像を保存するフォルダ（自動作成されます）
output_dir = r"E:\program\AI figure learn\yolo\movi_cut_result"

# 3. 何秒ごとに切り出すか（秒）
interval_sec = 0.5

# 4. 保存する画像のファイル名の接頭辞
prefix = "frame"
# -----------

os.makedirs(output_dir, exist_ok=True)

# 動画を開く
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print(f"動画を開けませんでした: {video_path}")
    raise SystemExit

# FPS を取得（取得できない場合は 30 と仮定）
fps = cap.get(cv2.CAP_PROP_FPS)
if fps is None or fps <= 0:
    print("FPSを取得できなかったため、30fpsと仮定します。")
    fps = 30.0

# interval_sec 秒ごとのフレーム間隔
frame_interval = max(1, int(round(fps * interval_sec)))

print(f"切り出しを開始します（{interval_sec}秒ごと / FPS={fps:.2f} / {frame_interval}フレームごと）...")

frame_index = 0   # 動画全体での通し番号
saved_count = 0   # 保存した画像の枚数

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # frame_interval フレームごとに保存
    if frame_index % frame_interval == 0:
        # タイムスタンプ（ミリ秒）をファイル名に含める
        timestamp_ms = int((frame_index / fps) * 1000)
        filename = f"{prefix}_{saved_count:04d}_{timestamp_ms:07d}ms.jpg"
        save_path = os.path.join(output_dir, filename)
        cv2.imwrite(save_path, frame)
        saved_count += 1

    frame_index += 1

cap.release()

print(f"完了しました。{saved_count}枚の画像を保存しました。\n保存先: {output_dir}")
