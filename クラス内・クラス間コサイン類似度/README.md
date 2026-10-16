# 野菜判定AI クラス内・クラス間コサイン類似度 精度評価ツール

DINOv2で抽出済みの特徴量(`_cls.npy` / `_patch.npy`)をもとに、
**クラス内・クラス間コサイン類似度 (教師なし)** で
「同じ野菜同士がどれだけ似ているか」「違う野菜同士がどれだけ似ていないか」
を評価するツールです。拡張例としてシルエットスコア・線形プルーブ・k-NN評価も同梱しています。

## クラス内・クラス間コサイン類似度とは

分類器を一切学習させずに、DINOv2の特徴空間上で
2種類の平均コサイン類似度を直接比較する指標です。

- **クラス内類似度 (intra-class similarity)**
  同じ野菜のサンプル同士のコサイン類似度の平均。
  **1に近いほど**、同じ野菜の写真はどれも似た特徴を持つ(理想的)。

- **クラス間類似度 (inter-class similarity)**
  異なる野菜のサンプル同士のコサイン類似度の平均。
  **低いほど**、違う野菜どうしがきちんと区別できている(理想的)。

- **分離マージン (margin) = クラス内類似度 − クラス間類似度**
  大きいほど「同じ野菜は似ていて、違う野菜とは似ていない」
  = 特徴量として良い性質を持つことを意味します。

シルエットスコアが「各サンプルにとって最も近い別クラス」だけを見るのに
対し、こちらは**すべてのクラスペアの組み合わせ**を網羅的に算出するため、
「かぼちゃ と ズッキーニ は特に混同されやすい」といった、
**具体的にどの野菜同士が紛らわしいか**を特定しやすいのが特徴です。

## ファイル構成

```
vegetable_cosine_eval/
├── data_loader.py                     # features_photo_homu以下を読み込む
├── feature_processor.py               # cls/patchトークンを特徴ベクトルに変換する戦略群
├── evaluators/
│   ├── __init__.py                    # 評価手法のレジストリ(--methodで切替)
│   ├── base.py                        # 評価器の共通インターフェース(抽象基底クラス)
│   ├── intra_inter_cosine_evaluator.py  # クラス内・クラス間コサイン類似度(教師なし・メイン)
│   ├── silhouette_evaluator.py        # [拡張例] シルエットスコア(教師なし)
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

1. `vegetable_cosine_eval` フォルダを `features_photo_homu` と
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
# 既定: クラス内・クラス間コサイン類似度 (clsトークン)
python main.py --data-dir ../features_photo_homu --strategy cls

# ヒートマップを省略し、混同しやすいペアを10件表示する場合
python main.py --strategy cls --no-heatmap --top-k-pairs 10

# patch平均プーリングを使った特徴量で評価
python main.py --strategy patch_mean

# [拡張例] 他の評価手法に切り替えたい場合
python main.py --method silhouette --strategy cls
python main.py --method linear_probe --strategy cls
python main.py --method knn --k 5 --cv loo
```

実行すると `eval_results/` 配下に以下が保存されます。

- `report.txt`: 全体のクラス内/クラス間類似度、分離マージン、
  クラスごとの詳細、混同しやすいクラスペアTop-N
- `cosine_heatmap.png`: クラス×クラスの類似度行列のヒートマップ
  （対角=クラス内類似度、非対角=クラス間類似度。色が濃い非対角セルほど
  そのペアの野菜が混同されやすい可能性がある）

## 主なオプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--data-dir` | 特徴量ルートディレクトリ | `features_photo_homu` |
| `--strategy` | 特徴ベクトルの構築方法 (`cls`, `patch_mean`, `patch_max`, `cls_patch_mean_concat`, `cls_patch_maxmean_concat`) | `cls` |
| `--method` | 評価手法 (`intra_inter_cosine`, `silhouette`, `linear_probe`, `knn`) | `intra_inter_cosine` |
| `--no-heatmap` | [intra_inter_cosine] ヒートマップ出力を無効化 | (指定なしで出力ON) |
| `--top-k-pairs` | [intra_inter_cosine] 混同しやすいペアの表示件数 | `5` |
| `--metric` | [silhouette/knn] 距離指標 | `cosine` |
| `--cv` | [linear_probe/knn] 交差検証方法 (`loo`, `kfold`) | `kfold` |
| `--k` | [knn] k値 | `5` |
| `--C` | [linear_probe] 正則化の強さの逆数 | `1.0` |
| `--out-dir` | 結果出力先 | `eval_results` |

## 数値の読み方

- **分離マージンが大きい(目安: 0.2以上など)**: 特徴量として良好。
  同じ野菜はまとまり、違う野菜とはしっかり離れている。
- **分離マージンが小さい/0に近い**: 特徴量だけでは野菜同士の区別が
  難しい可能性がある。`--strategy` を変えて(例: `patch_mean` や
  `cls_patch_mean_concat`)、より分離しやすい特徴量の組み合わせを探すか、
  分類器側(線形プルーブ等)で補う必要があるかもしれません。
- **特定のクラスペアだけ類似度が高い**: `cosine_heatmap.png` や
  レポートの「混同しやすいクラスペア」を確認し、
  見た目が似ている野菜(例: 似た葉の形)である可能性を検討してください。

あくまで相対的な目安であり、絶対的な合格ラインがあるわけではないため、
`--strategy` や `--method` を変えながら比較するのがおすすめです。

## 拡張方法

### 1. 野菜の種類を増やしたい
`features_photo_homu` の下に新しいディレクトリ(野菜名)を追加し、
同じ命名規則(`連番_cls.npy`, `連番_patch.npy`)でファイルを置くだけです。
`data_loader.py` の変更は不要です。

### 2. 特徴量の合成方法を増やしたい
`feature_processor.py` に `@register_strategy("新しい名前")` を付けた関数を
1つ追加するだけで、`main.py --strategy 新しい名前` として使えます。

### 3. 別の評価指標を追加したい
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

- サンプルが1枚しかないクラスは「クラス内類似度」が定義できないため、
  レポート上は該当クラスのintraが計算対象外になります(NaN扱い)。
  可能であれば1クラスあたり最低2枚以上の写真を用意してください。
- サンプル数が非常に多い場合、全ペアのコサイン類似度行列(n×n)の計算に
  時間がかかることがあります。数千枚程度までは通常問題ありません。
- 画像内の日本語ラベルは、環境に日本語フォントが入っていないと
  文字化けする場合があります。その場合はOSに日本語フォント
  (例: `Noto Sans CJK JP`)を追加してください。
- `cls.npy` の形状は `(D,)` または `(1, D)`、`patch.npy` の形状は
  `(N, D)` または `(1, N, D)` を想定しています（先頭の余分な次元は自動で吸収します）。
