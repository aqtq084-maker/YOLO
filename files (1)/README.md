# 野菜判定AI シルエットスコア精度評価ツール

DINOv2で抽出済みの特徴量(`_cls.npy` / `_patch.npy`)をもとに、
**シルエットスコア (Silhouette Score, 教師なし)** で
「野菜ごとの写真がDINOv2の特徴空間上でどれだけきれいに分かれているか」
を評価するツールです。拡張例として線形プルーブ・k-NN評価も同梱しています。

## シルエットスコアとは

分類器を一切学習させずに、特徴空間上での
「クラスタ(=野菜の種類)のまとまりの良さ」を測る指標です。

各サンプル `i` について:

- `a(i)` : 同じ野菜のクラス内の他サンプルとの平均距離（凝集度・小さいほど良い）
- `b(i)` : 最も近い「別の野菜」のクラスとの平均距離（分離度・大きいほど良い）
- `s(i) = (b(i) - a(i)) / max(a(i), b(i))`

`s(i)` は **-1〜1** の範囲を取り、

- **+1に近い**: 同じ野菜同士は近く、他の野菜とは離れている（理想的）
- **0付近**: クラス境界上にあり紛らわしい
- **-1に近い**: 別の野菜のクラスタに紛れ込んでいる

線形プルーブやk-NNが「分類器を学習させた上での正解率」を測るのに対し、
シルエットスコアは分類器を介さず、**DINOv2の特徴量そのものの質**を
直接評価できるのが特徴です。学習が不要なため、写真の枚数が少なくても
計算できます。

## ファイル構成

```
vegetable_silhouette_eval/
├── data_loader.py                     # features_photo_homu以下を読み込む
├── feature_processor.py               # cls/patchトークンを特徴ベクトルに変換する戦略群
├── evaluators/
│   ├── __init__.py                    # 評価手法のレジストリ(--methodで切替)
│   ├── base.py                        # 評価器の共通インターフェース(抽象基底クラス)
│   ├── silhouette_evaluator.py        # シルエットスコア(教師なし・メイン)
│   └── classification_evaluator.py    # [拡張例] k-NN/線形プルーブ(教師あり)
├── main.py                            # CLIエントリーポイント
├── dinov2_extractor.py                # [拡張用] 新しい画像からDINOv2特徴量を抽出する
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

1. `vegetable_silhouette_eval` フォルダを `features_photo_homu` と
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
# 既定: シルエットスコア (clsトークン, cosine距離)
python main.py --data-dir ../features_photo_homu --strategy cls

# ユークリッド距離で評価し、PCA散布図は省略する場合
python main.py --strategy cls --metric euclidean --no-pca-plot

# patch平均プーリングを使った特徴量で評価
python main.py --strategy patch_mean

# [拡張例] 教師あり評価(線形プルーブ/k-NN)に切り替えたい場合
python main.py --method linear_probe --strategy cls
python main.py --method knn --k 5 --cv loo
```

実行すると `eval_results/` 配下に以下が保存されます。

- `report.txt`: 全体のシルエットスコアとクラスごとの平均スコア
- `silhouette_plot.png`: クラスごとにサンプルのシルエット値を並べたプロット
  （野菜ごとにどれだけ「まとまって」いるかを一目で確認できる）
- `pca_scatter.png`: 特徴量を2次元PCAに圧縮した散布図
  （実際にクラスがどう分布しているかを視覚的に確認できる）

## 主なオプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--data-dir` | 特徴量ルートディレクトリ | `features_photo_homu` |
| `--strategy` | 特徴ベクトルの構築方法 (`cls`, `patch_mean`, `patch_max`, `cls_patch_mean_concat`, `cls_patch_maxmean_concat`) | `cls` |
| `--method` | 評価手法 (`silhouette`, `linear_probe`, `knn`) | `silhouette` |
| `--metric` | [silhouette/knn] 距離指標 (`cosine`, `euclidean` など) | `cosine` |
| `--no-pca-plot` | [silhouette] PCA散布図の出力を無効化 | (指定なしで出力ON) |
| `--cv` | [linear_probe/knn] 交差検証方法 (`loo`, `kfold`) | `kfold` |
| `--n-splits` | [linear_probe/knn] kfoldの分割数 | `5` |
| `--C` | [linear_probe] 正則化の強さの逆数 | `1.0` |
| `--k` | [knn] k値 | `5` |
| `--out-dir` | 結果出力先 | `eval_results` |

## シルエットスコアの読み方の目安

| スコア | 目安 |
|---|---|
| 0.7 〜 1.0 | 非常に明確に分離できている |
| 0.5 〜 0.7 | ある程度分離できている |
| 0.25 〜 0.5 | 分離は弱いが構造は見える |
| 0.25未満 | ほとんど分離できていない可能性 |

あくまで目安であり、特徴量の次元数やデータ数によっても変わるため、
`--strategy`(cls / patch_mean など)や `--metric` を変えて比較し、
**相対的にどの特徴量の組み合わせが良いか**を見るのがおすすめです。

## 拡張方法

### 1. 野菜の種類を増やしたい
`features_photo_homu` の下に新しいディレクトリ(野菜名)を追加し、
同じ命名規則(`連番_cls.npy`, `連番_patch.npy`)でファイルを置くだけです。
`data_loader.py` の変更は不要です。

### 2. 特徴量の合成方法を増やしたい
`feature_processor.py` に `@register_strategy("新しい名前")` を付けた関数を
1つ追加するだけで、`main.py --strategy 新しい名前` として使えます。

### 3. 別の教師なし指標を追加したい (Davies-Bouldin指数など)
`evaluators/新しい評価器.py` に `BaseEvaluator` を継承したクラスと
`build_xxx_evaluator()` を定義し、`evaluators/__init__.py` の
`METHOD_REGISTRY` に1行追加するだけで、`main.py --method xxx` として
使えるようになります。各評価器は `evaluate(X, y, out_dir)` の中で
自分のレポート・画像を自己完結的に保存する設計です。

### 4. 新しい写真からその場で特徴量を抽出したい
`dinov2_extractor.py` の `DINOv2Extractor` を使うと、
`features_photo_homu` の命名規則に沿った `.npy` を直接生成できます。
（`pip install torch torchvision transformers pillow` が別途必要です）

## 注意点

- シルエットスコアは「特徴空間上の分かれ方」を見る指標であり、
  実際の分類精度(Accuracy)とは別の観点の評価です。
  スコアが低くても、線形プルーブ/k-NNでは十分な精度が出ることもあります。
  両方を併用して確認することをおすすめします。
- 1クラスのサンプル数が1枚しかない場合、そのサンプルのシルエット値は
  定義上0として扱われます（比較対象がいないため）。
- 画像内の日本語ラベルは、環境に日本語フォントが入っていないと
  文字化けする場合があります。その場合はOSに日本語フォント
  (例: `Noto Sans CJK JP`)を追加してください。
- `cls.npy` の形状は `(D,)` または `(1, D)`、`patch.npy` の形状は
  `(N, D)` または `(1, N, D)` を想定しています（先頭の余分な次元は自動で吸収します）。
