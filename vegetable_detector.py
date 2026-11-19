"""Local YOLO model discovery and image detection helpers."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

PROJECT_DIR = Path(__file__).resolve().parent
MODEL_DIR = PROJECT_DIR / "runs" / "detect"
MAX_IMAGE_PIXELS = 24_000_000


@dataclass(frozen=True)
class ModelFile:
    path: Path
    modified_ns: int
    size: int

    @property
    def label(self) -> str:
        return self.path.relative_to(MODEL_DIR).as_posix()


def discover_models(root: Path = MODEL_DIR) -> list[ModelFile]:
    """Prefer best.pt, then custom weights, then last.pt; newest within each group."""
    models = []
    if not root.is_dir():
        return models
    for path in root.rglob("*"):
        if path.suffix.lower() != ".pt" or not path.is_file():
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(root.resolve()):
            continue
        try:
            stat = path.stat()
        except FileNotFoundError:  # A training process may be replacing a weight file.
            continue
        if stat.st_size:
            models.append(ModelFile(path, stat.st_mtime_ns, stat.st_size))

    def order(model: ModelFile) -> tuple:
        name = model.path.name.lower()
        priority = 0 if name == "best.pt" else 2 if name == "last.pt" else 1
        return priority, -model.modified_ns, str(model.path).lower()

    return sorted(models, key=order)


def read_image(data: bytes) -> Image.Image:
    with Image.open(io.BytesIO(data)) as image:
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ValueError("画像は2,400万画素以下にしてください。縮小して再度お試しください。")
        image.load()
        return ImageOps.exif_transpose(image).convert("RGB")


def detection_rows(result) -> list[dict]:
    """Copy detection tensors to ordinary values for UI and CSV output."""
    if result.boxes is None:
        raise ValueError("物体検出用のYOLOモデル（detect）を選択してください。")
    rows = []
    for box, class_id, score in zip(
        result.boxes.xyxy.cpu().tolist(),
        result.boxes.cls.cpu().tolist(),
        result.boxes.conf.cpu().tolist(),
    ):
        rows.append({
            "クラス": str(result.names[int(class_id)]),
            "信頼度 (%)": round(float(score) * 100, 1),
            "左": round(box[0], 1),
            "上": round(box[1], 1),
            "右": round(box[2], 1),
            "下": round(box[3], 1),
        })
    return sorted(rows, key=lambda row: row["信頼度 (%)"], reverse=True)


def annotate_image(image: Image.Image, rows: list[dict]) -> Image.Image:
    """Draw locally with Pillow, including Japanese labels on Windows."""
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    font_size = max(14, min(48, image.width // 45))
    font = ImageFont.load_default(size=font_size)
    for font_path in ("C:/Windows/Fonts/meiryo.ttc", "C:/Windows/Fonts/YuGothM.ttc"):
        if Path(font_path).is_file():
            font = ImageFont.truetype(font_path, size=font_size)
            break
    palette = ("#16804a", "#2563eb", "#b45309", "#9333ea", "#be185d")
    colors = {name: palette[i % len(palette)] for i, name in enumerate(sorted({r['クラス'] for r in rows}))}
    for row in rows:
        color = colors[row["クラス"]]
        x1, y1, x2, y2 = (row[key] for key in ("左", "上", "右", "下"))
        draw.rectangle((x1, y1, x2, y2), outline=color, width=max(2, image.width // 300))
        label = f"{row['クラス']} {row['信頼度 (%)']:.1f}%"
        left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
        width, height = right - left + 12, bottom - top + 10
        x = max(0, min(x1, image.width - width))
        y = max(0, y1 - height)
        draw.rectangle((x, y, x + width, y + height), fill=color)
        draw.text((x + 6 - left, y + 5 - top), label, font=font, fill="white")
    return annotated


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=["クラス", "信頼度 (%)", "左", "上", "右", "下"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")
