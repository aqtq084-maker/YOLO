import os

# ==========================================
# 1. ここを変更してください
# ==========================================
# labels（txt）が入っているフォルダのパス
folder_path = r"E:\program\AI figure learn\yolo\dataset_daikon\labels\train"

# つけたい名前（imagesと同じ）
prefix = "daikon_tarain"

# ★images と同じ開始番号にする
start_num = 1  


# ==========================================
# 2. 実行処理
# ==========================================
# フォルダ内の全ファイルを取得（名前順）
files = sorted(os.listdir(folder_path))

count = start_num
for file_name in files:
    # すでに prefix_ から始まるものはスキップ
    if file_name.startswith(f"{prefix}_"):
        continue

    old_file_path = os.path.join(folder_path, file_name)
    name, ext = os.path.splitext(file_name)

    # txt 以外はスキップ
    if ext.lower() != ".txt":
        continue

    # 新しいファイル名（例：komatsuna_041.txt）
    new_name = f"{prefix}_{count:03d}{ext}"
    new_file_path = os.path.join(folder_path, new_name)

    # 名前を変更
    os.rename(old_file_path, new_file_path)
    print(f"変更: {file_name} -> {new_name}")

    count += 1

print(f"\n{start_num}番からの labels 名称変更が完了しました！")