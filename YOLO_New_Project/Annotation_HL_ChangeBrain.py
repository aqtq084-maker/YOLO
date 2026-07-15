from ultralytics import YOLO

# 1. まっさらな状態からスタート
# 1. ★まっさら(yolov8n.pt)ではなく、モデル1のパスを指定する！
model = YOLO(r'C:\Users\kiso1\OneDrive - 岡山大学\協生農法　技術班\YOLO\runs\detect\komatsuna_second_train\weights\best.pt')

# 2. 修正したデータでガッツリ学習
# data.yaml のパスは環境に合わせてください
model.train(
    data='data.yaml', 
    epochs=100,      # 100回学習
    imgsz=640, 
    device='cpu',
    
    # 水増し設定（30枚を数百枚分の価値にする）
    degrees=20.0,    # 回転
    flipud=0.5,      # 上下反転
    fliplr=0.5,      # 左右反転
    mosaic=1.0,      # 画像合成    
    name='komatsuna_third_train'  # ★フォルダ名を分かりやすく固定
)