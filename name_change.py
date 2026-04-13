import os

# ==========================================
# 1. ここを変更してください
# ==========================================
# 画像が入っているフォルダのパス
folder_path = r"E:\program\AI figure learn\yolo\dataset_komatsuna\小松菜_写真とtxtデータ\小松菜アノテーション51-95"

# つけたい名前（接頭辞）
prefix = "komatsuna_train"

# ★何番からスタートするかを指定します
start_num = 51

# ==========================================
# 2. 実行処理
# ==========================================
# フォルダ内の全ファイルを取得（名前順に並び替え）
files = sorted(os.listdir(folder_path))

count = start_num
for file_name in files:
    # ★すでに「daikon_」から始まるファイルはスキップ（無視）する
    #if file_name.startswith(f"{prefix}_"):
        #continue
        
    #old_file_path = os.path.join(folder_path, file_name)
    name, ext = os.path.splitext(file_name)
    
    # 画像ファイル以外はスキップ
    if ext.lower() not in ['.jpg', '.jpeg', '.png','.webp']:
        continue
        
    # 新しいファイル名を作成（例：daikon_021.jpg）
    new_name = f"{prefix}_{count:03d}{ext}"
    new_file_path = os.path.join(folder_path, new_name)
    
    # 名前を変更
    os.rename(old_file_path, new_file_path)
    print(f"変更: {file_name} -> {new_name}")
    
    count += 1

print(f"\n{start_num}番からの名前変更が完了しました！")