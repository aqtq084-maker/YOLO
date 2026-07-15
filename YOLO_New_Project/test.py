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