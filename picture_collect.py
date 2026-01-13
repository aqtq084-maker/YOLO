import os
import shutil
from icrawler.builtin import BingImageCrawler

def collect_images():
    # ---------------------------------------------------------
    # 1. 保存先のフォルダ設定
    # ---------------------------------------------------------
    # ここにダウンロードされます
    save_dir = 'downloaded_images'

    # もしフォルダがなければ作る
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        print(f"フォルダ作成完了: {save_dir}")
    else:
        print(f"フォルダ確認: {save_dir} (既存のフォルダを使用します)")

    # ---------------------------------------------------------
    # 2. 検索キーワードの設定（呪文）
    # ---------------------------------------------------------
    # 意図: 「1枚だけ」「接写」「花はダメ」「群生はダメ」
    # single: 単体
    # macro / close up: 接写（背景ボケを狙う）
    # -flower -bloom: 花を除外
    # -field -grass -lawn: 野原や芝生全体（引きの画）を除外
    # -illustration -vector: イラストを除外
    keyword_text = 'single clover leaf macro close up -flower -bloom -field -grass -lawn -many -pattern -illustration -vector'

    print(f"検索キーワード: {keyword_text}")
    print("収集を開始します...（これには数秒〜数分かかります）")

    # ---------------------------------------------------------
    # 3. クローラー（収集ロボット）の起動
    # ---------------------------------------------------------
    crawler = BingImageCrawler(
        storage={'root_dir': save_dir},
        # エラーが出ても無視して次に進む設定
        downloader_threads=4, 
    )

    # ---------------------------------------------------------
    # 4. ダウンロード実行
    # ---------------------------------------------------------
    crawler.crawl(
        keyword=keyword_text,
        max_num=30,  # 集める枚数（必要に応じて変更してください）
        filters=dict(
            type='photo',  # 写真のみ
            # size='large' # 画質優先ならこのコメント(#)を外してください（枚数は減る可能性があります）
        )
    )

    print("--------------------------------------------------")
    print("収集が完了しました！")
    print(f"保存先フォルダ: {os.path.abspath(save_dir)}")
    print("必ず中身を目視確認して、不要な画像（複数枚写っているもの等）は削除してください。")
    print("--------------------------------------------------")

if __name__ == "__main__":
    collect_images()