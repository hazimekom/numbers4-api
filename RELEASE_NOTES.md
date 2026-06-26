# Release Notes

## 2026-06-26: Firebase Hosting Deploy Hardening

Numbers4 API の Firebase Hosting deploy を安定化した。

### Changed

- GitHub Actions の Firebase deploy で `firebase-tools` を `15.22.1` に固定。
- GitHub Actions の Node.js を `22.23.1` に固定。
- Firebase Hosting の公開対象を repo root から `deploy/` 生成物へ変更。
- `deploy-manifest.json` を追加し、deploy hash と file count を公開。
- 公開済み deploy hash が一致する場合は Firebase Hosting deploy を skip。
- `firebase-tools` の Release API retry で `supplied version ... is the current active version` が発生しても、公開済みhashが一致すれば成功扱いにする運用へ変更。
- GitHub Actions ログへ Node / npm / firebase-tools / deploy hash / remote hash / skip reason を出力。

### Operational Notes

- `deploy/` は GitHub Actions 実行時に生成する一時成果物で、Git管理しない。
- `firebase.json` の `public` は `deploy`。
- `.git/` と `.github/` は Firebase Hosting の公開対象外。
- 将来は Service Account JSON から Workload Identity Federation への移行を検討する。

### Known Issue

2026-06-25〜26 に、Node.js / `firebase-tools` の HTTP keep-alive 周辺で
Google API通信が `Premature close` となり、Firebase Hosting Release API が
同じVersionへ再送される事象を確認した。

その結果、Firebase側では公開済みであるにもかかわらず、GitHub Actions が
以下のエラーで failure になることがある。

```text
supplied version ... is the current active version
```

本対応では、固定Version化、deploy hash skip、live hash 照合によりこの failure パターンを回避する。
