from ultralytics import YOLO

# 1. まっさらな標準モデル（Mediumサイズ）をベースにする
# 3種類をしっかり覚えるため、少し脳の容量が大きい「m」を使います。
model = YOLO('yolov8m.pt')

# 2. 合体させたデータで学習スタート
model.train(
    # ★さきほど合体させて作った新しい data.yaml のパスを指定してください
    data=r'E:\program\AI figure learn\yolo\dataset_veggies_3classes\data.yaml',
    
    epochs=100,      # 学習する回数（100回反復練習します）
    
    # 画像サイズ（PCのスペックに合わせて調整してください）
    # ※もしCPUで重すぎる場合は 640 のままでOKです。余裕があれば 800 などに上げると賢くなります。
    imgsz=640,       
    
    device='cpu',    # CPUを使って学習する設定
    
    # 水増し設定（AIに色々な角度や組み合わせの問題を解かせる）
    degrees=20.0, 
    flipud=0.5, 
    fliplr=0.5, 
    mosaic=1.0, 
    
    # ★超重要：野菜の「色」を変えない設定
    # これを入れないと、AIが大根を緑色に塗ったりして混乱してしまいます。
    hsv_h=0.0,
    
    # 完了後に保存されるフォルダの名前
    name='veggies_3classes_v1'
)