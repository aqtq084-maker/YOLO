# SDD progress — plan: docs/superpowers/plans/2026-07-17-rename-app.md (v2)
計画はv2に改訂(2026-07-17): パターン2直接投入 + datasets/<野菜>構造 + data_staging改名
Task 1 (v1): core.py 作成済み・レビュー合格 → v2 Task 1 で改修予定(未着手)
Task 2-5 (v2): 未着手
次のアクション: ユーザーのspec v2承認後、Task 1(v2改修)から再開
Task 1 (v2): complete (core.py改修, レビュー: スペック✅/品質Approved)
  - Minor記録: build_import_planとbuild_rename_planのロジック重複(計画が逐語転写を指定)
  - Minor記録: random.shuffleシード固定なし(既存と同挙動、新規劣化ではない)
  - ⚠️解決: 既存関数無改変はTask 4の通し検証で機能的に担保
Task 2 (v2): complete (rename_new_images.py CLI, レビュー: スペック✅/品質Approved, 指摘なし)
Task 3 (v2): complete (merge_to_dataset.py CLI, レビュー: スペック✅/品質Approved, 指摘なし)
Task 4 (v2): complete (通し検証 22/22 パス、レビュアー再実行で再現確認、実データ無傷)
Task 5 (v2): complete (datasets/daikon移行 375→375一致, yaml更新, staging新設, README, レビュー: スペック✅/Approved)
全タスク完了。残: 最終ブランチレビュー
最終レビュー: マージ可(Critical/Important なし)。Minor triage: 重複=後回し可 / シード=not-a-bug / datasets/のgitignore=ユーザー判断待ち / README軽微不足=後回し可
=== 全工程完了 (2026-07-18) ===
=== フォローアップ (2026-07-24): 残Minor片付け ===
- gitignore判断: ユーザー選択「追跡を続ける(現状維持)」→ .gitignore・コードとも変更なし
- 重複解消: core.py に _pair_by_stem / _assign_split_numbers を抽出し、build_rename_plan(mode2) と build_import_plan の重複ロジックを集約(外部挙動不変)
- 検証: verify_rename_app.py に build_rename_plan mode"2" のチェックを追加(22→27件)。リファクタ前後とも ALL CHECKS PASSED (27)
- README補強: image.png(設計スケッチ) と rename_log.txt を構成に明記、空txt=背景画像扱いの注記を追加
- シード固定なし: not-a-bug のため対応せず（判断済み）
