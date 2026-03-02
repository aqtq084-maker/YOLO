from ultralytics import YOLO

model = YOLO('yolov8s.pt')

model.train(
    data='/home/momoshita/協生農法/YOLO/data.yaml',
    epochs=100,
    imgsz=640,
    device='cpu',

    batch=8,          # CPU向け最適
    workers=12,       # 24コアを活かす

    degrees=15.0,
    fliplr=0.5,
    flipud=0.0,       # 畑用途なら切るのがおすすめ
    mosaic=1.0,

    hsv_h=0.0,        # ★色を守る（最重要）
    hsv_s=0.7,
    hsv_v=0.4,

    name='veggies_3classes_v1_cpu_opt'
)