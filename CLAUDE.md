# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of standalone Python scripts (not a package — no `src/`, no `__init__.py`, no build system) built around **Ultralytics YOLOv8** for training and running object detectors on agricultural subjects: clover (クローバー), daikon (大根), komatsuna (小松菜), and a multi-class "veggies" model. Each script is self-contained and typically hardcodes its own input/output paths at the top of the file rather than sharing config.

## Environment setup

- Python 3.11 venv lives in `venv/` (created via `python -m venv`, gitignored). Activate with `venv\Scripts\activate` (PowerShell/cmd) before running anything.
- Dependencies are in `requirements.txt`, but **that file is UTF-16LE-encoded** (not UTF-8) — it was saved incorrectly at some point. If you edit it with a tool that assumes UTF-8, you'll corrupt it further; re-save as UTF-16LE or convert the whole file to UTF-8 first (`pip` itself tolerates the BOM fine).
- There is no linter, formatter, or test suite configured anywhere in the repo. There's nothing to run for "build/lint/test" — verification is done by visually inspecting drawn bounding boxes or Ultralytics' own training/val output (`results.png`, `confusion_matrix.png`, etc.) under `runs/` or a custom `project=` folder.

## Running scripts

Every script is run directly, e.g.:
```
python train_clover.py
python Annotation.py
streamlit run streamlet_test.py   # note: filename is "streamlet", not a typo to fix silently
```
Before running any script, **open it first and check the hardcoded paths** — they are absolute, machine-specific, and inconsistent across the repo (some point at `E:\program\AI figure learn\yolo\...`, others at a stale `C:\Users\lenob\.vscode\program\AI figure learn\yolo\...`, and `HL_learn_From_Web.py` even hardcodes a Linux path from a different contributor's machine). Don't assume a script's paths are valid without checking.

## Pipeline architecture

Scripts fall into five stages of one recurring workflow (collect → label → verify → train → infer). Understanding this pipeline is more useful than reading any single file in isolation:

1. **Collect images** — `picture_collect.py` uses `icrawler` (BingImageCrawler) to bulk-download candidate images by keyword into `downloaded_images/`. Output must be manually reviewed before use (crawled sets contain noise).

2. **Normalize filenames** — `name_change.py` (images) and `label_change.py` (label `.txt` files) rename files in a folder to `<prefix>_<NNN>.<ext>`, driven by a `prefix`/`start_num` you edit per run. Used to merge batches of new data into an existing numbered sequence without collisions.

3. **Auto-label (draft annotation)** — `Annotation.py`, `Annotation_HL.py`, `Annotation_HL_ChangeBrain.py` run an existing YOLO model (`model.predict`) over a folder of unlabeled images and write YOLO-format `.txt` labels, but only for detections whose center falls inside one or more manually-specified ROI rectangles (`rois = [[x1,y1,x2,y2], ...]`). The three scripts differ only in which model/paths they point at (a fresh `yolov8n.pt` vs. a previously trained `best.pt`) — this is a draft/pre-label step, always meant to be hand-corrected afterward, not a final labeling method.

4. **Verify labels** — `Annotation_Check.py` draws YOLO-format boxes from a `labels/` folder onto their matching images and saves them to `check_result/` for batch review. `show_baundybox.py` does the same but interactively via `cv2.imshow`, one image at a time (any key = next, Esc = quit) — use this for spot-checking a handful of images rather than a whole folder.

5. **Train** — `train_clover.py`, `CAVT_clover_cloud.py`, `HL_learn_From_Web.py`, `allData.py`, `Verification.py` (top half) all call `YOLO(...).train(data=..., epochs=..., imgsz=640, device='cpu', ...)`, differing in: which `data.yaml` they point at, whether they start from a stock checkpoint (`yolov8n.pt`/`yolov8s.pt`) or continue from a prior run's `best.pt` (fine-tuning), and the `name=`/`project=` used to namespace output. Default Ultralytics output goes to `runs/detect/<name>/`; scripts that pass `project=` (e.g. `CAVT_clover_cloud.py` → `Clover_CAVT_test/`) write elsewhere instead. Training run names are versioned by hand in the `name=` string (`clover_retry_v2`, `v22`, `v3`, `v32`, `daikon_retry_v4`, ...) — check `runs/detect/` / the relevant project folder for the latest existing version before picking the next one.

6. **Infer** — `Verification.py` (bottom half) loads a trained `best.pt`/`last.pt` and runs `model.predict(source=..., save=True, conf=...)` against a single image. `streamlet_test.py` and `streamlit_test_Nginx.py` wrap inference in a Streamlit UI (camera or file upload); the former also gates access by client IP prefix (Wi-Fi allowlist) — that check is tied to a specific network and will silently block all access if reused elsewhere.

## Data layout

- Root `data.yaml` and `clover1/data.yaml` are Ultralytics dataset configs (`path`/`train`/`val`/`nc`/`names`) — each points at one dataset's own directory tree (`images/train`, `images/val`, `labels/train`, `labels/val`).
- Multiple parallel dataset directories exist for different subjects/label-format origins: `dataset/`, `dataset_2/` (both have an `HLimages`/`HLlabels` pairing alongside the standard YOLO layout), `dataset_daikon/` (also has `no-anotation`/`yes-anotation` staging folders for the auto-label step above), `clover1/` (CVAT export format, includes `labels.cache`), `Labellmg_clover/` (flat labelImg output, image+txt side by side), `clover_images/`+`clover_labels/` (older flat clover set), `txt_CAVT/` (raw CVAT-for-YOLO export: `obj.data`, `obj.names`, `obj_train_data/`).
- `.gitignore` currently excludes `dataset/`, `clover_images/`, `clover_labels/`, `dataset_2/`, `*.pt`, and a few output folders — but `dataset/`, `dataset_2/`, `clover_images/`, and `clover_labels/` were committed to git *before* those ignore rules were added, so they are still tracked despite being listed. Adding new files under those paths won't be ignored; only genuinely new untracked paths respect `.gitignore`. If the intent is to stop tracking them, that needs an explicit `git rm --cached -r <dir>`, not just the ignore entry.

## 禁止事項 (Claude が勝手にやってはいけないこと)

- **データ・学習成果物の削除・上書き禁止** — `dataset*/`, `clover_images/`, `clover_labels/`, `clover1/`, `Labellmg_clover/`, `txt_CAVT/` などのデータセットや、`runs/`, `Clover_CAVT_test/` などの学習結果フォルダ、`*.pt` の重みファイルを削除・上書き・移動しない。手作業でラベル付けした画像やラベル、時間をかけて学習したモデルが失われると再現できない。整理・リネームが必要な場合も、実行前に対象と方法をユーザーに確認してから行う。
- **Git操作の制限** — `git push`、force push、`git reset --hard`、履歴の書き換え、コミット済みファイルの `git rm` は、ユーザーに明示的に指示されない限り行わない。特に上記の「トラッキングされているのにgitignoreに載っている」データフォルダを勝手に `git rm --cached` しない — 対応が必要でも、必ず先にユーザーに確認する。
- **パス・ハードコード値の無断変更禁止** — 各スクリプト冒頭の絶対パス（`model_path`, `input_dir`, `output_dir`, `rois`, `data=` など）や `name=`/`project=` の値は、そのスクリプトを動かす人が意図的に設定したものなので、指示されていない限り書き換えない。バグ修正や整理の一環でも、パスを変更する場合は変更内容と理由をユーザーに伝えてから行う。
- 上記に反する変更が本当に必要だと判断した場合は、実行せず先にユーザーに相談すること。
- **作業範囲はこの `yolo` フォルダ内に限定する** — このリポジトリ (`E:\program\AI figure learn\yolo`) の外にあるファイル・フォルダは読み書きしない。`.claude/settings.local.json` に `Read`/`Write`/`Edit`/`Bash`/`PowerShell` に対する拒否ルールを設定して技術的にも制限しているが、Bash/PowerShellは任意のシェルコマンドを実行できるため、パターンに一致しない迂回（環境変数経由のパス指定など）までは防げない。技術的な制限に頼らず、フォルダ外への操作が必要になった場合は必ず先にユーザーに確認すること。
