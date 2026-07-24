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
### Task 2: rename_app/rename_new_images.py — 対話式CLI

**Files:**
- Create: `rename_app/rename_new_images.py`

**Interfaces:**
- Consumes: Task 1 の `core.build_rename_plan`, `core.execute_rename_plan`, `core.build_import_plan`, `core.execute_import_plan`, `core.default_dataset_dir`, `core.count_dataset_images`, 定数 `NEW_DIR`, `RECEIVED_IMAGES_DIR`, `RECEIVED_LABELS_DIR`, `RENAMED_DIR`, `LABELS_DIR`, `DEFAULT_VEG_NAME`, `PROCESSED_DIR_NAME`, `LOG_FILE`
- Produces: `python rename_app/rename_new_images.py` の対話式CLI(パターン1=staging行き / パターン2=dataset直接投入)

- [ ] **Step 1: CLI を作成する**

```python
"""新規データのリネーム — 対話式CLI。

パターン1: 集めた画像をリネームして staging（2_renamed）で待機させる（アノテーション前）
パターン2: アノテーション済みペアをリネームして dataset へ直接投入する
ロジックは core.py にある。ここは質問・プレビュー表示・y/N 確認だけ。
"""
import core


def ask(prompt, default):
    ans = input(f"{prompt} [{default}]: ").strip()
    return ans if ans else default


def main():
    print("=== 新規データのリネーム（続き番号 + train/val 振り分け）===")
    print("  1: 自分で集めた画像（アノテーション前・画像のみ → staging で待機）")
    print("  2: 外部から届いたアノテーション済みデータ（画像 + txt → dataset へ直接投入）")
    mode = ask("どちらのパターンですか", "1")
    if mode not in ("1", "2"):
        print(f"エラー: 1 か 2 を入力してください（入力値: {mode}）")
        return

    if mode == "1":
        img_in_dir = ask("新しい画像のフォルダ", core.NEW_DIR)
        lbl_in_dir = None
    else:
        img_in_dir = ask("届いた画像のフォルダ", core.RECEIVED_IMAGES_DIR)
        lbl_in_dir = ask("届いた txt のフォルダ", core.RECEIVED_LABELS_DIR)
    veg_name = ask("野菜名 (prefix)", core.DEFAULT_VEG_NAME)
    dataset_dir = ask("データセットのフォルダ", core.default_dataset_dir(veg_name))

    if mode == "1":
        result = core.build_rename_plan(mode, img_in_dir, lbl_in_dir, dataset_dir, veg_name)
    else:
        result = core.build_import_plan(img_in_dir, lbl_in_dir, dataset_dir, veg_name)

    if result["ignored"]:
        print(f"※ 対象外のファイルは無視します: {', '.join(result['ignored'])}")
    if result["problems"]:
        print(f"\nエラーのため中断しました（何も変更していません）: {len(result['problems'])}件")
        for p in result["problems"]:
            print(f"  - {p}")
        return

    max_num = result["max_num"]
    print(f"\n既存の番号: train は {max_num['train']:03d} まで / val は {max_num['val']:03d} まで")

    plan = result["plan"]
    print(f"\n--- プレビュー ({len(plan)}件: train {result['n_train']} / val {result['n_val']}) ---")
    if mode == "1":
        for img, txt, new_img, new_txt in plan:
            print(f"  {img} -> {new_img}")
        print(f"\n・画像は新しい名前で {core.RENAMED_DIR} へコピーします")
        print(f"・元のファイルは各フォルダ内の {core.PROCESSED_DIR_NAME}/ へ移動します（二重リネーム防止）")
    else:
        for img, txt, new_img, new_txt, split in plan:
            print(f"  {img} + {txt} -> {split}/{new_img} + {new_txt}")
        if result["empty_txts"]:
            print(f"\n※ 中身が空の txt が {len(result['empty_txts'])}件あります（検出対象なしの背景画像として扱われます）:")
            for lbl in result["empty_txts"]:
                print(f"  - {lbl}")
        print(f"\n・{dataset_dir} へ直接投入します（画像も txt も新しい名前になります）")
        print(f"・元のファイルは各フォルダ内の {core.PROCESSED_DIR_NAME}/ へ移動します（二重取り込み防止）")

    ans = input("\n実行しますか？ [y/N]: ").strip().lower()
    if ans not in ("y", "yes"):
        print("キャンセルしました（何も変更していません）。")
        return

    if mode == "1":
        for line in core.execute_rename_plan(plan, mode, img_in_dir, lbl_in_dir):
            print(f"コピー: {line}")
        print(f"\n完了！ {len(plan)}件をリネームしました (train {result['n_train']} / val {result['n_val']})")
        print(f"記録: {core.LOG_FILE}")
        print(f"次の手順: {core.RENAMED_DIR} の画像をアノテーションして、txt を {core.LABELS_DIR} に保存してください。")
    else:
        for line in core.execute_import_plan(plan, img_in_dir, lbl_in_dir, dataset_dir):
            print(f"投入: {line}")
        print(f"\n完了！ {len(plan)}ペアを取り込みました (train {result['n_train']} / val {result['n_val']})")
        for split, total in core.count_dataset_images(dataset_dir).items():
            print(f"  {split}: 合計 {total}枚")
        print(f"記録: {core.LOG_FILE}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: N キャンセルでスモークテスト(パターン1・何も変更しないこと)**

```bash
mkdir -p ".superpowers/sdd/work/smoke/new" ".superpowers/sdd/work/smoke/dataset"
printf 'dummy' > ".superpowers/sdd/work/smoke/new/photo1.jpg"
printf '1\n.superpowers/sdd/work/smoke/new\ndaikon\n.superpowers/sdd/work/smoke/dataset\nN\n' | venv/Scripts/python.exe rename_app/rename_new_images.py
ls ".superpowers/sdd/work/smoke/new"
```
Expected:
- プレビューに `photo1.jpg -> daikon_train_001.jpg` が出る
- `キャンセルしました（何も変更していません）。`
- 最後の `ls` で `photo1.jpg` のみ(processed/ ができていない)

- [ ] **Step 3: N キャンセルでスモークテスト(パターン2)**

```bash
mkdir -p ".superpowers/sdd/work/smoke/rimg" ".superpowers/sdd/work/smoke/rlbl"
printf 'dummy' > ".superpowers/sdd/work/smoke/rimg/a.jpg"
printf '0 0.5 0.5 0.1 0.1\n' > ".superpowers/sdd/work/smoke/rlbl/a.txt"
printf '2\n.superpowers/sdd/work/smoke/rimg\n.superpowers/sdd/work/smoke/rlbl\ndaikon\n.superpowers/sdd/work/smoke/dataset\nN\n' | venv/Scripts/python.exe rename_app/rename_new_images.py
ls ".superpowers/sdd/work/smoke/dataset" 2>/dev/null; echo "exit=$?"
```
Expected:
- プレビューに `a.jpg + a.txt -> train/daikon_train_001.jpg + daikon_train_001.txt`
- `キャンセルしました（何も変更していません）。`
- dataset フォルダは空のまま

- [ ] **Step 4: ユーザーへ報告**

---

