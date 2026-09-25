from pathlib import Path
import numpy as np

from files.data_loader import FeatureDataset
from files.feature_processor import build_feature_vector
from files.linear_probe_evaluator import (
    LinearProbeConfig,
    build_linear_probe_evaluator,
)

# データ読み込み
dataset = FeatureDataset("features_photo_homu")

print(f"クラス数: {len(dataset.labels)}")
print(f"サンプル数: {len(dataset.samples)}")
print("クラスごとのサンプル数:")
print(dataset.summary())

# CLS特徴量を使用
X_list = []
y_list = []

for sample in dataset.samples:
    try:
        vec = build_feature_vector(sample, "cls")
        X_list.append(vec)
        y_list.append(sample.label)
    except KeyError as e:
        print(f"スキップ: {e}")

X = np.stack(X_list)
y = y_list

print(f"特徴量 shape: {X.shape}")

# Linear Probe
config = LinearProbeConfig(
    C=1.0,
    max_iter=2000,
    standardize=True,
    class_weight="balanced",
    cv_method="kfold",
    n_splits=5,
)

evaluator = build_linear_probe_evaluator(config)

result = evaluator.evaluate(X, y)

print("\n========== Linear Probe 評価結果 ==========")
print(f"Accuracy: {result.accuracy:.4f}")
print()
print(result.report_text)

# 結果保存
out_dir = Path("eval_results")
out_dir.mkdir(exist_ok=True)

with open(out_dir / "linear_probe_report.txt", "w", encoding="utf-8") as f:
    f.write("DINOv2 Linear Probe Evaluation\n")
    f.write(f"Accuracy: {result.accuracy:.4f}\n\n")
    f.write(result.report_text)

print("\n結果を保存しました:")
print("eval_results/linear_probe_report.txt")
