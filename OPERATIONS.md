# Numbers4 API 運用ガイド

## 概要

このリポジトリは **GitHub Pages** を利用した静的 JSON API を提供します。

- **URL**: https://hazimekom.github.io/numbers4-api/
- **データ更新**: ローカルで生成 → main ブランチに push

---

## リポジトリ構成

```
numbers4-api/
├── index.html              # API ホームページ
├── README.md               # ドキュメント
├── OPERATIONS.md           # 運用ガイド（このファイル）
├── api/
│   └── v1/
│       ├── latest.json           # 最新1件
│       ├── numbers4_all_min.json # 軽量版全履歴
│       ├── numbers4_all_full.json# 詳細版全履歴
│       ├── version.json          # バージョン情報
│       └── metadata/
│           └── schema.json       # スキーマ定義
└── .github/
    └── workflows/
        └── deploy-pages.yml      # Pages デプロイ用
```

---

## ⚠️ 重要: リポジトリ分離ルール

| リポジトリ | 可視性 | 用途 |
|-----------|--------|------|
| `numbers4-api` | **Public** | JSON API 配信（GitHub Pages） |
| `numbers4-app` | **Private** | Flutter アプリ本体 |
| `numbers4` | Private | Python 予測モデル・スクレイピング |

### 絶対に守ること

1. **VS Code は2ウィンドウで使う** - API と App を混同しない
2. **Flutter ビルド workflow を API 側に置かない**
3. **API リポジトリには JSON と静的ファイルのみ**
4. **機密情報（API キー等）は API リポジトリに含めない**

---

## データ更新手順

### 1. numbers4 プロジェクトで JSON を生成

```bash
cd ~/Desktop/Python/numbers4

# 最新データをスクレイピング
.venv/bin/python scripts/scrape_numbers4.py --append

# JSON を生成
.venv/bin/python scripts/convert_json.py --output github_pages_api/api/v1 --compact
```

### 2. numbers4-api にコピー＆プッシュ

```bash
cd ~/Desktop/Python/numbers4/github_pages_api

# 変更を確認
git status

# コミット＆プッシュ
git add api/v1/*.json
git commit -m "chore: update data $(date +%Y-%m-%d)"
git push
```

### 3. デプロイ確認

- GitHub Actions の **Deploy to GitHub Pages** が自動実行される
- 数分後に https://hazimekom.github.io/numbers4-api/api/v1/latest.json で確認

---

## トラブルシューティング

### Pages が更新されない

1. GitHub リポジトリの **Settings** → **Pages** を確認
2. **Source** が `GitHub Actions` になっているか確認
3. Actions タブでデプロイ状況を確認

### JSON が不正

```bash
# JSON の構文チェック
python -m json.tool api/v1/latest.json
```

---

## GitHub Pages 設定

1. **Settings** → **Pages**
2. **Source**: `GitHub Actions`（推奨）または `Deploy from a branch`
3. **Branch**: `main` / `/ (root)`

---

## 定期更新（オプション）

自動更新が必要な場合は、`numbers4` プロジェクト側で cron ジョブまたは
GitHub Actions を設定し、生成した JSON を `numbers4-api` に push してください。

例: macOS の launchd / cron で毎日21時に実行

```bash
0 21 * * 1-5 cd ~/Desktop/Python/numbers4 && ./update_api.sh
```

---

## バージョン管理

- **スキーマバージョン**: `version.json` の `schema` フィールド
- **API バージョン**: `/api/v1/` → `/api/v2/` で破壊的変更に対応
- **v1 は互換性維持** - 新機能追加時は v2 を作成
