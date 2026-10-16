# 野菜判定AI k-NN精度評価ツール

DINOv2で抽出済みの特徴量(`_cls.npy` / `_patch.npy`)をもとに、
k-NN分類器で「野菜の葉の写真から野菜名を当てる」精度を評価するツールです。

## ファイル構成

```
vegetable_knn_eval/
├── data_loader.py        # features_photo_homu以下を読み込む
├── feature_processor.py  # cls/patchトークンを特徴ベクトルに変換する戦略群
├── evaluator.py           # k-NN + 交差検証で精度を評価する
├── main.py                # CLIエントリーポイント
├── dinov2_extractor.py    # [拡張用] 新しい画像からDINOv2特徴量を抽出する
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

1. `vegetable_knn_eval` フォルダを `features_photo_homu` と同じ階層に置くか、
   `--data-dir` オプションでパスを指定してください。
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
# 最もシンプルな評価 (clsトークンのみ, Leave-One-Out交差検証)
python main.py --data-dir ../features_photo_homu --strategy cls --k 5

# patchトークンを平均プーリングして使う場合
python main.py --data-dir ../features_photo_homu --strategy patch_mean --k 3 --metric cosine

# clsとpatch平均を連結して使う場合 + 5分割の層化交差検証
python main.py --strategy cls_patch_mean_concat --cv kfold --n-splits 5
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
| `--k` | k-NNのk値 | `5` |
| `--metric` | 距離指標 (`cosine`, `euclidean`, `manhattan` など) | `cosine` |
| `--cv` | 交差検証方法 (`loo`=Leave-One-Out, `kfold`=層化K分割) | `loo` |
| `--n-splits` | `--cv kfold` のときの分割数 | `5` |
| `--weights` | k-NNの重み付け (`uniform`, `distance`) | `distance` |
| `--out-dir` | 結果出力先 | `eval_results` |

## 評価方法について (なぜ交差検証か)

野菜1種類あたりの写真枚数が少ないケースが多いため、学習用・評価用に
固定で分割してしまうと精度の見積もりが不安定になります。
そこで本ツールでは:

- **Leave-One-Out (LOO)**: 1枚だけをテストに使い、残り全部で学習する、を全サンプル分繰り返す。
  データ数が少ない場合(目安: 数十枚程度まで)におすすめ。
- **層化K分割 (kfold)**: クラスの比率を保ったままK個に分割して交差検証する。
  データ数がある程度多い場合はこちらのほうが高速。

いずれも `cross_val_predict` を使い、全サンプルに対する予測結果から
Accuracy・混同行列・クラスごとのprecision/recall/f1を算出しています。

## 拡張方法

### 1. 野菜の種類を増やしたい
`features_photo_homu` の下に新しいディレクトリ(野菜名)を追加し、
同じ命名規則(`連番_cls.npy`, `連番_patch.npy`)でファイルを置くだけです。
`data_loader.py` の変更は不要です。

### 2. 特徴量の合成方法を増やしたい
`feature_processor.py` に `@register_strategy("新しい名前")` を付けた関数を
1つ追加するだけで、`main.py --strategy 新しい名前` として使えるようになります。

```python
@register_strategy("patch_mean_weighted")
def _patch_mean_weighted(sample: Sample) -> np.ndarray:
    ...
    return vec
```

### 3. 新しい写真からその場で特徴量を抽出したい
`dinov2_extractor.py` の `DINOv2Extractor` を使うと、
`features_photo_homu` の命名規則に沿った `.npy` を直接生成できます。
（`pip install torch torchvision transformers pillow` が別途必要です）

### 4. k-NN以外の分類器も比較したい
`evaluator.py` の `KNNEvaluator` と同じ `evaluate(X, y) -> EvalResult`
インターフェースを持つクラスを追加すれば、`main.py` はほぼそのまま
分類器を差し替えて使えます。

## 注意点

- `confusion_matrix.png` 内の野菜名(日本語)は、環境に日本語フォントが
  入っていないと文字化けする場合があります。その場合はOSに日本語フォント
  (例: `Noto Sans CJK JP`)を追加するか、`main.py` の `_plot_confusion_matrix`
  内でフォントを指定してください。
- `cls.npy` の形状は `(D,)` または `(1, D)`、`patch.npy` の形状は
  `(N, D)` または `(1, N, D)` を想定しています（先頭の余分な次元は自動で吸収します）。
