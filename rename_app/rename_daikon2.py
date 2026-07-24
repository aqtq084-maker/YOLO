import os

BASE = r"E:\program\AI figure learn\yolo\dataset_daikon2"
VEG_NAME = "daikon"
MAP_FILE = os.path.join(BASE, "rename_map.txt")

plan = []  # (img_dir, lbl_dir, old_img, old_lbl, new_stem, ext, split)
for split in ("train", "val"):
    img_dir = os.path.join(BASE, split, "images")
    lbl_dir = os.path.join(BASE, split, "labels")
    imgs = sorted(os.listdir(img_dir))
    lbls = set(os.listdir(lbl_dir))

    seen_stems = set()
    used_lbls = set()
    for i, fname in enumerate(imgs, start=1):
        stem, ext = os.path.splitext(fname)
        if stem in seen_stems:
            raise SystemExit(f"ABORT: duplicate stem '{stem}' in {split}/images")
        seen_stems.add(stem)
        lbl = stem + ".txt"
        if lbl not in lbls:
            raise SystemExit(f"ABORT: label missing for {split}/images/{fname}")
        used_lbls.add(lbl)
        new_stem = f"{VEG_NAME}_{split}_{i:03d}"
        plan.append((img_dir, lbl_dir, fname, lbl, new_stem, ext, split))

    extra = sorted(lbls - used_lbls)
    if extra:
        raise SystemExit(f"ABORT: labels without matching image in {split}: {extra}")

# phase 1: move everything to temporary names so final names can never
# collide with a not-yet-renamed file
for k, (img_dir, lbl_dir, img, lbl, new_stem, ext, split) in enumerate(plan):
    os.rename(os.path.join(img_dir, img), os.path.join(img_dir, f"__tmp_{k:04d}{ext}"))
    os.rename(os.path.join(lbl_dir, lbl), os.path.join(lbl_dir, f"__tmp_{k:04d}.txt"))

# phase 2: temporary names -> final names
lines = []
for k, (img_dir, lbl_dir, img, lbl, new_stem, ext, split) in enumerate(plan):
    os.rename(os.path.join(img_dir, f"__tmp_{k:04d}{ext}"), os.path.join(img_dir, new_stem + ext))
    os.rename(os.path.join(lbl_dir, f"__tmp_{k:04d}.txt"), os.path.join(lbl_dir, new_stem + ".txt"))
    lines.append(f"{split}: {img} -> {new_stem}{ext}")

with open(MAP_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"renamed {len(plan)} image/label pairs")
print(f"mapping saved to {MAP_FILE}")
