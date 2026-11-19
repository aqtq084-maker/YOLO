import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, UnidentifiedImageError

from vegetable_detector import (
    annotate_image, csv_bytes, detection_rows, discover_models, png_bytes, read_image,
)


class ModelDiscoveryTests(unittest.TestCase):
    def test_missing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(discover_models(Path(directory) / "missing"), [])

    def test_nested_weights_priority_and_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / "old" / "weights" / "best.pt",
                     root / "new" / "weights" / "best.pt",
                     root / "vegetable.PT", root / "last.pt"]
            for i, path in enumerate(paths):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test weights")
                os.utime(path, (100 + i, 100 + i))
            (root / "empty.pt").touch()
            (root / "notes.txt").write_text("not a model", encoding="utf-8")
            self.assertEqual([m.path for m in discover_models(root)],
                             [paths[1], paths[0], paths[2], paths[3]])
            previous = discover_models(root)[0]
            paths[1].write_bytes(b"replacement weights")
            current = discover_models(root)[0]
            self.assertNotEqual((previous.modified_ns, previous.size),
                                (current.modified_ns, current.size))


class ImageTests(unittest.TestCase):
    def test_exif_rotation_and_rgb_conversion(self):
        image = Image.new("RGB", (20, 10), "green")
        exif = Image.Exif()
        exif[274] = 6
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", exif=exif)
        result = read_image(buffer.getvalue())
        self.assertEqual(result.size, (10, 20))
        self.assertEqual(result.mode, "RGB")
        rgba = Image.new("RGBA", (10, 10))
        self.assertEqual(read_image(png_bytes(rgba)).mode, "RGB")

    def test_invalid_and_oversized_image(self):
        with self.assertRaises(UnidentifiedImageError):
            read_image(b"invalid image")
        with patch("vegetable_detector.MAX_IMAGE_PIXELS", 50):
            with self.assertRaises(ValueError):
                read_image(png_bytes(Image.new("RGB", (10, 10))))

    def test_drawing_preserves_original_and_csv_supports_japanese(self):
        rows = [{"クラス": "大根", "信頼度 (%)": 98.5,
                 "左": 10, "上": 40, "右": 100, "下": 100}]
        image = Image.new("RGB", (200, 150), "white")
        annotated = annotate_image(image, rows)
        self.assertEqual(image.getpixel((10, 40)), (255, 255, 255))
        self.assertNotEqual(annotated.getpixel((10, 40)), (255, 255, 255))
        self.assertEqual(read_image(png_bytes(annotated)).size, image.size)
        csv = csv_bytes(rows)
        self.assertTrue(csv.startswith(b"\xef\xbb\xbf"))
        self.assertIn("大根", csv.decode("utf-8-sig"))
        self.assertEqual(len(csv_bytes([]).decode("utf-8-sig").splitlines()), 1)


class FakeTensor:
    def __init__(self, data):
        self.data = data

    def cpu(self):
        return self

    def tolist(self):
        return self.data


class FakeBoxes:
    xyxy = FakeTensor([[1, 2, 3, 4], [5, 6, 7, 8]])
    cls = FakeTensor([0, 1])
    conf = FakeTensor([0.6, 0.95])


class ResultTests(unittest.TestCase):
    def test_class_mapping_confidence_and_sort(self):
        result = type("Result", (), {"boxes": FakeBoxes(), "names": {0: "大根", 1: "にんじん"}})()
        rows = detection_rows(result)
        self.assertEqual([row["クラス"] for row in rows], ["にんじん", "大根"])
        self.assertEqual(rows[0]["信頼度 (%)"], 95.0)
        self.assertEqual(rows[0]["左"], 5)

    def test_empty_detection_and_wrong_task(self):
        boxes = type("Boxes", (), {name: FakeTensor([]) for name in ["xyxy", "cls", "conf"]})()
        result = type("Result", (), {"boxes": boxes, "names": {0: "大根"}})()
        self.assertEqual(detection_rows(result), [])
        result.boxes = None
        with self.assertRaises(ValueError):
            detection_rows(result)


if __name__ == "__main__":
    unittest.main()
