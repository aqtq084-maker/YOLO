# rename_app — データセット追加用リネームツール

野菜データセット（`../datasets/<野菜名>/`）へ新しい画像を追加するときに使うツール一式。
将来は Streamlit アプリ化する予定（core.py を import して UI を足すだけ）。

## 構成

```
rename_app/
├─ core.py               # ロジック本体（計画立案と実行を分離。UIなし）
├─ rename_new_images.py  # ① リネーム（対話式CLI）
├─ merge_to_dataset.py   # ② パターン1の取り込み（対話式CLI）
├─ rename_daikon2.py     # 初回移行スクリプト（実行済み。記録として保管）
├─ image.png             # フォルダ構成の設計スケッチ（手描きの構想図・参考用）
└─ data_staging/         # 作業用フォルダ
   ├─ 1_new/             #   パターン1: 自分で集めた画像を入れる
   ├─ received/          #   パターン2: 届いた画像+txtを入れる（images/ と labels/）
   ├─ 2_renamed/         #   パターン1のリネーム済み画像（アノテ待ち）
   ├─ 3_labels/          #   パターン1のアノテーションtxtを置く
   └─ rename_log.txt     #   処理履歴の追記ログ（自動生成）
```

（`image.png` はこの構成を手描きでスケッチした構想図。実際のフォルダ名・挙動は本 README とコードが正）

データセット本体はリポジトリルートの `datasets/<野菜名>/train|val/images|labels` にある
（例: `datasets/daikon/`。旧 `dataset_daikon2` を移動したもの）。

## 使い方

リポジトリルートで venv を有効化してから実行する:

```
venv\Scripts\activate
python rename_app\rename_new_images.py
python rename_app\merge_to_dataset.py
```

### Streamlit アプリ（CLIと同じ操作をGUIで）

CLI と同じ3ワークフローを1画面で操作できる GUI。ロジックは同じ `core.py`。

```
venv\Scripts\activate
streamlit run rename_app\app.py
```

上部のモード選択（① リネーム / ② 取り込み / ③ 直接投入）を切り替え、各フォルダパスと
野菜名を入力して「プレビュー」→内容を確認して「実行する」。入力やモードを変更すると
プレビューは無効になる（古い内容での実行を防ぐため）。問題が1件でもあればプレビューで
中断し、ファイルには一切変更を加えない。

### パターン1: 自分で集めた画像（アノテーション前）

1. 画像を `data_staging/1_new/` に入れる
2. `rename_new_images.py` → モード `1`（続き番号で採番、train/val 8:2、`2_renamed/` で待機）
3. `2_renamed/` の画像をアノテーションし、txt を `3_labels/` に同名で保存
4. `merge_to_dataset.py` で全件検証して `datasets/<野菜名>/` へ取り込み

### パターン2: アノテーション済みデータをもらった場合

1. 画像を `received/images/`、txt を `received/labels/` に入れる
2. `rename_new_images.py` → モード `2` — リネームと同時に `datasets/<野菜名>/` へ**直接投入**

どちらも実行前にプレビューが出て、`y` を入力するまで何も変更しない。
1件でも問題（ペア欠け・名前形式違い・同名衝突）があれば何もせず中断する。
中身が空の txt は「検出対象なしの背景画像」として扱われるため、プレビューで件数を警告表示する（処理は止めない）。
処理履歴は `data_staging/rename_log.txt` に追記される。

取り込み後の学習はリポジトリルートの `data_daikon2.yaml`（`datasets/daikon` を指す）を `data=` に指定する。
