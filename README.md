# YOLO 野菜判定アプリ

Windows のブラウザー上で、学習済みYOLOモデルを使って写真内の野菜を検出します。
画像のアップロードとカメラ撮影、検出枠・クラス・信頼度・個数の表示、結果画像とCSVの保存に対応しています。

## モデルの配置

このプロジェクトの `runs\detect` に **物体検出用の学習済み `.pt` ファイル**を配置してください。
サブフォルダも検索するため、YOLOの学習出力をそのまま使えます。

```text
runs\detect\vegetables\weights\best.pt
runs\detect\another_model.pt
```

`best.pt`、任意の名前の `.pt`、`last.pt` の順で優先し、それぞれ更新日時の新しい順に表示します。
サイドバーで使用するモデルを選択してください。追加・上書き後は「モデル一覧を再読み込み」を押します。
モデルがない場合は配置案内を表示します。別の汎用モデルを自動取得することはありません。

判定対象の名前はモデル内の学習クラスをそのまま表示します。
例：`daikon` のみを学習したモデルでは、ほかの野菜の種類は判定できません。
分類専用モデル（classify）ではなく、検出モデル（detect）を利用してください。

## 初回セットアップ（Windows / PowerShell・cmux）

Python 3.11 をインストールし、プロジェクトのフォルダで実行します。

```powershell
Set-Location -LiteralPath 'E:\program\AI figure learn\yolo'
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

既存の `venv` で `No Python at ...` が出る場合、作成時のPythonが見つからなくなっています。
Python 3.11をインストールしたうえで、既存環境を別名に退避して作り直してください。
退避先の名前がすでにある場合は、別の名前を使ってください。

```powershell
Rename-Item -LiteralPath '.\venv' -NewName 'venv_backup'
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

`py` が見つからない場合は、インストールしたPython 3.11の `python.exe` のフルパスを
`& 'C:\インストール先\python.exe' -m venv venv` の形で指定してください。

## 起動

```powershell
Set-Location -LiteralPath 'E:\program\AI figure learn\yolo'
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_app.ps1
```

または直接起動できます。仮想環境のActivateは不要です。

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.maxUploadSize 20
```

ブラウザーで `http://127.0.0.1:8501` を開きます。終了はターミナルで `Ctrl+C`。

1. サイドバーでモデル・信頼度の下限・CPUまたは自動実行を選択します。
2. JPEG・PNG・WebPの写真（20MB以下、2,400万画素以下）をアップロードするか撮影します。
3. 「野菜を判定する」を押して検出結果を確認します。
4. 必要に応じて結果画像やCSVを保存します。CSVはWindowsのExcel向けにUTF-8 BOM付きで出力します。

画像・モデル・設定を変更したときは再度判定してください。信頼度は正解の確率を保証する値ではありません。
画像と推論結果はアプリから外部に送信せず、結果を自動でファイル保存しません。
カメラはブラウザーの利用許可が必要です。モデルの追加・差し替えはアプリの再インストールなしで行えます。

## テスト

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```
