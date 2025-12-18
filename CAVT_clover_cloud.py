from ultralytics import YOLO

# 1. ベースとなるモデルをロード (元のyolov8n.ptなど)
model = YOLO('yolov8n.pt') 

# 2. CVATからエクスポートしたデータを使って学習を開始
results = model.train(
    data=r'C:\Users\lenob\.vscode\program\AI figure learn\yolo\clover1\data.yaml',  # ステップ1で解凍した .yaml ファイルのパスを指定
    epochs=50,             # 学習回数（最初は30〜50程度でOK）
    imgsz=640,             # 画像サイズ
    project='Clover_CAVT_test', # 学習結果の保存先プロジェクト名
    name='clover_v1'       # この学習の名前
)