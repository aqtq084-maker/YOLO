from ultralytics import YOLO

# 1. 学習完了したモデル(best.pt)を読み込む
# 先ほどの学習結果が 'train8' にあったので、その中の best.pt を指定します
# パスの前の 'r' は、Windowsのパス文字化けを防ぐためのおまじないです
model_path = r'E:\program\AI figure learn\runs\detect\clover_retry_v22\weights\best.pt'
model = YOLO(model_path)

# 2. 推論（予測）したい画像を指定する
# ここでは例として学習に使った 'clo2.png' を指定しますが、
# もしスマホなどで撮った「新しいクローバーの画像」があれば、そのパスに書き換えてください！
image_path = r'C:\Users\lenob\OneDrive\画像\スクリーンショット\スクリーンショット 2025-12-18 194115.png'

# 3. 推論を実行する
# save=True : 枠線がついた画像を保存する
# conf=0.25 : 「自信が25%以上あるもの」を表示する（見つからない場合はこの数字を下げます）
results = model.predict(source=image_path, save=True, conf=0.25)

print("--------------------------------------------------")
print("推論完了！")
print("結果は runs/detect/predict フォルダを確認してください。")
print("--------------------------------------------------")