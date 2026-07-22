"""
DINOv2 を Linux PC (RTX 5080 搭載) 上で動かすスクリプト

■ 事前準備 (RTX 5080 = Blackwell / sm_120 のための環境構築)
--------------------------------------------------------------
RTX 5080はBlackwellアーキテクチャ(sm_120)のため、CUDA 12.8以降に対応した
PyTorchが必要です。PyTorch 2.7.0以降の安定版であればcu128向けビルドが
公式提供されているため、以下でインストールしてください。

  # 既存のtorchを削除(入っている場合)
  pip uninstall torch torchvision torchaudio -y

  # CUDA 12.8対応の安定版PyTorchをインストール
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

  # DINOv2の実行に必要なパッケージ
  pip install transformers pillow numpy

  # GPU認識確認
  python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"

  ※ 上記でエラーが出る場合は、NVIDIAドライバがCUDA 12.8以降に対応しているか
    (nvidia-smi の CUDA Version表示を確認)、driverの更新も検討してください。

■ 対応フォルダ構成
--------------------------------------------------------------
  images_DINOv2/
    だいこん/
      daikon_1.jpg
      daikon_2.jpg
    かぼちゃ/
      kabotya_1.jpg
      ...

  上記のようにカテゴリ別サブフォルダに画像が入っている場合、--image_dir に
  images_DINOv2 を指定すると、サブフォルダを再帰的に探索してすべて処理します。
  (crop_yolo_annotations.py の出力フォルダ(output/だいこん/...)をそのまま
   --image_dir に指定してもOKです)

  出力される特徴量(.npy)もカテゴリ構成を保ったまま features/ 以下に保存されます。
    features/
      だいこん/
        daikon_1_cls.npy
        daikon_1_patch.npy
      かぼちゃ/
        kabotya_1_cls.npy
        ...

■ 使い方
--------------------------------------------------------------
  # 単一画像から特徴量(CLSトークン)を抽出
  python run_dinov2_rtx5080.py --image path/to/image.jpg

  # カテゴリ別サブフォルダを含むディレクトリを再帰的にバッチ処理
  python run_dinov2_rtx5080.py --image_dir images_DINOv2 --output_dir features --model dinov2-base

  --model で選択可能: dinov2-small / dinov2-base / dinov2-large / dinov2-giant
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

MODEL_MAP = {
    "dinov2-small": "facebook/dinov2-small",
    "dinov2-base": "facebook/dinov2-base",
    "dinov2-large": "facebook/dinov2-large",
    "dinov2-giant": "facebook/dinov2-giant",
}


def check_gpu():
    if not torch.cuda.is_available():
        print("[警告] CUDAが利用できません。CPUで実行します(低速)。")
        print("       RTX5080を使う場合はCUDA12.8対応のPyTorchが正しくインストールされているか確認してください。")
        return torch.device("cpu")

    device = torch.device("cuda:0")
    name = torch.cuda.get_device_name(0)
    cap = torch.cuda.get_device_capability(0)
    print(f"[情報] 使用GPU: {name} (compute capability sm_{cap[0]}{cap[1]})")
    return device


def load_model(model_name: str, device: torch.device):
    hf_name = MODEL_MAP[model_name]
    print(f"[情報] モデルをロード中: {hf_name}")
    processor = AutoImageProcessor.from_pretrained(hf_name)
    model = AutoModel.from_pretrained(hf_name)
    model.eval().to(device)

    # RTX5080はTensorCore(fp16/bf16)で高速化可能
    if device.type == "cuda":
        model = model.to(dtype=torch.bfloat16)

    return processor, model


@torch.no_grad()
def extract_features(image_path: Path, processor, model, device: torch.device):
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)

    if device.type == "cuda":
        inputs = {k: v.to(dtype=torch.bfloat16) if v.dtype.is_floating_point else v
                   for k, v in inputs.items()}

    outputs = model(**inputs)

    # CLSトークン(画像全体の特徴量)とパッチトークン(局所特徴量)
    cls_token = outputs.last_hidden_state[:, 0, :]          # shape: (1, hidden_dim)
    patch_tokens = outputs.last_hidden_state[:, 1:, :]      # shape: (1, num_patches, hidden_dim)

    return cls_token.float().cpu().numpy(), patch_tokens.float().cpu().numpy()


def gather_image_paths(image: str, image_dir: str):
    """処理対象の画像パス一覧を取得する。

    --image_dir の場合はサブフォルダ(カテゴリフォルダ)も再帰的に探索する。
    戻り値は (画像パス, image_dirからの相対パスの親ディレクトリ) のタプルのリスト。
    単一画像指定時の相対ディレクトリは空文字列(Path(""))とする。
    """
    exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

    if image:
        return [(Path(image), Path(""))]

    if image_dir:
        image_dir = Path(image_dir)
        paths = sorted(p for p in image_dir.rglob("*") if p.suffix.lower() in exts)
        return [(p, p.parent.relative_to(image_dir)) for p in paths]

    raise ValueError("--image か --image_dir のいずれかを指定してください")


def main():
    parser = argparse.ArgumentParser(description="DINOv2による画像特徴量抽出 (RTX5080向け)")
    parser.add_argument("--image", type=str, default=None, help="単一画像のパス")
    parser.add_argument("--image_dir", type=str, default=None, help="複数画像が入ったディレクトリ")
    parser.add_argument("--output_dir", type=str, default="features", help="特徴量(.npy)の保存先")
    parser.add_argument("--model", type=str, default="dinov2-base", choices=list(MODEL_MAP.keys()))
    args = parser.parse_args()

    device = check_gpu()
    processor, model = load_model(args.model, device)

    image_entries = gather_image_paths(args.image, args.image_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for path, rel_dir in image_entries:
        cls_feat, patch_feat = extract_features(path, processor, model, device)
        rel_label = f"{rel_dir}/" if str(rel_dir) not in ("", ".") else ""
        print(f"[完了] {rel_label}{path.name}: CLS特徴量 shape={cls_feat.shape}, パッチ特徴量 shape={patch_feat.shape}")

        save_dir = output_dir / rel_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        np.save(save_dir / f"{path.stem}_cls.npy", cls_feat)
        np.save(save_dir / f"{path.stem}_patch.npy", patch_feat)

    print(f"すべての特徴量を {output_dir} に保存しました")


if __name__ == "__main__":
    main()
