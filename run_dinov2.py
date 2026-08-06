"""
DINOv2 画像特徴量抽出スクリプト

特徴:
- 実行時に画像フォルダを指定可能
- 出力先を指定可能
- モデル選択可能
- サブフォルダ（野菜カテゴリ）を維持して保存

例:
野菜画像/
├── かぼちゃ/
│   ├── 001.jpg
│   └── 002.jpg
│
├── だいこん/
│   ├── 001.jpg
│   └── 002.jpg


出力:
features/
├── かぼちゃ/
│   ├── 001_cls.npy
│   └── 001_patch.npy
│
└── だいこん/
    ├── 001_cls.npy
    └── 001_patch.npy
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel


# ===============================
# 使用可能モデル
# ===============================

MODEL_MAP = {
    "dinov2-small": "facebook/dinov2-small",
    "dinov2-base": "facebook/dinov2-base",
    "dinov2-large": "facebook/dinov2-large",
    "dinov2-giant": "facebook/dinov2-giant",
}


# ===============================
# GPU確認
# ===============================

def check_gpu():

    if not torch.cuda.is_available():

        print("[警告] CUDAが利用できません")
        print("CPUで実行します")

        return torch.device("cpu")


    device = torch.device("cuda:0")

    name = torch.cuda.get_device_name(0)
    cap = torch.cuda.get_device_capability(0)

    print(
        f"[情報] GPU: {name} "
        f"(sm_{cap[0]}{cap[1]})"
    )

    return device



# ===============================
# モデルロード
# ===============================

def load_model(model_name, device):

    hf_name = MODEL_MAP[model_name]

    print(
        f"[情報] モデルロード: {hf_name}"
    )


    processor = AutoImageProcessor.from_pretrained(
        hf_name
    )

    model = AutoModel.from_pretrained(
        hf_name
    )


    model.eval()
    model.to(device)


    # RTX5080向け
    if device.type == "cuda":

        model = model.to(
            dtype=torch.bfloat16
        )


    return processor, model



# ===============================
# 特徴量抽出
# ===============================

@torch.no_grad()
def extract_features(
        image_path,
        processor,
        model,
        device
):

    image = Image.open(
        image_path
    ).convert("RGB")


    inputs = processor(
        images=image,
        return_tensors="pt"
    )


    inputs = {
        k:v.to(device)
        for k,v in inputs.items()
    }


    if device.type == "cuda":

        inputs = {
            k:
            v.to(dtype=torch.bfloat16)
            if v.dtype.is_floating_point
            else v

            for k,v in inputs.items()
        }


    outputs = model(**inputs)


    # CLS特徴量
    cls_token = (
        outputs.last_hidden_state[:,0,:]
    )


    # Patch特徴量
    patch_tokens = (
        outputs.last_hidden_state[:,1:,:]
    )


    return (
        cls_token.float()
        .cpu()
        .numpy(),

        patch_tokens.float()
        .cpu()
        .numpy()
    )



# ===============================
# 画像一覧取得
# ===============================

def gather_image_paths(
        image,
        image_dir
):

    extensions = (
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".webp"
    )


    if image:

        return [
            (
                Path(image),
                Path("")
            )
        ]



    image_dir = Path(image_dir)


    paths = sorted(
        [
            p
            for p in image_dir.rglob("*")
            if p.suffix.lower()
            in extensions
        ]
    )


    return [
        (
            p,
            p.parent.relative_to(image_dir)
        )
        for p in paths
    ]



# ===============================
# メイン
# ===============================

def main():


    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--image",
        type=str,
        default=None
    )


    parser.add_argument(
        "--image_dir",
        type=str,
        default=None
    )


    parser.add_argument(
        "--output_dir",
        type=str,
        default="features"
    )


    parser.add_argument(
        "--model",
        type=str,
        default="dinov2-base",
        choices=list(MODEL_MAP.keys())
    )


    args = parser.parse_args()



    # ===============================
    # 対話入力
    # ===============================


    if (
        args.image is None
        and args.image_dir is None
    ):

        args.image_dir = input(
            "画像フォルダを入力してください: "
        ).strip()



    if args.output_dir == "features":

        output = input(
            "出力フォルダ "
            "(Enterでfeatures): "
        ).strip()


        if output:

            args.output_dir = output



    model_input = input(
        "モデル "
        "(small/base/large/giant) "
        "[base]: "
    ).strip()



    if model_input:


        if model_input.startswith(
            "dinov2-"
        ):

            args.model = model_input

        else:

            args.model = (
                "dinov2-"
                + model_input
            )



    print("\n========== 設定 ==========")

    print(
        f"画像 : {args.image_dir}"
    )

    print(
        f"出力 : {args.output_dir}"
    )

    print(
        f"モデル : {args.model}"
    )

    print(
        "==========================\n"
    )



    # GPU

    device = check_gpu()



    # モデル

    processor, model = load_model(
        args.model,
        device
    )



    # 画像取得

    images = gather_image_paths(
        args.image,
        args.image_dir
    )



    output_dir = Path(
        args.output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )



    # ===============================
    # 推論
    # ===============================


    for path, rel_dir in images:


        cls_feat, patch_feat = extract_features(
            path,
            processor,
            model,
            device
        )


        print(
            f"[完了] {path}"
        )

        print(
            f" CLS : {cls_feat.shape}"
        )

        print(
            f" Patch : {patch_feat.shape}"
        )



        save_dir = (
            output_dir
            /
            rel_dir
        )


        save_dir.mkdir(
            parents=True,
            exist_ok=True
        )



        np.save(
            save_dir
            /
            f"{path.stem}_cls.npy",
            cls_feat
        )


        np.save(
            save_dir
            /
            f"{path.stem}_patch.npy",
            patch_feat
        )



    print(
        "\n特徴量抽出完了"
    )

    print(
        f"保存先: {output_dir}"
    )



if __name__ == "__main__":

    main()
