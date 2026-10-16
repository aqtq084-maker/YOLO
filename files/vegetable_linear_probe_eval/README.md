# 野菜判定AI 線形プルーブ精度評価ツール

DINOv2で抽出済みの特徴量(`_cls.npy` / `_patch.npy`)をもとに、
**線形プルーブ (Linear Probe)** で「野菜の葉の写真から野菜名を当てる」
精度を評価するツールです。拡張例として k-NN 評価も同梱しています。

## 線形プルーブとは

DINOv2のような自己教師あり学習(SSL)モデルの特徴量の質を評価する
代表的な方法です。

- バックボーン(DINOv2)は完全に凍結(freeze)したまま更新しない
- その特徴量の上に**単純な線形分類器(ロジスティック回帰)だけ**を学習させる
- その精度で「特徴空間内でクラスがどれだけ線形分離可能か」を測る

k-NNやSVM(RBFカーネル)のような複雑な分類器を使わないことで、
「分類器側の頑張り」ではなく「特徴表現そのものの質」を素直に評価できます。

## ファイル構成

```
vegetable_linear_probe_eval/
├── data_loader.py                       # features_photo_homu以下を読み込む
├── feature_processor.py                 # cls/patchトークンを特徴ベクトルに変換する戦略群
├── evaluators/
│   ├── __init__.py                      # 評価手法のレジストリ(--methodで切替)
│   ├── base.py                          # 交差検証・レポート生成の共通ロジック
│   ├── linear_probe_evaluator.py        # 線形プルーブ(ロジスティック回帰)
│   └── knn_evaluator.py                 # [拡張例] k-NN評価器
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

1. `vegetable_linear_probe_eval` フォルダを `features_photo_homu` と
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
# 既定: 線形プルーブ (clsトークン, 5分割層化交差検証)
python main.py --data-dir ../features_photo_homu --strategy cls

# 正則化を強くする(過学習が疑われる場合)
python main.py --strategy cls --C 0.1

# patch平均プーリング + Leave-One-Out交差検証
python main.py --strategy patch_mean --cv loo

# [拡張例] k-NNで評価したい場合、同じCLIのまま手法だけ切り替え可能
python main.py --method knn --k 5 --metric cosine --cv loo
```

実行すると以下が出力されます。

- コンソール: クラスごとのサンプル数、Accuracy、クラスごとのprecision/recall/f1
- `eval_results/report.txt`: 上記のテキストレポート
- `eval_results/confusion_matrix.png`: 混同行列の画像

## 主なオプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--data-dir` | 特徴量ルートディレクトリ | `features_photo_homu` |
| `--strategy` | 特徴ベクトルの構築方法 (`cls`, `patch_mean`, `patch_max`, `cls_patch_mean_concat`, `cls_patch_maxmean_concat`) | `cls` |
| `--method` | 評価手法 (`linear_probe`, `knn`) | `linear_probe` |
| `--cv` | 交差検証方法 (`loo`, `kfold`) | `kfold` |
| `--n-splits` | `--cv kfold` のときの分割数 | `5` |
| `--C` | [linear_probe] 正則化の強さの逆数(小さいほど正則化が強い) | `1.0` |
| `--max-iter` | [linear_probe] 最大反復回数 | `2000` |
| `--no-standardize` | [linear_probe] 特徴量の標準化を無効化 | (指定なしで標準化ON) |
| `--class-weight` | [linear_probe] クラス重み (`balanced` または `none`) | `balanced` |
| `--k` | [knn] k-NNのk値 | `5` |
| `--metric` | [knn] 距離指標 | `cosine` |
| `--weights` | [knn] 重み付け方法 (`uniform`, `distance`) | `distance` |
| `--out-dir` | 結果出力先 | `eval_results` |

## 評価方法について (なぜ交差検証か)

野菜1種類あたりの写真枚数が少ないケースが多いため、学習用・評価用を
固定で分割すると精度の見積もりが不安定になりがちです。本ツールでは
`cross_val_predict` を使い、全サンプルに対する予測結果から
Accuracy・混同行列・クラスごとのprecision/recall/f1を算出しています。

- **層化K分割 (kfold, 既定)**: クラス比率を保ったままK個に分割。
  線形プルーブは学習に一定量のデータを使うため、通常はこちらを推奨。
- **Leave-One-Out (loo)**: 1枚だけテストに使い残り全部で学習、を繰り返す。
  データ数が極端に少ない場合向け。

## 拡張方法

### 1. 野菜の種類を増やしたい
`features_photo_homu` の下に新しいディレクトリ(野菜名)を追加し、
同じ命名規則(`連番_cls.npy`, `連番_patch.npy`)でファイルを置くだけです。
`data_loader.py` の変更は不要です。

### 2. 特徴量の合成方法を増やしたい
`feature_processor.py` に `@register_strategy("新しい名前")` を付けた関数を
1つ追加するだけで、`main.py --strategy 新しい名前` として使えます。

### 3. 評価手法を増やしたい (線形SVMなど)
`evaluators/新しい評価器.py` に `XxxConfig` と `build_xxx_evaluator()` を
定義し、`evaluators/__init__.py` の `METHOD_REGISTRY` に1行追加するだけで、
`main.py --method xxx` として使えます。線形プルーブ・k-NNはどちらも
`evaluators/base.py` の `SklearnCVEvaluator` を利用しているため、
scikit-learn互換のestimator(fit/predictを持つもの)であれば
同じ枠組みにそのまま載せられます。

### 4. 新しい写真からその場で特徴量を抽出したい
`dinov2_extractor.py` の `DINOv2Extractor` を使うと、
`features_photo_homu` の命名規則に沿った `.npy` を直接生成できます。
（`pip install torch torchvision transformers pillow` が別途必要です）

## 注意点

- `confusion_matrix.png` 内の野菜名(日本語)は、環境に日本語フォントが
  入っていないと文字化けする場合があります。その場合はOSに日本語フォント
  (例: `Noto Sans CJK JP`)を追加するか、`main.py` の `_plot_confusion_matrix`
  内でフォントを指定してください。
- `cls.npy` の形状は `(D,)` または `(1, D)`、`patch.npy` の形状は
  `(N, D)` または `(1, N, D)` を想定しています（先頭の余分な次元は自動で吸収します）。
- 線形プルーブはサンプル数が極端に少ない(1クラス数枚など)場合、
  ロジスティック回帰が不安定になることがあります。その場合は
  `--C` を小さくして正則化を強めるか、`--cv loo` を試してください。
