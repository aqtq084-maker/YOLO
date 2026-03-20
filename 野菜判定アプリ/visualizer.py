import cv2
import numpy as np

def draw_labeled_boxes(image_np, boxes, confs, cls_ids, class_names):
    """
    バウンディングボックスとクラス名（Daikon, Komatsunaなど）、確信度を描画する。
    文字を大きく、かつ縁取りを行うことで視認性を大幅に向上させています。
    """
    if len(boxes) == 0:
        return image_np

    # OpenCV用にBGR変換
    image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    
    # --- 描画スタイルの設定（ここを調整してサイズを変更できます） ---
    line_thickness = 3      # バウンディングボックスの線の太さ（元は2）
    font_scale = 2.4        # フォントの大きさ（元は0.6。2倍に設定）
    font_thickness = 3      # フォントの太さ（元は1）
    text_padding = 10       # テキスト背景ボックスの余白
    # -----------------------------------------------------------

    # 野菜の名前ごとに「専用の色」を決める（BGR形式）
    # ※モデルのクラス名に合わせて変更してください
    color_map = {
        "komatsuna": (0, 255, 0),   # 小松菜は 緑 (Green)
        "daikon": (255, 100, 0),    # 大根は 水色っぽく (Blueに近い)
        "radish": (0, 0, 255)       # ラディッシュは 赤 (Red)
    }

    # 各ボックスを描画
    for box, conf, cls_id in zip(boxes, confs, cls_ids):
        x1, y1, x2, y2 = map(int, box[:4])
        
        # クラス名を取得し、大文字にする（見やすくするため）
        label_name = class_names.get(cls_id, "unknown").upper()
        
        # 色マップから取得。無ければグレー
        box_color = color_map.get(label_name.lower(), (128, 128, 128))
        
        # 1. バウンディングボックス（四角い枠）を描く
        cv2.rectangle(image_bgr, (x1, y1), (x2, y2), box_color, line_thickness)
        
        # 🌟 ラベルテキストの作成：「KOMATSUNA (85%)」形式に
        label_text = f"{label_name} ({conf*100:.0f}%)"
        
        # 2. テキストのサイズを取得して背景ボックスの大きさを決める
        (text_width, text_height), baseline = cv2.getTextSize(
            label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness
        )
        
        # テキストが画像の上にはみ出さないように調整
        text_bg_y1 = y1 - text_height - baseline - (text_padding * 2)
        text_bg_y2 = y1
        if text_bg_y1 < 0: # 画像上部ギリギリの場合、ボックスの中に表示
            text_bg_y1 = y1
            text_bg_y2 = y1 + text_height + baseline + (text_padding * 2)

        # 🌟 テキスト背景ボックスを描画（ボックスと同じ色にする。ただし文字は縁取りするので見える）
        cv2.rectangle(
            image_bgr, 
            (x1, text_bg_y1), 
            (x1 + text_width + text_padding, text_bg_y2), 
            box_color, 
            -1 # 塗りつぶし
        )
        
        # テキストの描画位置
        text_x = x1 + (text_padding // 2)
        text_y = text_bg_y1 + text_height + text_padding
        
        # 🌟 プロの手法：文字をはっきり見せるための「アウトライン（縁取り）」描画
        # まず、黒色で太めに文字を描く
        cv2.putText(
            image_bgr, 
            label_text, 
            (text_x, text_y), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            font_scale, 
            (0, 0, 0), # 黒色
            font_thickness + 4, # 元の太さ+4で縁取りにする
            cv2.LINE_AA # アンチエイリアスで綺麗に
        )
        
        # その上に、本来の白文字を描画する
        cv2.putText(
            image_bgr, 
            label_text, 
            (text_x, text_y), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            font_scale, 
            (255, 255, 255), # 白色
            font_thickness, 
            cv2.LINE_AA
        )

    # RGBに戻して返す
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)