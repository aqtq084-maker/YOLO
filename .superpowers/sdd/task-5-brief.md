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
### Task 5: 実データの移行と後片付け(検証が通ってから行う)

**Files:**
- Move: `dataset_daikon2/` → `datasets/daikon/`(実データ。件数検証つき)
- Modify: `data_daikon2.yaml`(path を新しい場所に)
- Move: `rename_daikon2.py` → `rename_app/rename_daikon2.py`(無変更)
- Delete: root の `rename_new_images.py`, `merge_to_dataset.py`(置き換え済み)
- Delete: root の `daikon2_staging/`(空確認後)
- Create: `rename_app/data_staging/` 構造、`rename_app/README.md`

**Interfaces:**
- Consumes: Task 1〜4 完了・検証通過
- Produces: spec v2 の「フォルダ構成」と一致する最終状態

- [ ] **Step 1: 移動前の件数を記録する**

```bash
find dataset_daikon2 -type f | wc -l
find dataset_daikon2/train/images -type f | wc -l
find dataset_daikon2/val/images -type f | wc -l
```
Expected: `375` / `150` / `37`(1件でも違ったら**中断してユーザーに報告**。375 = 150+150+37+37+rename_map.txt)

- [ ] **Step 2: datasets/daikon へ移動して件数を確認する**

```bash
mkdir -p datasets
mv dataset_daikon2 datasets/daikon
find datasets/daikon -type f | wc -l
ls datasets/daikon
```
Expected: `375`、`ls` に `train val rename_map.txt`。件数が合わなければ**即ユーザーに報告**(mv はフォルダ単位なので通常欠損しない)。

- [ ] **Step 3: data_daikon2.yaml の path を更新する**

Edit で置換:

old:
```yaml
path: E:\program\AI figure learn\yolo\dataset_daikon2
```
new:
```yaml
path: E:\program\AI figure learn\yolo\datasets\daikon
```
(train/val/nc/names は変更しない)

- [ ] **Step 4: 旧 staging の空確認 → 片付け・新設**

```bash
find daikon2_staging -type f
```
Expected: 出力なし(ファイルが出たら**削除せず中断**、ユーザーに確認)

```bash
mv rename_daikon2.py rename_app/rename_daikon2.py
rm rename_new_images.py merge_to_dataset.py
rm -r daikon2_staging
mkdir -p rename_app/data_staging/1_new \
         rename_app/data_staging/received/images \
         rename_app/data_staging/received/labels \
         rename_app/data_staging/2_renamed \
         rename_app/data_staging/3_labels
```
(3スクリプトとも git 未追跡なので git 操作は不要。`git rm` は使わない)

- [ ] **Step 5: README.md を作成する**

`rename_app/README.md`:

````markdown
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
└─ data_staging/         # 作業用フォルダ
   ├─ 1_new/             #   パターン1: 自分で集めた画像を入れる
   ├─ received/          #   パターン2: 届いた画像+txtを入れる
   ├─ 2_renamed/         #   パターン1のリネーム済み画像（アノテ待ち）
   └─ 3_labels/          #   パターン1のアノテーションtxtを置く
```

データセット本体はリポジトリルートの `datasets/<野菜名>/train|val/images|labels` にある
（例: `datasets/daikon/`。旧 `dataset_daikon2` を移動したもの）。

## 使い方

リポジトリルートで venv を有効化してから実行する:

```
venv\Scripts\activate
python rename_app\rename_new_images.py
python rename_app\merge_to_dataset.py
```

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
処理履歴は `data_staging/rename_log.txt` に追記される。

取り込み後の学習はリポジトリルートの `data_daikon2.yaml`（`datasets/daikon` を指す）を `data=` に指定する。
````

- [ ] **Step 6: 最終確認**

```bash
ls rename_app rename_app/data_staging datasets/daikon
ls rename_daikon2.py rename_new_images.py merge_to_dataset.py daikon2_staging dataset_daikon2 2>&1
venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'rename_app'); import core, os; print(os.path.isdir(core.default_dataset_dir('daikon')))"
```
Expected:
- `rename_app/` に core.py, rename_new_images.py, merge_to_dataset.py, rename_daikon2.py, README.md, image.png, data_staging
- 2つ目の `ls` は 5つとも "No such file or directory"
- 3つ目は `True`(core の既定パスが移行後の実フォルダを指す)

- [ ] **Step 7: ユーザーへ報告**

移行結果(件数一致)・最終構成・「コミットはしていないこと」を報告する。

---

## Self-Review 結果

- **Spec coverage:** datasets/<野菜>構造→Task1(default_dataset_dir)+Task5(移行) / パターン2直接投入→Task1(import関数)+Task2(mode2) / パターン1 staging維持→Task2(mode1)+Task3 / staging改名→Task1+Task5 / yaml更新→Task5 Step3 / 検証→Task4。ギャップなし。
- **Placeholder scan:** TBD/TODO なし。全ステップ実コード・実コマンド・期待値あり。
- **Type consistency:** import plan のタプルは5要素(img, txt, new_img, new_txt, split)で build/execute/CLI/検証すべて一致。rename plan は4要素のまま。`default_dataset_dir` の呼び出し箇所(CLI 2本・検証)一致。
