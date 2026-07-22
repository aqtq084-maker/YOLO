import numpy as np
from pathlib import Path
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

files = sorted(Path("features").glob("*_cls.npy"))

features = []

for f in files:
    x = np.load(f)
    features.append(x.squeeze())

features = np.array(features)

print("特徴量:", features.shape)

pca = PCA(n_components=2)
result = pca.fit_transform(features)

plt.figure(figsize=(8, 6))
plt.scatter(result[:, 0], result[:, 1])

for i, f in enumerate(files):
    plt.text(result[i, 0], result[i, 1], f.stem)

plt.savefig("pca_result.png", dpi=300)
print("保存しました: pca_result.png")

