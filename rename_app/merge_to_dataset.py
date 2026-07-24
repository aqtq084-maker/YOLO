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
