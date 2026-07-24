# rename_app 設計書 (v2)

日付: 2026-07-17
ステータス: v2 承認待ち(v1 は承認済み・Task 1 実装済み。ユーザーのフォルダ構成イメージ審査と
「パターン2の直接投入」決定を受けて改訂)

## 目的

野菜データセットへのデータ追加に使うリネーム関連機能を `rename_app/` に集約する。
将来は Streamlit の Web UI としてアプリ化する予定のため、ロジック(core.py)を UI から分離する。
v2 で複数野菜対応(`datasets/<野菜名>/`)とパターン2の dataset 直接投入を加えた。

## 決定事項(ユーザー回答)

| 論点 | 決定 |
|---|---|
| 最終的なアプリの形 | Streamlit の Web UI(今回は作らない。将来 app.py を足すだけの構成に) |
| フォルダ名 | `rename_app`(英数字のみ) |
| 既存スクリプト・staging の扱い | ルートから `rename_app/` へ移動(コピーではない) |
| コード構成 | コア分離: ロジックを `core.py` に、対話式 CLI は薄い皮に |
| **(v2)** データセットの置き場所 | **リポジトリルートの `datasets/<野菜名>/`**(rename_app の中には置かない) |
| **(v2)** パターン2(アノテ済みペア) | **リネームと同時に dataset へ直接投入**(staging を経由しない) |
| **(v2)** パターン1(アノテ前画像) | 従来どおり staging 経由(ラベルなし画像の混入防止のため直接投入しない) |
| **(v2)** staging の名前 | `daikon2_staging` → **`data_staging`**(野菜に依存しない名前に) |

## フォルダ構成

```
yolo/                              (リポジトリルート)
├─ datasets/                       ← 野菜ごとの統一構造(新設)
│  └─ daikon/                      ← 旧 dataset_daikon2 を移動したもの
│     ├─ train/images/  train/labels/
│     ├─ val/images/    val/labels/
│     └─ rename_map.txt            (移行時にそのまま同伴)
├─ data_daikon2.yaml               ← path を datasets/daikon に更新
└─ rename_app/
   ├─ core.py                      # ロジック本体(input/print なし)
   ├─ rename_new_images.py         # 対話式CLI: パターン1=staging行き / パターン2=dataset直接投入
   ├─ merge_to_dataset.py          # 対話式CLI: パターン1の取り込み(アノテ完了後)
   ├─ rename_daikon2.py            # 役目を終えた移行スクリプト。無変更で保管
   ├─ README.md                    # 使い方
   ├─ image.png                    # ユーザーの構成メモ(触らない)
   └─ data_staging/
      ├─ 1_new/                    # パターン1: 自分で集めた画像を入れる
      ├─ received/images/  received/labels/   # パターン2: 届いたペアを入れる
      ├─ 2_renamed/                # パターン1のリネーム済み画像(アノテ待ち)
      └─ 3_labels/                 # パターン1のアノテーション txt 置き場
```

## データフロー

```
パターン1(自分で収集): 1_new → [リネーム] → 2_renamed で待機
                        → アノテーションして 3_labels に保存
                        → [merge: 全件検証] → datasets/<野菜>/
パターン2(届いたペア): received → [リネーム+全件検証+直接投入] → datasets/<野菜>/
```

パターン1を staging 経由のまま残す理由: ラベルのない画像を dataset に入れると
YOLO が「背景画像」として学習してしまい、アノテ忘れが精度低下として静かに混入するため。

## core.py の設計

「検証・計画立案 → プレビュー → 実行」の分離。**build 系はファイルシステムに書き込まない。**

- 定数: `STAGING_DIR`(= rename_app/data_staging)、`NEW_DIR`、`RECEIVED_IMAGES_DIR`、
  `RECEIVED_LABELS_DIR`、`RENAMED_DIR`、`LABELS_DIR`、`DATASETS_ROOT`(= ルート/datasets)、
  `DEFAULT_VEG_NAME`、`TRAIN_RATIO`、`IMAGE_EXTS`、`PROCESSED_DIR_NAME`、`LOG_FILE`
- `default_dataset_dir(veg_name)` → `datasets/<野菜名>` を導出(CLI はこれを既定値として提示、上書き可)
- パターン1: `build_rename_plan(...)` / `execute_rename_plan(...)`(v1 のまま)
- パターン1取り込み: `build_merge_plan(...)` / `execute_merge_plan(...)`(v1 のまま)
- **(v2 新設)** パターン2直接投入: `build_import_plan(images_dir, labels_dir, dataset_dir, veg_name, ...)` /
  `execute_import_plan(plan, images_dir, labels_dir, dataset_dir, ...)`
  - 検証: ペア完全性・続き番号(dataset と staging の両方を走査)・dataset 内衝突・空 txt 警告
  - 実行: 新名で dataset へコピー → 元ファイルは received 内の processed/ へ退避 → ログ追記(tag=import)
- 番号体系は全パターン共通: `<野菜名>_<train|val>_<連番3桁>`、train/val ランダム 8:2、番号は名前順

## 移行(実データの移動 — 実行前に件数を検証すること)

1. `datasets/` を作成し、`dataset_daikon2/` をフォルダごと `datasets/daikon/` へ移動
   (中身: train 150ペア + val 37ペア + rename_map.txt = 375ファイル。移動前後で件数一致を確認)
2. `data_daikon2.yaml` の `path:` を `E:\program\AI figure learn\yolo\datasets\daikon` に更新
   (train/val/nc/names は変更なし)
3. 旧 `daikon2_staging/`(空)を削除し、`rename_app/data_staging/` 構造を新設
4. `rename_daikon2.py` を rename_app へ移動、root の旧2スクリプトを削除

フォルダ名を `datasets`(複数形)にする理由: git にトラッキングが残る旧 `dataset/` との混同を避けるため。

## 変えないこと

- 対話プロンプト方式(デフォルト値 Enter)、プレビュー、`y/N` 確認、ログ追記形式
- 「1件でも問題があれば何も変更せず中断」の全件検証方針
- `rename_daikon2.py` の中身(無変更で移動のみ)
- 本物のデータセットの中身(移動はするが、ファイルの追加・削除・改名はしない)

## 検証方法

ダミーデータ(リポジトリ内 `.superpowers/sdd/work/`)で以下を通しで実行して確認する:
パターン1フロー(リネーム→アノテ→merge)、パターン2直接投入(番号の続き・空txt警告含む)、
エラー系(ペア欠け・名前形式違い・衝突)。本物の datasets/ には触らない。
