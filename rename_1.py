import os
import re

# ==========================================
# 1. ここを変更してください
# ==========================================

# .npyファイルが入っているフォルダ
folder_path = r"/home/momoshita/協生農法/YOLO/features_photo_homu/じゃがいも"

# ★つけたい接頭辞
# 例: "train" -> train_001_satoimo_cls.npy
prefix = ""

# ★つけたい接尾辞
# 例: "satoimo" -> train_001_satoimo_cls.npy
suffix = ""

# ★何番からスタートするか
start_num = 1


# ==========================================
# 2. ファイル名の設定
# ==========================================

# 対象とする種類
# 必ずこの2種類を区別して処理します
file_types = ["cls", "patch"]


# ==========================================
# 3. 数字を自然順に並べる関数
# ==========================================

def natural_keys(text):
    return [
        int(c) if c.isdigit() else c.lower()
        for c in re.split(r'(\d+)', text)
    ]


# ==========================================
# 4. フォルダ内の.npyファイルを取得
# ==========================================

all_files = os.listdir(folder_path)

npy_files = [
    f for f in all_files
    if f.lower().endswith(".npy")
]


# ==========================================
# 5. cls / patch を判別
# ==========================================

cls_files = []
patch_files = []

for f in npy_files:

    name, ext = os.path.splitext(f)

    if name.endswith("_cls"):
        cls_files.append(f)

    elif name.endswith("_patch"):
        patch_files.append(f)


# ==========================================
# 6. 数字順にソート
# ==========================================

cls_files.sort(key=natural_keys)
patch_files.sort(key=natural_keys)


# ==========================================
# 7. 件数確認
# ==========================================

print("==========================================")
print("リネーム対象")
print("==========================================")

print(f"cls   : {len(cls_files)} ファイル")
print(f"patch : {len(patch_files)} ファイル")

print("==========================================")


if len(cls_files) != len(patch_files):
    print("警告：cls と patch のファイル数が一致していません。")
    print("処理を中止します。")
    exit()


# ==========================================
# 8. 一時ファイル名へ変更
#    → ファイル名の衝突を防ぐ
# ==========================================

temp_mapping = []

for i, file_name in enumerate(npy_files):

    old_path = os.path.join(folder_path, file_name)

    # 元の拡張子を維持
    temp_name = f"__rename_temp_{i}__.npy"
    temp_path = os.path.join(folder_path, temp_name)

    os.rename(old_path, temp_path)

    temp_mapping.append((file_name, temp_path))


# ==========================================
# 9. cls / patch の元ファイルを再取得
# ==========================================

# 一時ファイル名に変わっているため、
# 元ファイル名から種類を判定して保存

temp_cls = []
temp_patch = []

for original_name, temp_path in temp_mapping:

    if original_name.endswith("_cls.npy"):
        temp_cls.append((original_name, temp_path))

    elif original_name.endswith("_patch.npy"):
        temp_patch.append((original_name, temp_path))


# 元の順番を維持
temp_cls.sort(key=lambda x: natural_keys(x[0]))
temp_patch.sort(key=lambda x: natural_keys(x[0]))


# ==========================================
# 10. 本来の名前に変更
# ==========================================

count = start_num

for i in range(len(temp_cls)):

    # --------------------------------------
    # 新しい共通番号
    # --------------------------------------

    number = f"{count:03d}"


    # --------------------------------------
    # cls の新しい名前
    # --------------------------------------

    if prefix and suffix:
        cls_new_name = f"{prefix}_{number}_{suffix}_cls.npy"

    elif prefix:
        cls_new_name = f"{prefix}_{number}_cls.npy"

    elif suffix:
        cls_new_name = f"{number}_{suffix}_cls.npy"

    else:
        cls_new_name = f"{number}_cls.npy"


    # --------------------------------------
    # patch の新しい名前
    # --------------------------------------

    if prefix and suffix:
        patch_new_name = f"{prefix}_{number}_{suffix}_patch.npy"

    elif prefix:
        patch_new_name = f"{prefix}_{number}_patch.npy"

    elif suffix:
        patch_new_name = f"{number}_{suffix}_patch.npy"

    else:
        patch_new_name = f"{number}_patch.npy"


    # --------------------------------------
    # パス
    # --------------------------------------

    cls_temp_path = temp_cls[i][1]
    patch_temp_path = temp_patch[i][1]

    cls_new_path = os.path.join(folder_path, cls_new_name)
    patch_new_path = os.path.join(folder_path, patch_new_name)


    # --------------------------------------
    # 同名ファイルが存在する場合
    # --------------------------------------

    if os.path.exists(cls_new_path):
        os.remove(cls_new_path)

    if os.path.exists(patch_new_path):
        os.remove(patch_new_path)


    # --------------------------------------
    # リネーム
    # --------------------------------------

    os.rename(cls_temp_path, cls_new_path)
    os.rename(patch_temp_path, patch_new_path)


    print(f"完了: {cls_new_name}")
    print(f"完了: {patch_new_name}")


    count += 1


# ==========================================
# 11. 完了
# ==========================================

print()
print("==========================================")
print("リネーム完了！")
print("==========================================")
print(f"開始番号 : {start_num}")
print(f"cls      : {len(temp_cls)}")
print(f"patch    : {len(temp_patch)}")
print("==========================================")
