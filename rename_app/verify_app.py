"""app.py の通し検証（AppTest・使い捨て）。実データ・実 staging には触らない。"""
import os
import shutil
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
import core
from streamlit.testing.v1 import AppTest

BASE = os.path.join(APP_DIR, "app_verify_work")
if os.path.isdir(BASE):
    shutil.rmtree(BASE)

NEW = os.path.join(BASE, "1_new")
RENAMED = os.path.join(BASE, "2_renamed")
LABELS = os.path.join(BASE, "3_labels")
RCV_IMG = os.path.join(BASE, "received", "images")
RCV_LBL = os.path.join(BASE, "received", "labels")
DS = os.path.join(BASE, "datasets", "daikon")
LOG = os.path.join(BASE, "rename_log.txt")

# core の staging 系定数をテスト用に差し替え（実 staging / 実ログを汚さない）
core.RENAMED_DIR = RENAMED
core.LABELS_DIR = LABELS
core.LOG_FILE = LOG

APP = os.path.join(APP_DIR, "app.py")

checks = []


def check(name, cond):
    checks.append((name, cond))
    print(("OK  " if cond else "NG  ") + name)


def write(path, text="dummy"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def has_button(at, key):
    return any(b.key == key for b in at.button)


def fresh():
    return AppTest.from_file(APP, default_timeout=60)


# ---- ① rename: preview → execute ----
for i in range(5):
    write(os.path.join(NEW, f"photo{i}.jpg"))
at = fresh()
at.run()
at.radio(key="mode").set_value("rename")
at.text_input(key="veg").set_value("daikon")
at.text_input(key="dataset_dir").set_value(DS)
at.text_input(key="rename_img").set_value(NEW)
at.run()
at.button(key="preview_btn").click().run()
check("① preview: 例外なし", len(at.exception) == 0)
check("① preview: エラー表示なし", len(at.error) == 0)
check("① preview: 実行ボタンが出る", has_button(at, "execute_btn"))
at.button(key="execute_btn").click().run()
check("① execute: 例外なし", len(at.exception) == 0)
check("① execute: 成功メッセージ", len(at.success) >= 1)
check("① execute: staging に5枚コピー", len(os.listdir(RENAMED)) == 5)
check("① execute: 元は processed へ退避",
      os.path.isdir(os.path.join(NEW, "processed"))
      and len(os.listdir(os.path.join(NEW, "processed"))) == 5)

# ---- ① 入力変更でプレビュー無効化 ----
# (① execute で NEW の写真は processed へ退避済みのため、再度ダミー画像を用意する)
for i in range(5):
    write(os.path.join(NEW, f"photo2_{i}.jpg"))
at2 = fresh()
at2.run()
at2.text_input(key="dataset_dir").set_value(DS)
at2.text_input(key="rename_img").set_value(NEW)
at2.run()
at2.button(key="preview_btn").click().run()
had = has_button(at2, "execute_btn")
at2.text_input(key="rename_img").set_value(os.path.join(BASE, "changed"))
at2.run()
check("① 入力変更前は実行ボタンあり / 変更後は消える",
      had and not has_button(at2, "execute_btn"))

# ---- ② merge: staging(B/C) → dataset へ移動 ----
# ①で RENAMED(=B) に daikon_train/val_*.jpg が5枚できている。対応する txt を C に作る
stems = [os.path.splitext(f)[0] for f in sorted(os.listdir(RENAMED))]
for i, stem in enumerate(stems):
    write(os.path.join(LABELS, stem + ".txt"),
          "" if i == 0 else "0 0.5 0.5 0.2 0.2\n")
at3 = fresh()
at3.run()
at3.radio(key="mode").set_value("merge")
at3.run()
at3.text_input(key="veg").set_value("daikon")
at3.text_input(key="dataset_dir").set_value(DS)
at3.text_input(key="merge_img").set_value(RENAMED)
at3.text_input(key="merge_lbl").set_value(LABELS)
at3.run()
at3.button(key="preview_btn").click().run()
check("② preview: 例外なし", len(at3.exception) == 0)
check("② preview: エラー表示なし", len(at3.error) == 0)
check("② preview: 実行ボタンが出る", has_button(at3, "execute_btn"))
check("② preview: 空txt警告が1件", len(at3.warning) >= 1)
at3.button(key="execute_btn").click().run()
check("② execute: 成功メッセージ", len(at3.success) >= 1)
check("② execute: B/C が空になった",
      os.listdir(RENAMED) == [] and os.listdir(LABELS) == [])
check("② execute: dataset 合計5枚",
      sum(core.count_dataset_images(DS).values()) == 5)

# ---- ③ import: 届いたペアを dataset へ直接投入（②で dataset に5枚ある続き番号になる）----
write(os.path.join(RCV_IMG, "recv_a.jpg"))
write(os.path.join(RCV_IMG, "recv_b.jpg"))
write(os.path.join(RCV_LBL, "recv_a.txt"), "0 0.5 0.5 0.1 0.1\n")
write(os.path.join(RCV_LBL, "recv_b.txt"), "")
at4 = fresh()
at4.run()
at4.radio(key="mode").set_value("import")
at4.run()
at4.text_input(key="veg").set_value("daikon")
at4.text_input(key="dataset_dir").set_value(DS)
at4.text_input(key="import_img").set_value(RCV_IMG)
at4.text_input(key="import_lbl").set_value(RCV_LBL)
at4.run()
at4.button(key="preview_btn").click().run()
check("③ preview: 例外なし", len(at4.exception) == 0)
check("③ preview: 実行ボタンが出る", has_button(at4, "execute_btn"))
check("③ preview: 空txt警告あり", len(at4.warning) >= 1)
at4.button(key="execute_btn").click().run()
check("③ execute: 成功メッセージ", len(at4.success) >= 1)
check("③ execute: dataset 合計7枚",
      sum(core.count_dataset_images(DS).values()) == 7)
check("③ execute: 元は processed へ退避",
      os.path.isdir(os.path.join(RCV_IMG, "processed"))
      and os.path.isdir(os.path.join(RCV_LBL, "processed")))

# ---- 問題系: import でペア欠け（txtのない画像）→ 実行ボタンを出さない＝無変更 ----
write(os.path.join(RCV_IMG, "recv_c.jpg"))  # 対応txtなし
at5 = fresh()
at5.run()
at5.radio(key="mode").set_value("import")
at5.run()
at5.text_input(key="dataset_dir").set_value(DS)
at5.text_input(key="import_img").set_value(RCV_IMG)
at5.text_input(key="import_lbl").set_value(RCV_LBL)
at5.run()
at5.button(key="preview_btn").click().run()
check("問題系: エラー表示が出る", len(at5.error) >= 1)
check("問題系: 実行ボタンを出さない", not has_button(at5, "execute_btn"))

print()
failed = [n for n, c in checks if not c]
if failed:
    print(f"FAILED: {len(failed)}/{len(checks)}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({len(checks)})")
