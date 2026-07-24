## Global Constraints

- 本物のデータセット(`dataset_daikon2/`、移行後は `datasets/daikon/`)の**中身**には触らない。移動は Task 5 の手順のみで行い、移動前後で件数一致を検証する。
- `rename_daikon2.py` は**無変更**で移動のみ。
- CLI の対話フロー(プロンプト方式・プレビュー・`y/N` 確認・ログ形式)は現状の方式を維持。
- pytest は導入しない。検証は使い捨てスクリプト(`.superpowers/sdd/work/`)で行う。
- **git commit / git add は行わない**(ユーザーが自分でコミットする)。
- リポジトリ(`E:\program\AI figure learn\yolo`)の外のファイルは読み書きしない。
- Windows 環境。パス結合は `os.path.join`、書き込みは `encoding="utf-8"` 明示。
- 旧 root スクリプトの削除・staging/dataset の移動は Task 5 まで行わない(検証が通るまで元を残す)。

---
### Task 4: 通し検証(ダミーデータで一連のフローを実行)

**Files:**
- Create: `.superpowers/sdd/work/verify_rename_app.py`(使い捨て)

**Interfaces:**
- Consumes: Task 1 の core 全関数(パス引数をすべてダミーに差し替えて呼ぶ)

- [ ] **Step 1: 検証スクリプトを作成する**

```python
"""rename_app の通し検証（使い捨て）。本物の datasets/ には一切触らない。"""
import os
import shutil
import sys

sys.path.insert(0, r"E:\program\AI figure learn\yolo\rename_app")
import core

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_work")
NEW = os.path.join(BASE, "1_new")
RCV_IMG = os.path.join(BASE, "received", "images")
RCV_LBL = os.path.join(BASE, "received", "labels")
B = os.path.join(BASE, "2_renamed")
C = os.path.join(BASE, "3_labels")
DS = os.path.join(BASE, "datasets", "daikon")
LOG = os.path.join(BASE, "rename_log.txt")

checks = []

def check(name, cond):
    checks.append((name, cond))
    print(("OK  " if cond else "NG  ") + name)

def write(path, text="dummy"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

if os.path.isdir(BASE):
    shutil.rmtree(BASE)

# --- パターン1: 画像のみ 5枚をリネーム（staging 行き）---
for i in range(5):
    write(os.path.join(NEW, f"photo{i}.jpg"))
r = core.build_rename_plan("1", NEW, None, DS, "daikon",
                           out_images_dir=B, out_labels_dir=C)
check("P1: 問題なし", r["problems"] == [])
check("P1: 5件の計画", len(r["plan"]) == 5)
check("P1: train4/val1", r["n_train"] == 4 and r["n_val"] == 1)
core.execute_rename_plan(r["plan"], "1", NEW, None,
                         out_images_dir=B, out_labels_dir=C, log_file=LOG)
check("P1: B に 5枚", len(os.listdir(B)) == 5)
check("P1: 元は processed へ",
      len(os.listdir(os.path.join(NEW, "processed"))) == 5)
check("P1: 入力フォルダに画像が残っていない",
      [f for f in os.listdir(NEW) if f != "processed"] == [])

# --- アノテーション相当: B の各画像に対応する txt を C に作る（1つは空 = 背景）---
stems = [os.path.splitext(f)[0] for f in sorted(os.listdir(B))]
for i, stem in enumerate(stems):
    write(os.path.join(C, stem + ".txt"),
          "" if i == 0 else "0 0.5 0.5 0.2 0.2\n")

# --- パターン1の取り込み（merge）---
m = core.build_merge_plan(B, C, DS, "daikon")
check("M1: 問題なし", m["problems"] == [])
check("M1: 5ペア", len(m["plan"]) == 5)
check("M1: 空txtを1件検出", len(m["empty_txts"]) == 1)
core.execute_merge_plan(m["plan"], B, C, DS, log_file=LOG)
counts = core.count_dataset_images(DS)
check("M1: dataset 合計5枚", sum(counts.values()) == 5)
check("M1: B/C が空になった", os.listdir(B) == [] and os.listdir(C) == [])

# --- パターン2: 届いたペア 2組を dataset へ直接投入（続き番号になること）---
write(os.path.join(RCV_IMG, "recv_a.jpg"))
write(os.path.join(RCV_IMG, "recv_b.jpg"))
write(os.path.join(RCV_LBL, "recv_a.txt"), "0 0.5 0.5 0.1 0.1\n")
write(os.path.join(RCV_LBL, "recv_b.txt"), "")
r2 = core.build_import_plan(RCV_IMG, RCV_LBL, DS, "daikon",
                            staging_images_dir=B, staging_labels_dir=C)
check("P2: 問題なし", r2["problems"] == [])
check("P2: 2件の計画", len(r2["plan"]) == 2)
check("P2: 空txtを1件検出", r2["empty_txts"] == ["recv_b.txt"])
prev_max = r2["max_num"]
new_nums_ok = all(
    int(new_img.split("_")[-1].split(".")[0]) > prev_max[split]
    for _, _, new_img, _, split in r2["plan"])
check("P2: 番号が既存の続きから始まる", new_nums_ok)
core.execute_import_plan(r2["plan"], RCV_IMG, RCV_LBL, DS, log_file=LOG)
check("P2: dataset 合計7枚", sum(core.count_dataset_images(DS).values()) == 7)
check("P2: 元は processed へ",
      len(os.listdir(os.path.join(RCV_IMG, "processed"))) == 2
      and len(os.listdir(os.path.join(RCV_LBL, "processed"))) == 2)
lbl_files = (os.listdir(os.path.join(DS, "train", "labels"))
             + os.listdir(os.path.join(DS, "val", "labels")))
check("P2: dataset の labels も 7件", len(lbl_files) == 7)

# --- エラー系: import でペア欠け（txt なし画像）→ 全件中断 ---
write(os.path.join(RCV_IMG, "recv_c.jpg"))
r3 = core.build_import_plan(RCV_IMG, RCV_LBL, DS, "daikon",
                            staging_images_dir=B, staging_labels_dir=C)
check("E1: ペア欠けを検出して plan が空", r3["problems"] != [] and r3["plan"] == [])
os.remove(os.path.join(RCV_IMG, "recv_c.jpg"))

# --- エラー系: merge で名前形式が違う画像 ---
write(os.path.join(B, "wrongname.jpg"))
write(os.path.join(C, "wrongname.txt"), "0 0.5 0.5 0.1 0.1\n")
m4 = core.build_merge_plan(B, C, DS, "daikon")
check("E2: 名前形式の問題を検出", any("名前の形式" in p for p in m4["problems"]))
os.remove(os.path.join(B, "wrongname.jpg"))
os.remove(os.path.join(C, "wrongname.txt"))

# --- default_dataset_dir の導出 ---
check("DD: datasets/<野菜名> を返す",
      core.default_dataset_dir("komatsuna").endswith(os.path.join("datasets", "komatsuna")))

# --- ログが書かれている ---
with open(LOG, encoding="utf-8") as f:
    log_text = f.read()
check("LOG: rename/merge/import が記録されている",
      "| rename |" in log_text and "| merge |" in log_text and "| import |" in log_text)

print()
failed = [n for n, c in checks if not c]
if failed:
    print(f"FAILED: {len(failed)}/{len(checks)}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({len(checks)})")
```

- [ ] **Step 2: 実行して全チェック通過を確認する**

Run: `venv/Scripts/python.exe ".superpowers/sdd/work/verify_rename_app.py"`
Expected: 各行 `OK` で最後に `ALL CHECKS PASSED (22)`。
NG が出たら core.py / 検証スクリプトの期待値のどちらが設計とずれているかを特定して修正・再実行。

- [ ] **Step 3: ユーザーへ報告**

---

