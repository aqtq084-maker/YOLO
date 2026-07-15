from ultralytics import YOLO

# 1. ゼロからではなく、前回の「賢いモデル(v3)」をベースにさらに鍛える
model = YOLO(r'E:\program\AI figure learn\runs\detect\clover_retry_v22\weights\best.pt')

# 2. 追加データを含めて再学習
model.train(
    data='E:/program/AI figure learn/yolo/data.yaml', 
    epochs=100, 
    imgsz=640, 
    device='cpu',
    
    # 水増し設定（さらに粘り強く学習させる）
    degrees=20.0, 
    flipud=0.5, 
    fliplr=0.5, 
    mosaic=1.0, 
    
    name='clover_retry_v3'  # ★今回は「v4」として保存
)