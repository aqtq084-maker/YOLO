# 設計: リネームアプリの Streamlit UI 化

日付: 2026-07-24
対象: `rename_app/` の既存ロジック (`core.py`) を Streamlit UI から使えるようにする

## 背景・目的

`rename_app/` には、野菜データセット (`datasets/<野菜名>/`) へ新しい画像を追加するための
リネーム／取り込みロジックが `core.py` に実装済みで、対話式CLI2本
(`rename_new_images.py`, `merge_to_dataset.py`) から利用されている。
README に「将来 Streamlit アプリ化する予定（core.py を import して UI を足すだけ）」とある通り、
本設計はその Streamlit UI を新規に作る。

`core.py` は「計画を立てる (`build_*_plan`) / 実行する (`execute_*_plan`)」を分離しており、
build 系はファイルシステムに一切書き込まない。この分離が「プレビュー→確認→実行」UIに
そのまま対応するため、**`core.py` は一切変更しない**。

## スコープ

`core.py` の3ワークフロー全部を対象とする（1つのアプリ内でモード切替）:

1. **① リネーム**（パターン1・アノテ前）: 自分で集めた画像を続き番号でリネームし、
   train/val 8:2 に振り分けて staging (`2_renamed/`) で待機させる。
   `build_rename_plan(mode="1")` → `execute_rename_plan`
2. **② 取り込み（merge）**（パターン1の続き）: アノテ済みの staging (B=画像, C=txt) を
   検証して `datasets/<野菜名>/` へ**移動**する。
   `build_merge_plan` → `execute_merge_plan`
3. **③ 直接投入（import）**（パターン2）: 外部から届いたアノテ済みペアをリネームして
   `datasets/<野菜名>/` へ直接投入する。
   `build_import_plan` → `execute_import_plan`

### 非スコープ

- 画像のブラウザアップロード（今回は**フォルダパス指定**のみ。`core.py` がフォルダ前提のため）
- マルチページ構成（1画面+モード選択で行く）
- アノテーション機能そのもの（従来どおり外部ツールで実施）
- 認証・IP制限（既存 streamlit 推論アプリの IP ゲートとは無関係）
- `core.py` のロジック変更

## アーキテクチャ / ファイル配置

```
rename_app/
├─ core.py                （既存・無変更）ロジック本体
├─ app.py                 （新規）Streamlit UI。core を import するだけ
├─ rename_new_images.py   （既存・無変更）CLI
├─ merge_to_dataset.py    （既存・無変更）CLI
└─ ...（README 等はそのまま）
```

- 起動: リポジトリルートで venv を有効化し `streamlit run rename_app\app.py`
- `app.py` は冒頭で自身のフォルダを `sys.path` に追加してから `import core` する
  （`streamlit run` 実行時にも確実に `core` を解決させるため。既存の検証スクリプトと同じ流儀）。
- UI と CLI は同じ `core` を共有する二本立て。CLI は残す。

## UI フロー

### モード選択

画面上部の `st.radio` で ①②③ を切替。選んだモードに応じて入力欄・処理を出し分ける。

### 入力欄（`st.text_input`、デフォルトは `core` の定数）

| モード | 入力欄（デフォルト値） |
|---|---|
| ① リネーム | 新しい画像フォルダ (`core.NEW_DIR`) / 野菜名 (`core.DEFAULT_VEG_NAME`) / データセットフォルダ (`core.default_dataset_dir(野菜名)`) |
| ② 取り込み | リネーム済み画像フォルダ B (`core.RENAMED_DIR`) / txtフォルダ C (`core.LABELS_DIR`) / 野菜名 / データセットフォルダ |
| ③ 直接投入 | 届いた画像フォルダ (`core.RECEIVED_IMAGES_DIR`) / 届いたtxtフォルダ (`core.RECEIVED_LABELS_DIR`) / 野菜名 / データセットフォルダ |

「データセットフォルダ」の既定値は野菜名から `core.default_dataset_dir()` で導出する。

### 2段階の実行（CLIの「プレビュー→y/N」に対応）

**ステップ1: 「プレビュー」ボタン** → 対応する `build_*_plan` を呼び、戻り値 dict を
`st.session_state` に保存して表示する。

- `problems` が1件でもあれば **赤エラーで一覧表示し、「実行する」ボタンは出さない**
  （＝CLIの「中断」。ファイルには一切触れない）
- `ignored` があれば「無視した対象外ファイル」を info 表示
- `max_num`（既存の続き番号 train/val）と `n_train` / `n_val` を表示
- `plan` を**テーブル**で表示
  - ①: 旧名 → 新名（`plan` は `(旧画像, 旧txt, 新画像, 新txt)`）
  - ②: 画像 / txt → split（merge はリネームせず split フォルダへ**移動**。`plan` は `(split, 画像, txt)`）
  - ③: 旧名 → split / 新名（`plan` は `(旧画像, 旧txt, 新画像, 新txt, split)`）
- `empty_txts`（②③）があれば「空txt = 検出対象なしの背景画像として扱われます」を warning 表示

**ステップ2: 「実行する」ボタン**（プレビュー成功時のみ表示）→ 対応する `execute_*_plan` を呼ぶ。

- 実行結果の各行（`execute_*` の戻り値）を表示
- ①: 次手順の案内（`2_renamed/` をアノテして txt を `3_labels/` へ）
- ②③: `core.count_dataset_images()` の train/val 合計枚数を表示
- 共通: ログパス (`core.LOG_FILE`) を表示

## 状態管理・エラーハンドリング

### 状態（`st.session_state`）

- Streamlit はウィジェット操作のたびにスクリプトを再実行するため、「プレビュー」で作った
  `plan` を再実行間で保持する必要がある。`st.session_state` にプレビュー結果 dict と
  「そのプレビューを作ったときのモード・入力パス（野菜名・各フォルダ）」を一緒に保存する。
- **入力欄やモードが現在値と保存時で食い違う場合はプレビューを無効化**し、「実行する」ボタンを
  出さない（古い plan を新しい入力で実行してしまう事故を防ぐ）。
- 「実行」完了後は保存済みプレビューをクリアして完了メッセージを表示する。

### エラーハンドリング（無変更の保証を最優先）

- フォルダ不存在・ペア欠け・名前形式違い・同名衝突 → すべて `core` が `problems` に集約する。
  UIは赤表示して「実行する」ボタンを出さないだけで、ファイルには触れない。
- 実行フェーズの例外（コピー／移動の失敗など）は `try/except` で捕捉し `st.error` で表示する。
  `core` は「新名でコピー → 元をprocessed/へ移動」の順のため、途中失敗でも元画像は原則残る（既存挙動）。
- 本物の `datasets/` を壊さない: UIは入力パスをそのまま `core` に渡すだけで、削除・上書き系の
  操作を一切持たない。`core` 側も既存ファイルへの上書きは衝突チェックで拒否する。

## テスト

### ロジック（`core.py`）

既存の検証ハーネス `.superpowers/sdd/work/verify_rename_app.py`（27チェック）が全経路をカバー済み。
`core` を変更しないため、回帰確認用にそのまま維持する。

### UI（`app.py`）

`streamlit.testing.v1.AppTest` によるヘッドレス自動スモークテストを新規に追加する。
**実データ (`datasets/`) には触れず、テスト専用の一時フォルダ**を入力に使う。確認するケース:

- ① プレビュー: 画像フォルダを指定 → plan がテーブルに出る／train・val件数が出る／「実行する」ボタンが出る
- ① 実行: ボタン押下 → staging に画像がコピーされ、元が `processed/` へ退避、完了メッセージが出る
- ②③: それぞれプレビュー→実行の1往復が成功する
- エラー系: ペア欠け等で `problems` が表示され、**「実行する」ボタンが出ない**（＝無変更）
- 状態破棄: プレビュー後に入力を変えると古い「実行する」ボタンが無効化される

補足として、最後に `streamlit run` で一度起動して目視確認も行う。

## 受け入れ条件

- `streamlit run rename_app\app.py` で起動でき、①②③をモードで切替できる
- 各モードでプレビュー→実行が CLI と同じ結果になる
- 問題が1件でもあればプレビューで中断し、ファイルに一切変更が入らない
- `core.py` は無変更、既存CLIも従来どおり動く
- `AppTest` スモークテストが全て通る
- `datasets/` の実データを一切壊さない
