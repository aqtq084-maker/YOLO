"""UI checks use a fake model so no trained weights or downloads are required."""

import io
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
import streamlit as st
from streamlit.testing.v1 import AppTest

from vegetable_detector import MODEL_DIR, ModelFile, png_bytes
from test_vegetable_detector import FakeBoxes, FakeTensor


class Upload(io.BytesIO):
    @property
    def size(self):
        return len(self.getvalue())


class FakeModel:
    task = "detect"
    names = {0: "大根", 1: "にんじん"}

    def __init__(self, empty=False, fail=False):
        self.fail = fail
        self.calls = 0
        self.boxes = FakeBoxes()
        if empty:
            self.boxes = type("Boxes", (), {name: FakeTensor([]) for name in ["xyxy", "cls", "conf"]})()

    def predict(self, **kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError("Test prediction error")
        return [type("Result", (), {"boxes": self.boxes, "names": self.names})()]


class AppTests(unittest.TestCase):
    def setUp(self):
        st.cache_resource.clear()
        self.app_path = str(Path(__file__).resolve().parents[1] / "app.py")

    def app(self):
        return AppTest.from_file(self.app_path, default_timeout=30)

    def test_missing_model_shows_instructions(self):
        with patch("vegetable_detector.discover_models", return_value=[]):
            app = self.app().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("モデルを配置" in item.value for item in app.info))

    def test_predict_download_rerun_and_setting_invalidation(self):
        model = FakeModel()
        upload = Upload(png_bytes(Image.new("RGB", (200, 150), "white")))
        weights = ModelFile(MODEL_DIR / "vegetables" / "weights" / "best.pt", 1, 12)
        with patch("vegetable_detector.discover_models", return_value=[weights]), \
             patch("ultralytics.YOLO", return_value=model), \
             patch("streamlit.file_uploader", return_value=upload):
            app = self.app().run()
            self.assertEqual(len(app.exception), 0)
            app.button[0].click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual([item.value for item in app.metric], ["2 個", "2 種類"])
            self.assertEqual(len(app.get("download_button")), 2)
            app.run()
            self.assertEqual(model.calls, 1)
            self.assertEqual(len(app.metric), 2)
            app.slider[0].set_value(60).run()
            self.assertEqual(len(app.metric), 0)
            self.assertEqual(len(app.get("download_button")), 0)

    def test_no_detection_and_prediction_failure(self):
        model = FakeModel(empty=True)
        upload = Upload(png_bytes(Image.new("RGB", (200, 150))))
        weights = ModelFile(MODEL_DIR / "best.pt", 1, 12)
        with patch("vegetable_detector.discover_models", return_value=[weights]), \
             patch("ultralytics.YOLO", return_value=model), \
             patch("streamlit.file_uploader", return_value=upload):
            app = self.app().run()
            app.button[0].click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.metric[0].value, "0 個")
            self.assertTrue(any("検出できません" in item.value for item in app.warning))
            model.fail = True
            app.button[0].click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any("判定に失敗" in item.value for item in app.error))
            self.assertEqual(len(app.metric), 0)


if __name__ == "__main__":
    unittest.main()
