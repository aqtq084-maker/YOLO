import cv2
import numpy as np

def draw_semantic_mask(image_np, boxes, hsv_thresholds, color=(0, 255, 0), alpha=0.5):
    """
    検出されたボックス内で「メインの緑色の塊」だけを抽出して色付けする
    （隣接する別の植物を除外するための処理入り）
    """
    if len(boxes) == 0:
        return image_np

    # BGRに変換（OpenCV用）
    image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    h, w = image_bgr.shape[:2]
    
    # 最終的な描画用マスク（最初は真っ黒）
    final_mask = np.zeros((h, w), dtype=np.uint8)
    
    # 画像全体をHSVに変換
    hsv_image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

    # 閾値設定
    lower_green = np.array([hsv_thresholds['h_min'], hsv_thresholds['s_min'], hsv_thresholds['v_min']])
    upper_green = np.array([hsv_thresholds['h_max'], hsv_thresholds['s_max'], hsv_thresholds['v_max']])

    # --- 各ボックスごとの処理 ---
    for box in boxes:
        x1, y1, x2, y2 = map(int, box[:4])
        
        # ボックスが画像外にはみ出さないようにクリップ
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        # ボックスの幅と高さ
        box_w = x2 - x1
        box_h = y2 - y1
        if box_w <= 0 or box_h <= 0:
            continue

        # 1. そのボックス内の画像だけを切り抜く（ROI）
        roi_hsv = hsv_image[y1:y2, x1:x2]
        
        # 2. その中から「緑色」だけを抽出（マスク作成）
        # ここではまだ大根も小松菜も全部白くなっています
        roi_mask = cv2.inRange(roi_hsv, lower_green, upper_green)

        # 🌟 3. ノイズ除去（ごま塩ノイズを消す）
        # 小さなゴミを消して、葉っぱの塊をくっつける処理
        kernel = np.ones((3,3), np.uint8)
        roi_mask = cv2.morphologyEx(roi_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # 🌟 4. 「塊（コンポーネント）」に分解する
        # num_labels: 塊の数
        # labels: どのピクセルがどの塊か
        # stats: 各塊の大きさや場所 [x, y, width, height, area]
        # centroids: 各塊の中心座標
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(roi_mask, connectivity=8)

        # 塊がなければ次へ
        if num_labels <= 1: # 0は背景なので、1以下なら物体なし
            continue

        # 5. 「メインの塊」を決める
        # 条件：一番面積が大きく、かつボックスの中心に近いものを選ぶ
        box_center_x = box_w / 2
        box_center_y = box_h / 2
        
        best_label = -1
        max_score = -1

        # ラベル0は背景（黒）なので、1からスタート
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            cx, cy = centroids[i]
            
            # ボックス中心からの距離
            dist = np.sqrt((cx - box_center_x)**2 + (cy - box_center_y)**2)
            
            # スコア計算（面積が大きく、中心に近いほど高スコア）
            # 面積を重視しつつ、距離でペナルティを与える簡易式
            # ※極端に端っこにある塊を除外するため
            score = area / (dist + 1.0) 

            if score > max_score:
                max_score = score
                best_label = i
        
        # 6. 選ばれた「メインの塊」だけを最終マスクに書き込む
        if best_label != -1:
            # ROI内でのマスク（選ばれたラベルの場所だけ255にする）
            selected_blob_mask = np.where(labels == best_label, 255, 0).astype(np.uint8)
            
            # 元画像の座標に戻して書き込む
            # bitwise_orを使うことで、重なりがあっても大丈夫
            current_roi_mask = final_mask[y1:y2, x1:x2]
            final_mask[y1:y2, x1:x2] = cv2.bitwise_or(current_roi_mask, selected_blob_mask)

    # --- 描画処理 ---
    overlay = image_bgr.copy()
    
    # 最終マスクが白い場所だけ色を塗る
    overlay[final_mask > 0] = color
    
    # 合成
    output_bgr = cv2.addWeighted(overlay, alpha, image_bgr, 1 - alpha, 0)
    
    # RGBに戻す
    return cv2.cvtColor(output_bgr, cv2.COLOR_BGR2RGB)