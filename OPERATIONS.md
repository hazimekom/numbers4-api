# Numbers4 API 運用ガイド

## 概要

このリポジトリは **Firebase Hosting** を利用した静的 JSON API を提供します。

- **URL**: https://numbers4-1d961.web.app/
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
        └── firebase-deploy.yml   # Firebase Hosting デプロイ用
```

GitHub Actions 実行時のみ `deploy/` を生成し、Firebase Hosting の公開対象は
`firebase.json` の `public: "deploy"` に限定する。repo root を直接公開しない。

---

## ⚠️ 重要: リポジトリ分離ルール

| リポジトリ | 可視性 | 用途 |
|-----------|--------|------|
| `numbers4-api` | **Public** | JSON API 配信（Firebase Hosting） |
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

- GitHub Actions の **Deploy to Firebase Hosting** が自動実行される
- 数分後に https://numbers4-1d961.web.app/api/v1/latest.json で確認

---

## Firebase Hosting Deploy Hardening

### GitHub Actions 運用手順

通常運用では、`main` への push または schedule により
`.github/workflows/firebase-deploy.yml` が実行される。

手動確認が必要な場合は、GitHub Actions の `workflow_dispatch` から
**Deploy to Firebase Hosting** を実行する。

確認するログ:

- `Node version`
- `npm version`
- `firebase-tools version`
- `Deploy hash`
- `Deploy file count`
- `Remote deploy hash`
- `Local deploy hash`
- `Deploy skip reason`

### 固定Version

GitHub Actions は以下を固定する。

| 項目 | Version | 理由 |
|------|---------|------|
| Node.js | `22.23.1` | Node `22.23.0` / `24.17.0` の keep-alive regression による `Premature close` を避けるため |
| firebase-tools | `15.22.1` | `latest` 追従による突発的な Firebase CLI 挙動変更を避けるため |

### Known Issue

2026-06-25〜26 に、`firebase-tools` / Node.js の HTTP keep-alive 周辺で
Google API 通信が `Premature close` になる事象が確認された。

Hosting Release API は非冪等であり、1回目のReleaseがFirebase側で成功した後に
クライアント側が通信断としてretryすると、同じVersionへの2回目のReleaseが
以下で失敗する。

```text
supplied version ... is the current active version
```

その場合でも、公開済み `deploy-manifest.json` の `deploy_hash` がローカル生成hashと
一致すれば、公開自体は完了済みとみなし、workflowは成功扱いにする。

参考:

- `firebase-tools` Issue: `firebase/firebase-tools#10716`
- `firebase-tools` Issue: `firebase/firebase-tools#10726`
- Node.js Issue: `nodejs/node#63989`

### Deploy Skip 条件

Actions は deploy 前に `deploy/` を生成し、`deploy-manifest.json` に
成果物hashを保存する。

```text
https://numbers4-1d961.web.app/deploy-manifest.json
```

公開済みhashと今回生成hashが一致する場合は、Firebase Hosting releaseを作らず
successで終了する。

### Deploy対象

Hosting公開対象は `deploy/` のみ。

含めるもの:

- `index.html`
- `api/`
- `data/`
- `deploy-manifest.json`

含めないもの:

- `.git/`
- `.github/`
- `README.md`
- `OPERATIONS.md`
- secrets / service account keys

### 将来方針

`FirebaseExtended/action-hosting-deploy` で扱いきれない retry / idempotency 制御が
再発する場合は、Firebase Hosting REST API を直接呼ぶ deploy wrapper へ移行する。
その場合は、Release API の `current active version` を明示的に成功扱いできる。

認証方式は現状 `FIREBASE_SERVICE_ACCOUNT_NUMBERS4_1D961` の Service Account JSON を
利用する。将来は Workload Identity Federation へ移行し、長期鍵を使わない構成にする。
ただし WIF 移行時は `firebase-tools` の ADC / WIF 関連Issueを再確認してから行う。

---

## トラブルシューティング

### Firebase Hosting が更新されない

1. Actions タブで **Deploy to Firebase Hosting** の実行状況を確認
2. `deploy-manifest.json` の `deploy_hash` を確認
3. `Deploy skip reason` が `live_hash_matches` の場合は更新不要
4. `current active version` が出ても、live hashが一致していれば公開済み

### JSON が不正

```bash
# JSON の構文チェック
python -m json.tool api/v1/latest.json
```

---

## Firebase Hosting 設定

- Project: `numbers4-1d961`
- Site: `numbers4-1d961`
- Workflow: `.github/workflows/firebase-deploy.yml`
- Secret: `FIREBASE_SERVICE_ACCOUNT_NUMBERS4_1D961`

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
