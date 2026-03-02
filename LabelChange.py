import os
import glob

# ==========================================
# 1. ここを変更してください
# ==========================================
# ★書き換えたい野菜の「labels」フォルダのパス
<<<<<<< HEAD
label_dir = r"/home/momoshita/協生農法/YOLO/dataset_radish/labels/val"
=======
label_dir = r"E:\program\AI figure learn\yolo\dataset_radish\labels\train"
>>>>>>> 74475ef8d991ae563fc8f41f2a53e852be7cc6d9

# ★変更後のクラスID（小松菜なら '1'、3つ目の野菜なら '2'）
new_class_id = '2'

# ==========================================
# 2. 実行処理（ここは書き換え不要）
# ==========================================
files = glob.glob(os.path.join(label_dir, "*.txt"))

# classes.txt がある場合は誤作動を防ぐため除外
files = [f for f in files if not f.endswith("classes.txt")]

count = 0
for file_path in files:
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) > 0:
            # 先頭のクラスID（今まで0だったもの）を新しいIDに強制書き換え
            parts[0] = new_class_id
            new_lines.append(" ".join(parts) + "\n")
            
    # 上書き保存
    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    count += 1

print(f"{count}個のテキストファイルのIDを「{new_class_id}」に書き換えました！")