## Branch Rules（ブランチ運用ルール）

### 基本方針
- `main` は常に動く状態を保つ（直接 push 禁止）
- 作業は必ずブランチを切って Pull Request（PR）でマージする
- ブランチ名は「目的が一目でわかる」ことを最優先にする

### ブランチ命名規則（推奨）
以下の形式で作成する：

- 機能追加：`feature/<short-description>`
- バグ修正：`fix/<short-description>`
- 緊急修正：`hotfix/<short-description>`
- ドキュメント：`docs/<short-description>`
- 雑務（設定・依存関係・リファクタ等）：`chore/<short-description>`

例：
- `feature/login-page`
- `fix/null-pointer-on-startup`
- `docs/update-install-guide`
- `chore/update-dependencies`

命名ルール：
- 英小文字 + ハイフン区切り（snake_caseは使わない）
- できるだけ短く、何をするかが伝わる名前にする

### ブランチ作成〜PRまでの流れ
1) 最新の `main` を取得
```bash
git switch main
git pull origin main
