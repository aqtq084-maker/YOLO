from ultralytics import YOLO

# モデル読み込み
model = YOLO('yolov8n.pt')

# 学習開始
model.train(
    data='data.yaml',
    epochs=50, 
    imgsz=640, 
    device='cpu'  # NVIDIAのGPUがない場合は 'cpu' でOK
)