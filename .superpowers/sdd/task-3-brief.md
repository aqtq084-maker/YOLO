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
### Task 3: rename_app/merge_to_dataset.py — 対話式CLI(パターン1の取り込み)

**Files:**
- Create: `rename_app/merge_to_dataset.py`

**Interfaces:**
- Consumes: Task 1 の `core.build_merge_plan`, `core.execute_merge_plan`, `core.count_dataset_images`, `core.default_dataset_dir`, 定数 `RENAMED_DIR`, `LABELS_DIR`, `DEFAULT_VEG_NAME`, `LOG_FILE`
- Produces: `python rename_app/merge_to_dataset.py` の対話式CLI

- [ ] **Step 1: CLI を作成する**

```python
"""データセットへの取り込み（B + C → dataset）— パターン1専用の対話式CLI。

アノテーションが済んだ staging の画像+txt を検証して dataset へ移動する。
ロジックは core.py にある。ここは質問・プレビュー表示・y/N 確認だけ。
"""
import core


def ask(prompt, default):
    ans = input(f"{prompt} [{default}]: ").strip()
    return ans if ans else default


def main():
    print("=== データセットへの取り込み（B + C → dataset）===")
    images_dir = ask("リネーム済み画像のフォルダ (B)", core.RENAMED_DIR)
    labels_dir = ask("アノテーション txt のフォルダ (C)", core.LABELS_DIR)
    veg_name = ask("野菜名 (prefix)", core.DEFAULT_VEG_NAME)
    dataset_dir = ask("データセットのフォルダ", core.default_dataset_dir(veg_name))

    result = core.build_merge_plan(images_dir, labels_dir, dataset_dir, veg_name)

    if result["ignored"]:
        print(f"※ 対象外のファイルは無視します: {', '.join(result['ignored'])}")
    if result["problems"]:
        print(f"\nエラーのため中断しました（何も変更していません）: {len(result['problems'])}件")
        for p in result["problems"]:
            print(f"  - {p}")
        return

    plan = result["plan"]
    print(f"\n--- プレビュー ({len(plan)}ペア: train {result['n_train']} / val {result['n_val']}) ---")
    for split, img, lbl in plan:
        print(f"  {img} + {lbl} -> {split}/")
    if result["empty_txts"]:
        print(f"\n※ 中身が空の txt が {len(result['empty_txts'])}件あります（検出対象なしの背景画像として扱われます）:")
        for lbl in result["empty_txts"]:
            print(f"  - {lbl}")
    print(f"\n・{dataset_dir} へ「移動」します（B と C からは無くなります）")

    ans = input("\n実行しますか？ [y/N]: ").strip().lower()
    if ans not in ("y", "yes"):
        print("キャンセルしました（何も変更していません）。")
        return

    for line in core.execute_merge_plan(plan, images_dir, labels_dir, dataset_dir):
        print(f"移動: {line}")

    print(f"\n完了！ {len(plan)}ペアを取り込みました (train {result['n_train']} / val {result['n_val']})")
    for split, total in core.count_dataset_images(dataset_dir).items():
        print(f"  {split}: 合計 {total}枚")
    print(f"記録: {core.LOG_FILE}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 空フォルダでスモークテスト(安全に中断すること)**

```bash
mkdir -p ".superpowers/sdd/work/smoke/emptyB" ".superpowers/sdd/work/smoke/emptyC"
printf '.superpowers/sdd/work/smoke/emptyB\n.superpowers/sdd/work/smoke/emptyC\ndaikon\n.superpowers/sdd/work/smoke/dataset\n' | venv/Scripts/python.exe rename_app/merge_to_dataset.py
```
Expected: `エラーのため中断しました（何も変更していません）: 1件` と `取り込むファイルがありません。`

- [ ] **Step 3: ユーザーへ報告**

---

