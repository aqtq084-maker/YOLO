# 野菜判定AI 混同行列+PCA可視化 精度評価ツール

DINOv2で抽出済みの特徴量(`_cls.npy` / `_patch.npy`)をもとに、
**混同行列 (Confusion Matrix) + PCA可視化** で
「野菜の葉の写真から野菜名を当てる」精度を評価するツールです。
拡張例としてシルエットスコア・クラス内クラス間コサイン類似度・
線形プルーブ・k-NN単体評価も同梱しています。

## 混同行列 + PCA可視化とは

分類器(既定: k-NN、線形プルーブにも切替可)を交差検証で学習・評価し、
以下の2つを組み合わせて確認します。

1. **混同行列 (Confusion Matrix)**
   「かぼちゃ を さといも と間違えた枚数」のように、
   どの野菜がどの野菜に間違われやすいかを表形式で確認できます。

2. **PCA可視化 (PCA scatter)**
   DINOv2特徴量を2次元に圧縮した散布図の上に、
   誤分類されたサンプルを赤丸で強調表示します。
   間違えたサンプルが「クラスの境界付近」にあるのか、
   「明らかな外れ値」なのかを視覚的に確認できます。

混同行列だけでは「何枚間違えたか」という数値情報しか得られませんが、
PCA可視化と組み合わせることで「なぜ間違えたのか」の手がかりが得られます。

## ファイル構成

```
vegetable_confusion_pca_eval/
├── data_loader.py                       # features_photo_homu以下を読み込む
├── feature_processor.py                 # cls/patchトークンを特徴ベクトルに変換する戦略群
├── evaluators/
│   ├── __init__.py                      # 評価手法のレジストリ(--methodで切替)
│   ├── base.py                          # 評価器の共通インターフェース(抽象基底クラス)
│   ├── confusion_pca_evaluator.py       # 混同行列+PCA可視化(メイン)
│   ├── intra_inter_cosine_evaluator.py  # [拡張例] クラス内・クラス間コサイン類似度(教師なし)
│   ├── silhouette_evaluator.py          # [拡張例] シルエットスコア(教師なし)
│   └── classification_evaluator.py      # [拡張例] k-NN/線形プルーブ単体(教師あり)
├── main.py                              # CLIエントリーポイント
├── dinov2_extractor.py                  # [拡張用] 新しい画像からDINOv2特徴量を抽出する
├── requirements.txt
└── README.md
```

想定するデータ構造(既存のもの):

```
features_photo_homu/
├── かぼちゃ/
│   ├── 001_cls.npy
│   ├── 001_patch.npy
│   ├── 002_cls.npy
│   ├── 002_patch.npy
│   └── ...
├── さといも/
│   └── ...
└── じゃがいも/
    └── ...
```

## セットアップ (VS Code)

1. `vegetable_confusion_pca_eval` フォルダを `features_photo_homu` と
   同じ階層に置くか、`--data-dir` オプションでパスを指定してください。
2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windowsは .venv\Scripts\activate
   ```
3. 依存ライブラリのインストール
   ```bash
   pip install -r requirements.txt
   ```

## 実行方法

```bash
# 既定: 混同行列+PCA可視化 (分類器=k-NN, clsトークン, Leave-One-Out)
python main.py --data-dir ../features_photo_homu --strategy cls

# 分類器を線形プルーブに切り替え、5分割交差検証にする場合
python main.py --classifier linear_probe --cv kfold --n-splits 5

# 誤分類の強調表示を消して、通常のクラス分布確認だけにする場合
python main.py --no-highlight-misclassified

# [拡張例] 他の評価手法に切り替えたい場合
python main.py --method silhouette --strategy cls
python main.py --method intra_inter_cosine --strategy cls
python main.py --method linear_probe --strategy cls
python main.py --method knn --k 5 --cv loo
```

実行すると `eval_results/` 配下に以下が保存されます。

- `report.txt`: Accuracy、クラスごとのprecision/recall/f1、
  誤分類したサンプルの正解ラベルと予測ラベルの一覧
- `confusion_matrix.png`: 混同行列のヒートマップ
- `pca_scatter.png`: 2次元PCA散布図（誤分類サンプルは赤丸で強調）

## 主なオプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--data-dir` | 特徴量ルートディレクトリ | `features_photo_homu` |
| `--strategy` | 特徴ベクトルの構築方法 (`cls`, `patch_mean`, `patch_max`, `cls_patch_mean_concat`, `cls_patch_maxmean_concat`) | `cls` |
| `--method` | 評価手法 (`confusion_pca`, `intra_inter_cosine`, `silhouette`, `linear_probe`, `knn`) | `confusion_pca` |
| `--classifier` | [confusion_pca] 混同行列を作る分類器 (`knn`, `linear_probe`) | `knn` |
| `--no-highlight-misclassified` | [confusion_pca] 誤分類サンプルの強調表示を無効化 | (指定なしでON) |
| `--cv` | 交差検証方法 (`loo`, `kfold`) | `loo` |
| `--n-splits` | `--cv kfold` のときの分割数 | `5` |
| `--k` | [knn / confusion_pca(classifier=knn)] k値 | `5` |
| `--C` | [linear_probe / confusion_pca(classifier=linear_probe)] 正則化の強さの逆数 | `1.0` |
| `--out-dir` | 結果出力先 | `eval_results` |

## 結果の読み方

- **confusion_matrix.png の対角成分**が大きいほど正しく分類できています。
  対角以外に値がある場合、行のラベルの野菜が列のラベルの野菜に
  間違われたことを意味します。
- **pca_scatter.png の赤丸**が付いたサンプルは誤分類されたサンプルです。
  - 赤丸が他のクラスの点群の中に埋もれている
    → 特徴量的に本当に紛らわしい写真だった可能性が高い
  - 赤丸が自分のクラスの点群からもかなり離れている
    → 撮影条件(ピンボケ、影、背景など)に問題がある外れ値の可能性

## 拡張方法

### 1. 野菜の種類を増やしたい
`features_photo_homu` の下に新しいディレクトリ(野菜名)を追加し、
同じ命名規則(`連番_cls.npy`, `連番_patch.npy`)でファイルを置くだけです。
`data_loader.py` の変更は不要です。

### 2. 特徴量の合成方法を増やしたい
`feature_processor.py` に `@register_strategy("新しい名前")` を付けた関数を
1つ追加するだけで、`main.py --strategy 新しい名前` として使えます。

### 3. 混同行列の分類器を増やしたい (SVMなど)
`evaluators/confusion_pca_evaluator.py` の `_build_estimator()` に
分岐を1つ追加し、`ConfusionPCAConfig.classifier` に新しい選択肢を
増やすだけで対応できます。

### 4. 別の評価指標を追加したい
`evaluators/新しい評価器.py` に `BaseEvaluator` を継承したクラスと
`build_xxx_evaluator()` を定義し、`evaluators/__init__.py` の
`METHOD_REGISTRY` に1行追加するだけで、`main.py --method xxx` として
使えるようになります。

### 5. 新しい写真からその場で特徴量を抽出したい
`dinov2_extractor.py` の `DINOv2Extractor` を使うと、
`features_photo_homu` の命名規則に沿った `.npy` を直接生成できます。
（`pip install torch torchvision transformers pillow` が別途必要です）

## 注意点

- 画像内の日本語ラベルは、環境に日本語フォントが入っていないと
  文字化けする場合があります。その場合はOSに日本語フォント
  (例: `Noto Sans CJK JP`)を追加してください。
- `cls.npy` の形状は `(D,)` または `(1, D)`、`patch.npy` の形状は
  `(N, D)` または `(1, N, D)` を想定しています（先頭の余分な次元は自動で吸収します）。
- PCAは元の高次元(DINOv2は768〜1536次元程度)を2次元に圧縮するため、
  情報の一部が失われます。散布図上でクラスが重なって見えても、
  実際の特徴空間ではきちんと分離できている場合があります
  （`--method silhouette` や `--method intra_inter_cosine` と
  併用して確認することをおすすめします）。
