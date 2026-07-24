import os
import random
import shutil

SRC = r"E:\program\AI figure learn\yolo\dataset_daikon"
DST = r"E:\program\AI figure learn\yolo\dataset_daikon2"
SPLIT_RATIO = 0.8  # train ratio
SEED = 42

pairs = []
for split in ("train", "val"):
    img_dir = os.path.join(SRC, "images", split)
    lbl_dir = os.path.join(SRC, "labels", split)
    for fname in os.listdir(img_dir):
        stem, ext = os.path.splitext(fname)
        lbl_path = os.path.join(lbl_dir, stem + ".txt")
        if not os.path.isfile(lbl_path):
            print(f"WARNING: no label for {split}/{fname}, skipping")
            continue
        pairs.append((os.path.join(img_dir, fname), lbl_path))

print(f"total matched pairs: {len(pairs)}")

random.Random(SEED).shuffle(pairs)

n_train = round(len(pairs) * SPLIT_RATIO)
train_pairs = pairs[:n_train]
val_pairs = pairs[n_train:]
print(f"train: {len(train_pairs)}, val: {len(val_pairs)}")

for split_name, split_pairs in (("train", train_pairs), ("val", val_pairs)):
    img_out = os.path.join(DST, split_name, "images")
    lbl_out = os.path.join(DST, split_name, "labels")
    os.makedirs(img_out, exist_ok=True)
    os.makedirs(lbl_out, exist_ok=True)
    for img_path, lbl_path in split_pairs:
        shutil.copy2(img_path, os.path.join(img_out, os.path.basename(img_path)))
        shutil.copy2(lbl_path, os.path.join(lbl_out, os.path.basename(lbl_path)))

print("done")
