import os
import re

# ==========================================
# 1. ここを変更してください
# ==========================================
# 画像が入っているフォルダのパス
folder_path = r"C:\Users\kiso1\OneDrive - 岡山大学\協生農法　技術班\YOLO\photo\小松菜train用10枚②"

# つけたい名前（接頭辞）
prefix = "train_komatsuna"

# ★何番からスタートするかを指定します
start_num = 31  

# 処理対象とする拡張子のリスト（これらを見つけたら処理します）
valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff']

# --- 数字を正しく扱うためのソート用関数 ---
def natural_keys(text):
    return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]

# ==========================================
# 2. 実行処理
# ==========================================
# フォルダ内の全ファイルを取得
all_files = os.listdir(folder_path)
all_files.sort(key=natural_keys) # ここがポイント！

# 処理対象の画像ファイルだけをリストアップ（すでにprefixがついているものは除外）
target_files = []
for f in all_files:
    name, ext = os.path.splitext(f)
    if ext.lower() in valid_extensions: # startswithのチェックを消すと無理やり改名！and not f.startswith(f"{prefix}_"):
        target_files.append(f)

# --- ステップA: 一時的な名前に変える（衝突回避） ---
temp_mapping = []
for i, file_name in enumerate(target_files):
    old_path = os.path.join(folder_path, file_name)
    temp_name = f"re-naming_temp_{i}.tmp" # 絶対に被らない名前
    temp_path = os.path.join(folder_path, temp_name)
    os.rename(old_path, temp_path)
    temp_mapping.append(temp_path)

# --- ステップB: 本来の名前（.jpg）にリネーム ---
count = start_num
for temp_path in temp_mapping:
    new_name = f"{prefix}_{count:03d}.jpg"
    new_path = os.path.join(folder_path, new_name)
    
    # ここでもし同名ファイルがあれば削除してからリネーム（強制上書きモード）
    if os.path.exists(new_path):
        os.remove(new_path)
        
    os.rename(temp_path, new_path)
    print(f"完了: -> {new_name}")
    count += 1

print(f"\n{start_num}番からの名前変更（完全リセット版）が完了しました！")