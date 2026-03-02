import os

# ==========================================
# 1. ここを変更してください
# ==========================================
# ★ラベル（.txt）が入っているフォルダのパスに変更してください
# （おそらく images が labels に変わったパスになると思います）
folder_path = r"E:\program\AI figure learn\yolo\dataset_radish\labels\train"

# つけたい名前（接頭辞） ※画像と同じにします
prefix = "radish"

# ★画像と同じスタート番号を指定します
start_num = 1  

# ==========================================
# 2. 実行処理
# ==========================================
# フォルダ内の全ファイルを取得（名前順に並び替え）
files = sorted(os.listdir(folder_path))

count = start_num
for file_name in files:
    # すでに接頭辞から始まるファイルはスキップ
    if file_name.startswith(f"{prefix}_"):
        continue
        
    old_file_path = os.path.join(folder_path, file_name)
    name, ext = os.path.splitext(file_name)
    
    # ★テキストファイル(.txt)以外はスキップ
    if ext.lower() != '.txt':
        continue
        
    # ★重要：YOLO自動生成の「classes.txt」などを巻き込まないようにする
    if file_name == "classes.txt":
        continue
        
    # 新しいファイル名を作成（例：radish_049.txt）
    new_name = f"{prefix}_{count:03d}{ext}"
    new_file_path = os.path.join(folder_path, new_name)
    
    # 名前を変更
    os.rename(old_file_path, new_file_path)
    print(f"変更: {file_name} -> {new_name}")
    
    count += 1

print(f"\n{start_num}番からのラベル名前変更が完了しました！")