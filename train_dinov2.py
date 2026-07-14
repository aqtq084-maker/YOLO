import torch
import torchvision.transforms as T
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score
import joblib
from transformers import AutoModel # ★ここが新しくなりました！

# ===== 1. 設定 =====
DATASET_DIR = "dataset_dinov2/train" 
MODEL_SAVE_PATH = "dinov2_synecoculture_model.pkl"  # 協生農法（Synecoculture）の汎用モデルという名前に変更！
# GPUが使えるPCなら自動でGPUを使用、なければCPUを使用
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用デバイス: {device}")

# ===== 2. DINOv2モデルの読み込み (Transformers版に変更) =====
print("DINOv2モデルをダウンロード・読み込み中...")
# Metaの公式GitHubではなく、安定したHugging Faceからモデルを取得します
dinov2 = AutoModel.from_pretrained('facebook/dinov2-small')
dinov2.to(device)
dinov2.eval() 

# ===== 3. 画像の前処理 =====
transform = T.Compose([
    T.Resize(256, interpolation=T.InterpolationMode.BICUBIC),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
])

# ===== 4. データの読み込み =====
dataset = ImageFolder(DATASET_DIR, transform=transform)
dataloader = DataLoader(dataset, batch_size=16, shuffle=True)
print(f"学習するクラス（種類）: {dataset.classes}")

# ===== 5. 画像をDINOv2に入力し、特徴（ベクトル）を抽出 =====
def extract_features(loader):
    features_list = []
    labels_list = []
    with torch.no_grad(): 
        for images, labels in loader:
            images = images.to(device)
            
            # DINOv2に画像を入力して特徴を取り出す
            outputs = dinov2(pixel_values=images)
            # 画像全体の情報が詰まった「CLSトークン」という部分だけを抽出
            features = outputs.last_hidden_state[:, 0, :]
            
            features_list.append(features.cpu())
            labels_list.append(labels)
            
    return torch.cat(features_list), torch.cat(labels_list)

print(f"画像から特徴を抽出中... (合計: {len(dataset)}枚。少し時間がかかります)")
X_train, y_train = extract_features(dataloader)

# ===== 6. 抽出した特徴を使って、分類器（SVM）を学習 =====
print("分類器（AIの脳みそ）を学習中...")
classifier = LinearSVC(C=1.0, max_iter=10000)
classifier.fit(X_train.numpy(), y_train.numpy())

# 精度テスト
preds = classifier.predict(X_train.numpy())
acc = accuracy_score(y_train.numpy(), preds)
print(f"✅ 学習完了！ 訓練データの正解率: {acc * 100:.2f}%")

# ===== 7. 完成したモデルを保存 =====
joblib.dump({'model': classifier, 'classes': dataset.classes}, MODEL_SAVE_PATH)
print(f"AIモデルを '{MODEL_SAVE_PATH}' に保存しました！")