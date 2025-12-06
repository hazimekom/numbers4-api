#!/usr/bin/env python3
"""
Numbers4 CSV → JSON 変換スクリプト

GitHub Pages API用のJSONファイルを生成します。

生成ファイル:
- api/v1/latest.json: 最新1件の当選情報
- api/v1/numbers4_all_min.json: 軽量版全履歴（番号のみ）
- api/v1/numbers4_all_full.json: 詳細版全履歴（配当金含む）
- api/v1/version.json: バージョン情報

使用方法:
  python scripts/convert_json.py
  python scripts/convert_json.py --input path/to/csv --output api/v1/
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def load_csv(csv_path: str) -> pd.DataFrame:
    """CSVファイルを読み込む"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
    
    df = pd.read_csv(csv_path, encoding="utf-8")
    
    # 回号から数値を抽出
    df["draw_no"] = df["回号"].str.extract(r"(\d+)").astype(int)
    
    # 日付を正規化
    df["date"] = pd.to_datetime(df["抽せん日"]).dt.strftime("%Y-%m-%d")
    
    # 当選番号を4桁にパディング
    df["winning_number"] = df["当せん番号"].astype(str).str.zfill(4)
    
    # 各桁を整数に変換
    for i in range(1, 5):
        df[f"digit{i}"] = df[f"digit{i}"].astype(int)
    
    return df


def convert_payout(value: Any) -> int | None:
    """配当金をintまたはNoneに変換"""
    if pd.isna(value):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def generate_latest_json(df: pd.DataFrame) -> dict:
    """latest.json用データを生成"""
    latest = df.sort_values("draw_no", ascending=False).iloc[0]
    
    return {
        "draw_no": int(latest["draw_no"]),
        "date": latest["date"],
        "digits": [
            int(latest["digit1"]),
            int(latest["digit2"]),
            int(latest["digit3"]),
            int(latest["digit4"]),
        ],
        "winning_number": latest["winning_number"],
        "prize": {
            "straight": convert_payout(latest.get("straight_payout")),
            "box": convert_payout(latest.get("box_payout")),
            "set_straight": convert_payout(latest.get("set_straight_payout")),
            "set_box": convert_payout(latest.get("set_box_payout")),
        },
    }


def generate_all_min_json(df: pd.DataFrame) -> list[dict]:
    """numbers4_all_min.json用データを生成（軽量版）"""
    records = []
    for _, row in df.sort_values("draw_no").iterrows():
        records.append({
            "draw_no": int(row["draw_no"]),
            "date": row["date"],
            "digits": [
                int(row["digit1"]),
                int(row["digit2"]),
                int(row["digit3"]),
                int(row["digit4"]),
            ],
        })
    return records


def generate_all_full_json(df: pd.DataFrame) -> list[dict]:
    """numbers4_all_full.json用データを生成（詳細版）"""
    records = []
    for _, row in df.sort_values("draw_no").iterrows():
        records.append({
            "draw_no": int(row["draw_no"]),
            "date": row["date"],
            "digits": [
                int(row["digit1"]),
                int(row["digit2"]),
                int(row["digit3"]),
                int(row["digit4"]),
            ],
            "winning_number": row["winning_number"],
            "prize": {
                "straight": convert_payout(row.get("straight_payout")),
                "box": convert_payout(row.get("box_payout")),
                "set_straight": convert_payout(row.get("set_straight_payout")),
                "set_box": convert_payout(row.get("set_box_payout")),
            },
        })
    return records


def generate_version_json(df: pd.DataFrame) -> dict:
    """version.json用データを生成"""
    latest = df.sort_values("draw_no", ascending=False).iloc[0]
    latest_date = latest["date"]
    latest_draw_no = int(latest["draw_no"])
    
    # バージョン形式: YYYY-MM-DD-NNN
    version = f"{latest_date}-{latest_draw_no:03d}"
    
    return {
        "version": version,
        "schema": "1.0.0",
        "last_update": datetime.now().astimezone().isoformat(),
        "latest_draw_no": latest_draw_no,
        "latest_date": latest_date,
        "total_records": len(df),
    }


def save_json(data: Any, filepath: Path, compact: bool = False) -> None:
    """JSONファイルを保存"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        if compact:
            # 軽量版は改行なしでサイズ削減
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ファイルサイズを表示
    size_kb = filepath.stat().st_size / 1024
    print(f"  生成: {filepath} ({size_kb:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(description="Numbers4 CSV → JSON 変換")
    parser.add_argument(
        "--input", "-i",
        default="numbers4_results.csv",
        help="入力CSVファイルパス (default: numbers4_results.csv)"
    )
    parser.add_argument(
        "--output", "-o",
        default="api/v1",
        help="出力ディレクトリ (default: api/v1)"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="軽量JSONを生成（改行なし）"
    )
    args = parser.parse_args()
    
    # 入力ファイルパスを解決
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    if os.path.isabs(args.input):
        csv_path = args.input
    else:
        csv_path = project_root / args.input
    
    # 出力ディレクトリを解決
    if os.path.isabs(args.output):
        output_dir = Path(args.output)
    else:
        output_dir = project_root / args.output
    
    print(f"=== Numbers4 JSON 変換 ===")
    print(f"入力: {csv_path}")
    print(f"出力: {output_dir}")
    print()
    
    try:
        # CSVを読み込み
        print("CSVファイルを読み込み中...")
        df = load_csv(str(csv_path))
        print(f"  読み込み完了: {len(df)} 件")
        print()
        
        # JSONファイルを生成
        print("JSONファイルを生成中...")
        
        # latest.json
        latest_data = generate_latest_json(df)
        save_json(latest_data, output_dir / "latest.json")
        
        # numbers4_all_min.json（軽量版）
        all_min_data = generate_all_min_json(df)
        save_json(all_min_data, output_dir / "numbers4_all_min.json", compact=args.compact)
        
        # numbers4_all_full.json（詳細版）
        all_full_data = generate_all_full_json(df)
        save_json(all_full_data, output_dir / "numbers4_all_full.json", compact=args.compact)
        
        # version.json
        version_data = generate_version_json(df)
        save_json(version_data, output_dir / "version.json")
        
        print()
        print("✅ 変換完了!")
        print(f"  最新回号: 第{version_data['latest_draw_no']}回 ({version_data['latest_date']})")
        
    except FileNotFoundError as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
