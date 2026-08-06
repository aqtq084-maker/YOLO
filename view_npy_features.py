"""
DINOv2で抽出した特徴量(.npy)の中身を確認・可視化するスクリプト

使い方:
  # 1つのファイルの中身を表示
  python view_npy_features.py --file features/1_cls.npy

  # 2つのファイルの類似度を比較
  python view_npy_features.py --compare features/1_cls.npy features/2_cls.npy
  python view_npy_features.py --compare features_photo_homu/かぼちゃ/001_cls.npy features_photo_homu/すいか/s
uika_001_cls.npy

  # ヒートマップとして画像で保存
  python view_npy_features.py --file features/1_cls.npy --plot heatmap.png

依存パッケージ:
  pip install numpy matplotlib
"""

import argparse

import numpy as np


def show_info(path: str):
    data = np.load(path)
    print(f"ファイル: {path}")
    print(f"  shape: {data.shape}")
    print(f"  dtype: {data.dtype}")
    print(f"  min={data.min():.4f}  max={data.max():.4f}  mean={data.mean():.4f}")
    print(f"  先頭10要素: {data.flatten()[:10]}")
    return data


def compare(path_a: str, path_b: str):
    a = np.load(path_a).flatten()
    b = np.load(path_b).flatten()
    cos_sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    print(f"{path_a} と {path_b} のコサイン類似度: {cos_sim:.4f}")
    print("(1.0に近いほど似ている画像、0や負の値に近いほど似ていない画像)")


def plot_heatmap(path: str, out_path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = np.load(path)
    if data.ndim == 2 and data.shape[0] == 1:
        data = data.reshape(-1, 1)  # CLSベクトルを縦長に整形して見やすく

    plt.figure(figsize=(6, 8))
    plt.imshow(data, aspect="auto", cmap="viridis")
    plt.colorbar(label="特徴量の値")
    plt.title(f"{path}\nshape={data.shape}")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"ヒートマップを保存しました: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="npy特徴量ファイルの確認ツール")
    parser.add_argument("--file", type=str, default=None, help="中身を確認したい.npyファイル")
    parser.add_argument("--compare", type=str, nargs=2, default=None,
                         metavar=("FILE_A", "FILE_B"), help="2ファイルの類似度を比較")
    parser.add_argument("--plot", type=str, default=None, help="--fileと併用。ヒートマップ画像の保存先パス")
    args = parser.parse_args()

    if args.compare:
        compare(args.compare[0], args.compare[1])
    elif args.file:
        show_info(args.file)
        if args.plot:
            plot_heatmap(args.file, args.plot)
    else:
        parser.error("--file か --compare のいずれかを指定してください")


if __name__ == "__main__":
    main()