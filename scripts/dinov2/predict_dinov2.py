import torch
import torchvision.transforms as T
from PIL import Image
import joblib
from transformers import AutoModel

# ===== 1. 設定 =====
MODEL_PATH = "dinov2_synecoculture_model.pkl" 

# ★判定させたい画像のパスをここに入力してください！
# （例："dataset_dinov2/train/komatsuna/〇〇.jpg" など、今回学習に使ったものでもOKです）
TEST_IMAGE_PATH = "L:\\kyosei-nouhou\\YOLO\\dataset\\HLimages\\38.jpg" 

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ===== 2. AIの脳みそ（pklファイル）を開く（読み込む） =====
print("冷凍保存されたAIの脳みそを解凍中...")
saved_data = joblib.load(MODEL_PATH)
classifier = saved_data['model']
classes = saved_data['classes']

# ===== 3. DINOv2（眼）の準備 =====
print("DINOv2（眼）を準備中...")
dinov2 = AutoModel.from_pretrained('facebook/dinov2-small')
dinov2.to(device)
dinov2.eval()

# ===== 4. 画像の前処理 =====
transform = T.Compose([
    T.Resize(256, interpolation=T.InterpolationMode.BICUBIC),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
])

# ===== 5. 画像を読み込んで特徴を抽出 =====
print(f"画像 '{TEST_IMAGE_PATH}' を判定します...")
try:
    image = Image.open(TEST_IMAGE_PATH).convert('RGB')
    image_tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = dinov2(pixel_values=image_tensor)
        features = outputs.last_hidden_state[:, 0, :]

    # ===== 6. AIによる最終判定！ =====
    prediction = classifier.predict(features.cpu().numpy())[0]
    predicted_class = classes[prediction]

    print("\n==================================")
    print(f"🎯 判定結果: この植物は 【 {predicted_class} 】 です！")
    print("==================================\n")

except FileNotFoundError:
    print(f"エラー: 画像 '{TEST_IMAGE_PATH}' が見つかりません。パスが合っているか確認してください！")