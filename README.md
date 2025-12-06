# Numbers4 API

📊 **ナンバーズ4 当選番号データ API**

GitHub Pages を利用した静的 JSON データ配信サービスです。

## 🚀 エンドポイント

| エンドポイント | 説明 |
|---------------|------|
| [`/api/v1/latest.json`](https://hazimekom.github.io/numbers4-api/api/v1/latest.json) | 最新1件のみ（軽量） |
| [`/api/v1/numbers4_all_min.json`](https://hazimekom.github.io/numbers4-api/api/v1/numbers4_all_min.json) | 全履歴（番号のみ・軽量版） |
| [`/api/v1/numbers4_all_full.json`](https://hazimekom.github.io/numbers4-api/api/v1/numbers4_all_full.json) | 全履歴（配当金含む・詳細版） |
| [`/api/v1/version.json`](https://hazimekom.github.io/numbers4-api/api/v1/version.json) | バージョン情報（更新判定用） |

## 📋 データ形式

### latest.json

```json
{
  "draw_no": 6870,
  "date": "2025-12-05",
  "digits": [1, 2, 3, 4],
  "winning_number": "1234",
  "prize": {
    "straight": 980000,
    "box": 41000,
    "set_straight": 510000,
    "set_box": 20000
  }
}
```

### numbers4_all_min.json（軽量版）

```json
[
  {
    "draw_no": 1,
    "date": "1994-10-07",
    "digits": [1, 1, 4, 9]
  },
  ...
]
```

### numbers4_all_full.json（詳細版）

```json
[
  {
    "draw_no": 6870,
    "date": "2025-12-05",
    "digits": [1, 2, 3, 4],
    "winning_number": "1234",
    "prize": {
      "straight": 980000,
      "box": 41000,
      "set_straight": 510000,
      "set_box": 20000
    }
  },
  ...
]
```

### version.json

```json
{
  "version": "2025-12-05-870",
  "schema": "1.0.0",
  "last_update": "2025-12-05T21:10:00+09:00",
  "latest_draw_no": 6870,
  "latest_date": "2025-12-05",
  "total_records": 6870
}
```

## 🔄 更新スケジュール

- **自動更新**: 毎日 21:00 (JST) - 抽選結果発表後
- **手動更新**: GitHub Actions の `workflow_dispatch` から随時実行可能

## 💻 使用例

### JavaScript / TypeScript

```javascript
const API_BASE = 'https://hazimekom.github.io/numbers4-api/api/v1';

// 最新データを取得
const response = await fetch(`${API_BASE}/latest.json`);
const latest = await response.json();
console.log(`第${latest.draw_no}回: ${latest.digits.join('')}`);

// バージョンチェック
const versionRes = await fetch(`${API_BASE}/version.json`);
const version = await versionRes.json();
if (version.latest_draw_no > localDrawNo) {
  // 新しいデータがある
}
```

### Flutter / Dart

```dart
final url = Uri.parse(
  'https://hazimekom.github.io/numbers4-api/api/v1/latest.json',
);
final response = await http.get(url);
final data = jsonDecode(response.body);
print('第${data['draw_no']}回: ${data['digits'].join('')}');
```

### Python

```python
import requests

API_BASE = 'https://hazimekom.github.io/numbers4-api/api/v1'
response = requests.get(f'{API_BASE}/latest.json')
data = response.json()
print(f"第{data['draw_no']}回: {''.join(map(str, data['digits']))}")
```

## 🔒 CORS

GitHub Pages は CORS 許可済みのため、ブラウザやスマホアプリから制限なく取得可能です。

## ⚠️ 注意事項

- GitHub Pages は高負荷には適していません。大量リクエストが予想される場合は Firebase Hosting 等への移行を検討してください。
- 全履歴データは約 1MB 程度です。モバイル環境ではキャッシュの活用を推奨します。

## 📜 ライセンス

MIT License

---

**[🏠 ホームページを見る](https://hazimekom.github.io/numbers4-api/)**
