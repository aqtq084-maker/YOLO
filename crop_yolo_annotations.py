"""
YOLO形式アノテーションデータをもとに画像を矩形クロップするスクリプト

想定するディレクトリ構成 (カテゴリ分けなし、フラット構成):

  images/
    1.jpg
    2.jpg
    3.jpg
    ...

  labels/
    1.txt   (YOLO形式: class_id x_center y_center width height ※0〜1正規化)
    2.txt
    3.txt
    ...

  ※ images と labels で同じ連番(拡張子を除いたファイル名)のファイル同士をペアとして扱います。
    (例: images/15.jpg と labels/15.txt が対応)

出力:
  output/
    1_000_cls0.jpg
    2_000_cls0.jpg
    ...
  ファイル名: {元画像の連番}_{ボックス通番}_cls{class_id}.jpg
  (1枚の画像に複数のバウンディングボックスがある場合はボックス通番で区別)

使い方:
  python crop_yolo_annotations.py \
      --images_dir images \
      --labels_dir labels \
      --output_dir output \
      --margin 0.0 \
      --classes 0 1 2      # 省略時は全クラス対象

  ※ images_dir / labels_dir / output_dir は省略可能で、その場合はこのスクリプトと
    同じ階層にある images / labels / output を自動的に使用します。

依存パッケージ:
  pip install opencv-python
"""

import argparse
from pathlib import Path

import cv2


def parse_yolo_line(line: str):
    """1行分のYOLOアノテーション文字列を解析する"""
    parts = line.strip().split()
    if len(parts) < 5:
        return None
    class_id = int(float(parts[0]))
    x_center, y_center, width, height = map(float, parts[1:5])
    return class_id, x_center, y_center, width, height


def yolo_to_xyxy(x_center, y_center, width, height, img_w, img_h, margin=0.0):
    """正規化されたYOLO座標を画像ピクセル座標(x1, y1, x2, y2)に変換する

    margin: バウンディングボックスの幅・高さに対する余白の割合 (0.1 = 上下左右に10%ずつ拡張)
    """
    box_w = width * img_w * (1.0 + margin)
    box_h = height * img_h * (1.0 + margin)

    cx = x_center * img_w
    cy = y_center * img_h

    x1 = int(round(cx - box_w / 2))
    y1 = int(round(cy - box_h / 2))
    x2 = int(round(cx + box_w / 2))
    y2 = int(round(cy + box_h / 2))

    # 画像範囲内にクリップ
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(img_w, x2)
    y2 = min(img_h, y2)

    return x1, y1, x2, y2


def find_image_path(images_dir: Path, stem: str):
    """拡張子違いを考慮して画像ファイルを探す"""
    for ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
        candidate = images_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def crop_dataset(images_dir: str, labels_dir: str, output_dir: str,
                  margin: float = 0.0, target_classes=None):
    images_dir = Path(images_dir)
    labels_dir = Path(labels_dir)
    output_dir = Path(output_dir)

    if not images_dir.exists():
        print(f"[エラー] 画像フォルダが見つかりません: {images_dir}")
        return
    if not labels_dir.exists():
        print(f"[エラー] ラベルフォルダが見つかりません: {labels_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    label_files = sorted(labels_dir.glob("*.txt"), key=lambda p: (len(p.stem), p.stem))
    if not label_files:
        print(f"[警告] {labels_dir} にラベルファイル(.txt)が見つかりません")
        return

    total_crops = 0
    for label_path in label_files:
        stem = label_path.stem
        image_path = find_image_path(images_dir, stem)
        if image_path is None:
            print(f"[スキップ] 対応する画像が見つかりません: {stem}")
            continue

        img = cv2.imread(str(image_path))
        if img is None:
            print(f"[スキップ] 画像を読み込めません: {image_path}")
            continue

        img_h, img_w = img.shape[:2]

        with open(label_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for idx, line in enumerate(lines):
            parsed = parse_yolo_line(line)
            if parsed is None:
                continue
            class_id, x_center, y_center, width, height = parsed

            if target_classes is not None and class_id not in target_classes:
                continue

            x1, y1, x2, y2 = yolo_to_xyxy(
                x_center, y_center, width, height, img_w, img_h, margin=margin
            )

            if x2 <= x1 or y2 <= y1:
                print(f"[警告] 不正なボックスをスキップ: {stem} line {idx}")
                continue

            crop = img[y1:y2, x1:x2]

            out_name = f"{stem}_{idx:03d}_cls{class_id}.jpg"
            out_path = output_dir / out_name
            cv2.imwrite(str(out_path), crop)
            total_crops += 1

    print(f"完了: 合計 {total_crops} 件のクロップ画像を {output_dir} に保存しました")


def main():
    parser = argparse.ArgumentParser(description="YOLO形式アノテーションに基づく画像クロップ(フラット構成)")
    parser.add_argument("--images_dir", default="images", help="画像フォルダ。デフォルト: images")
    parser.add_argument("--labels_dir", default="labels", help="YOLO形式ラベルフォルダ。デフォルト: labels")
    parser.add_argument("--output_dir", default="output", help="クロップ画像の出力先ディレクトリ。デフォルト: output")
    parser.add_argument("--margin", type=float, default=0.0,
                         help="バウンディングボックスに対する余白の割合(例: 0.1 = 上下左右10%拡張)")
    parser.add_argument("--classes", type=int, nargs="*", default=None,
                         help="クロップ対象のクラスIDを指定(省略時は全クラス)")
    args = parser.parse_args()

    target_classes = set(args.classes) if args.classes else None

    crop_dataset(
        images_dir=args.images_dir,
        labels_dir=args.labels_dir,
        output_dir=args.output_dir,
        margin=args.margin,
        target_classes=target_classes,
    )


if __name__ == "__main__":
    main()