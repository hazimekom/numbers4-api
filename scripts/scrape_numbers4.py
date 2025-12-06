"""
ナンバーズ4 スクレイピングスクリプト

楽天宝くじサイトからナンバーズ4の当選番号と配当金情報を取得します。

取得項目:
- 回号、抽せん日、当せん番号、各桁(digit1-4)
- ストレート当選金、ボックス当選金
- セットストレート当選金、セットボックス当選金

使用方法:
  # 全データ取得
  python scripts/scrape_numbers4.py

  # 増分更新
  python scripts/scrape_numbers4.py --append

  # 配当金情報のみ補完
  python scripts/scrape_numbers4.py --fill-payouts
"""

import re
import time
import argparse
import os
from typing import Optional, Dict, List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE_URL = "https://takarakuji.rakuten.co.jp/backnumber/numbers4/"
PAST_URL = "https://takarakuji.rakuten.co.jp/backnumber/numbers4_past/"
DETAIL_BASE = "https://takarakuji.rakuten.co.jp/backnumber/numbers4_detail/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
}

# 月次ページの対象月を生成（2024年9月～現在月+2ヶ月先まで）
def generate_months() -> List[str]:
    """対象となる月のリストを生成"""
    months = []
    start_year, start_month = 2024, 9
    now = datetime.now()
    end_year, end_month = now.year, now.month + 2  # 2ヶ月先まで
    
    if end_month > 12:
        end_month -= 12
        end_year += 1
    
    current_year, current_month = start_year, start_month
    while (current_year, current_month) <= (end_year, end_month):
        months.append(f"{current_year}{current_month:02d}")
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    
    return months


MONTHS = generate_months()


def parse_payout_amount(text: str) -> Optional[int]:
    """配当金テキストから金額を抽出（円単位）
    
    例: "940,800円" → 940800
        "該当なし" → None
    """
    if not text or "該当なし" in text:
        return None
    # カンマと円を除去して数値を抽出
    cleaned = re.sub(r"[,円\s]", "", text)
    match = re.search(r"(\d+)", cleaned)
    if match:
        return int(match.group(1))
    return None


def scrape_month_with_payouts(url: str, session: requests.Session) -> List[Dict]:
    """月次ページから当選番号と配当金情報を取得
    
    Args:
        url: 月次ページのURL (例: https://takarakuji.rakuten.co.jp/backnumber/numbers4/202512/)
        session: requestsセッション
    
    Returns:
        当選結果のリスト。各結果は以下のキーを含む辞書:
        - 回号, 抽せん日, 当せん番号, digit1-4
        - straight_payout, box_payout, set_straight_payout, set_box_payout
    """
    try:
        res = session.get(url, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            return []
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "lxml")
    except Exception:
        return []

    results = []
    
    # 各回号ごとのテーブルを取得
    tables = soup.select("table.tblType02.tblNumberGuid")
    
    for table in tables:
        result = {
            "回号": None,
            "抽せん日": None,
            "当せん番号": None,
            "digit1": None,
            "digit2": None,
            "digit3": None,
            "digit4": None,
            "straight_payout": None,
            "box_payout": None,
            "set_straight_payout": None,
            "set_box_payout": None,
        }
        
        rows = table.select("tr")
        for row in rows:
            th = row.find("th")
            if not th:
                continue
            
            label = th.get_text(strip=True)
            tds = row.find_all("td")
            
            if label == "回号":
                # "第6868回" のような形式
                ths = row.find_all("th")
                if len(ths) > 1:
                    result["回号"] = ths[1].get_text(strip=True)
            
            elif label == "抽せん日" and tds:
                result["抽せん日"] = tds[0].get_text(strip=True)
            
            elif label == "当せん番号" and tds:
                numbers = tds[0].get_text(strip=True).strip()
                num_only = re.sub(r"\D", "", numbers)
                if len(num_only) == 4:
                    result["当せん番号"] = num_only
                    result["digit1"] = int(num_only[0])
                    result["digit2"] = int(num_only[1])
                    result["digit3"] = int(num_only[2])
                    result["digit4"] = int(num_only[3])
            
            elif label == "ストレート" and len(tds) >= 2:
                result["straight_payout"] = parse_payout_amount(tds[1].get_text(strip=True))
            
            elif label == "ボックス" and len(tds) >= 2:
                result["box_payout"] = parse_payout_amount(tds[1].get_text(strip=True))
            
            elif label == "セット（ストレート）" and len(tds) >= 2:
                result["set_straight_payout"] = parse_payout_amount(tds[1].get_text(strip=True))
            
            elif label == "セット（ボックス）" and len(tds) >= 2:
                result["set_box_payout"] = parse_payout_amount(tds[1].get_text(strip=True))
        
        # 有効なデータのみ追加
        if result["回号"] and result["当せん番号"]:
            results.append(result)
    
    return results


def scrape_month(url):
    """後方互換性のための関数（配当金なし版）"""
    session = requests.Session()
    results = scrape_month_with_payouts(url, session)
    # 配当金カラムを除去して返す
    for r in results:
        for key in ["straight_payout", "box_payout", "set_straight_payout", "set_box_payout"]:
            r.pop(key, None)
    return results


def get_max_round_from_past_page(session: requests.Session) -> Optional[int]:
    """numbers4_past ページから最大の回号(末尾)を推定して返す。
    例: href=".../numbers4_detail/6541-6546/" → 6546 を抽出
    取得に失敗したら None を返す。
    """
    try:
        r = session.get(PAST_URL, headers=HEADERS, timeout=20)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "lxml")
        links = [a.get("href", "") for a in soup.select("a[href]")]
        max_end = 0
        pat = re.compile(r"/numbers4_detail/(\d{4})-(\d{4})/?$")
        for href in links:
            m = pat.search(href)
            if m:
                end = int(m.group(2))
                if end > max_end:
                    max_end = end
        return max_end or None
    except Exception:
        return None


def get_max_round_from_current_month(session: requests.Session) -> Optional[int]:
    """現在月のページから最新の回号を取得する"""
    try:
        # 最新の月（202509, 202510など）を逆順でチェック
        for month in reversed(MONTHS):
            url = BASE_URL + month + "/"
            r = session.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue
                
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "lxml")
            
            rows = soup.select("table.tblType02.tblNumberGuid tr")
            max_round = 0
            
            round_no = None
            for row in rows:
                th = row.find("th")
                if not th:
                    continue
                    
                label = th.get_text(strip=True)
                if label == "回号":
                    round_text = row.find_all("th")[1].get_text(strip=True) if len(row.find_all("th")) > 1 else None
                    if round_text:
                        round_num = to_round_int(round_text)
                        if round_num > max_round:
                            max_round = round_num
            
            if max_round > 0:
                return max_round
        
        return None
    except Exception:
        return None


def build_detail_urls(start_round: int, end_round: int) -> list[str]:
    """0001-0020, 0021-0040 ... のような範囲URLを生成"""
    urls = []
    s = max(1, start_round)
    e = max(s, end_round)
    for st in range(s, e + 1, 20):
        en = min(st + 19, e)
        urls.append(f"{DETAIL_BASE}{st:04d}-{en:04d}/")
    return urls


def scrape_detail_page(url: str, session: requests.Session) -> list[dict]:
    """詳細ページ(範囲ページ)を1ページ分スクレイプして結果のリストを返す。
    対象のテーブルは table.tblType02.tblNumbers4
    列: 回号 / 抽せん日 / ナンバーズ4
    """
    res = session.get(url, headers=HEADERS, timeout=20)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "lxml")

    results: list[dict] = []
    table = soup.select_one("table.tblType02.tblNumbers4")
    if not table:
        return results

    for tr in table.select("tr"):
        tds = tr.find_all("td")
        if len(tds) != 3:
            continue  # ヘッダ行などをスキップ
        round_label = tds[0].get_text(strip=True)
        date = tds[1].get_text(strip=True)
        numbers = tds[2].get_text(strip=True)

        # 数字4桁だけを抽出(スペースや全角対策)
        num_only = re.sub(r"\D", "", numbers)
        if len(num_only) != 4:
            continue

        result = {
            "回号": round_label,
            "抽せん日": date,
            "当せん番号": num_only,
            "digit1": int(num_only[0]),
            "digit2": int(num_only[1]),
            "digit3": int(num_only[2]),
            "digit4": int(num_only[3]),
        }
        results.append(result)

    return results


def to_round_int(label: str) -> int:
    # 例: "第0001回" → 1
    m = re.search(r"(\d+)", label)
    return int(m.group(1)) if m else -1


def get_month_from_date(date_str: str) -> Optional[str]:
    """日付文字列から月を抽出 (YYYY/MM/DD → YYYYMM)"""
    try:
        match = re.match(r"(\d{4})/(\d{2})/\d{2}", date_str)
        if match:
            return f"{match.group(1)}{match.group(2)}"
    except Exception:
        pass
    return None


def collect_payouts_from_months(
    session: requests.Session,
    target_rounds: Optional[set] = None,
    months: Optional[List[str]] = None
) -> Dict[int, Dict]:
    """月次ページから配当金情報を収集
    
    Args:
        session: requestsセッション
        target_rounds: 取得対象の回号セット（Noneの場合は全て取得）
        months: 対象月のリスト（Noneの場合はMONTHSを使用）
    
    Returns:
        回号をキーとした配当金情報の辞書
    """
    if months is None:
        months = MONTHS
    
    payouts = {}
    
    for month in months:
        url = BASE_URL + month + "/"
        try:
            results = scrape_month_with_payouts(url, session)
            for r in results:
                round_num = to_round_int(r.get("回号", ""))
                if round_num > 0:
                    if target_rounds is None or round_num in target_rounds:
                        payouts[round_num] = {
                            "straight_payout": r.get("straight_payout"),
                            "box_payout": r.get("box_payout"),
                            "set_straight_payout": r.get("set_straight_payout"),
                            "set_box_payout": r.get("set_box_payout"),
                        }
            time.sleep(0.3)  # サーバー負荷軽減
        except Exception as e:
            print(f"⚠️ 月次データ取得失敗: {url} : {e}")
    
    return payouts


def fill_missing_payouts(df: pd.DataFrame, session: requests.Session) -> pd.DataFrame:
    """配当金情報が欠損している行を補完
    
    Args:
        df: 元のDataFrame
        session: requestsセッション
    
    Returns:
        補完後のDataFrame
    """
    # 配当金カラムが存在しない場合は追加
    payout_cols = ["straight_payout", "box_payout", "set_straight_payout", "set_box_payout"]
    for col in payout_cols:
        if col not in df.columns:
            df[col] = None
    
    # 配当金が欠損している回号を特定
    df["__round_int__"] = df["回号"].astype(str).apply(to_round_int)
    
    missing_mask = df[payout_cols].isna().all(axis=1)
    missing_rounds = set(df.loc[missing_mask, "__round_int__"].tolist())
    
    if not missing_rounds:
        print("配当金情報の欠損はありません。")
        df.drop(columns=["__round_int__"], inplace=True)
        return df
    
    print(f"配当金が欠損している回号: {len(missing_rounds)}件")
    
    # 欠損している回号の日付から、必要な月を特定
    months_needed = set()
    for idx, row in df[missing_mask].iterrows():
        month = get_month_from_date(str(row.get("抽せん日", "")))
        if month:
            months_needed.add(month)
    
    # 必要な月からデータを取得
    print(f"取得対象月: {sorted(months_needed)}")
    payouts = collect_payouts_from_months(session, missing_rounds, sorted(months_needed))
    
    # 欠損を補完
    filled_count = 0
    for idx, row in df.iterrows():
        round_num = row["__round_int__"]
        if round_num in payouts:
            payout_data = payouts[round_num]
            for col in payout_cols:
                if pd.isna(df.at[idx, col]) and payout_data.get(col) is not None:
                    df.at[idx, col] = payout_data[col]
                    filled_count += 1
    
    print(f"補完完了: {filled_count}件の配当金データを追加")
    
    df.drop(columns=["__round_int__"], inplace=True)
    return df


# CSV列の定義（新仕様: 10列）
CSV_COLUMNS = [
    "回号", "抽せん日", "当せん番号", 
    "digit1", "digit2", "digit3", "digit4",
    "straight_payout", "box_payout", "set_straight_payout", "set_box_payout"
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Numbers4 back numbers from Rakuten Lottery site")
    parser.add_argument("--start", type=int, default=1, help="Start round number (inclusive), default=1")
    parser.add_argument("--end", type=int, default=0, help="End round number (inclusive); when 0, auto-detect from past page")
    parser.add_argument("--append", action="store_true", help="Append only new results to existing numbers4_results.csv if present")
    parser.add_argument("--fill-payouts", action="store_true", help="Fill missing payout data in existing CSV")
    parser.add_argument("--with-payouts", action="store_true", help="Include payout data when scraping (slower)")
    args = parser.parse_args()

    session = requests.Session()

    # 配当金補完モード
    if args.fill_payouts:
        if not os.path.exists("numbers4_results.csv"):
            print("エラー: numbers4_results.csv が見つかりません")
            exit(1)
        
        print("配当金情報の補完を開始...")
        df = pd.read_csv("numbers4_results.csv", encoding="utf-8-sig")
        df = fill_missing_payouts(df, session)
        
        # 出力カラムを正規化
        for col in CSV_COLUMNS:
            if col not in df.columns:
                df[col] = None
        
        df[CSV_COLUMNS].to_csv("numbers4_results.csv", index=False, encoding="utf-8-sig")
        print("✅ 配当金情報の補完完了 → numbers4_results.csv")
        exit(0)

    # 1) 最新の回号(末尾)を自動検出。複数の方法を試す。
    end_from_past = get_max_round_from_past_page(session)
    end_from_current = get_max_round_from_current_month(session)
    
    # より大きな値を使用（現在月の方が通常最新）
    end_auto = max(filter(None, [end_from_past, end_from_current]), default=6546)
    
    print(f"過去ページから検出: 第{end_from_past or 0:04d}回")
    print(f"現在月から検出: 第{end_from_current or 0:04d}回") 
    print(f"使用する最新回号: 第{end_auto:04d}回")
    
    start_round = max(1, args.start)
    end_round = args.end if args.end and args.end >= start_round else end_auto
    
    # 追記モード: 既存CSVがあれば最後の回号を検出し、その次から取得する
    existing_df = None
    if args.append and os.path.exists("numbers4_results.csv"):
        try:
            existing_df = pd.read_csv("numbers4_results.csv", encoding="utf-8-sig")
            if not existing_df.empty and "回号" in existing_df.columns:
                existing_df["__round_int__"] = existing_df["回号"].astype(str).apply(to_round_int)
                max_saved = int(existing_df["__round_int__"].max())
                if max_saved >= end_round:
                    print(f"既に第{max_saved:04d}回まで取得済みです。追加取得は不要です。")
                    exit(0)
                start_round = max(start_round, max_saved + 1)
                print(f"追記モード: 既存CSVは第{max_saved:04d}回まで。新規取得は第{start_round:04d}回～第{end_round:04d}回になります。")
        except Exception as e:
            print(f"既存CSV読み込み失敗: {e} — フル取得を続行します。")

    detail_urls = build_detail_urls(start_round, end_round)

    print(f"取得範囲: 第{start_round:04d}回～第{end_round:04d}回 (全{len(detail_urls)}ページ)")

    all_results: List[Dict] = []

    # 2) 範囲ページを順にクロール（当選番号のみ取得）
    for i, url in enumerate(detail_urls, 1):
        print(f"[{i}/{len(detail_urls)}] スクレイピング中: {url}")
        try:
            page_results = scrape_detail_page(url, session)
            all_results.extend(page_results)
        except Exception as e:
            print(f"⚠️ 失敗: {url} : {e}")
        time.sleep(0.3)  # サーバー負荷軽減のためのウェイト

    # 3) 月次ページから配当金情報を取得
    print("\n配当金情報を取得中...")
    
    # 対象回号を特定
    target_rounds = set()
    for r in all_results:
        round_num = to_round_int(r.get("回号", ""))
        if start_round <= round_num <= end_round:
            target_rounds.add(round_num)
    
    # 月次ページから配当金を収集（with-payoutsオプションまたは追記モードで新規データのみ）
    if args.with_payouts or args.append:
        payouts = collect_payouts_from_months(session, target_rounds)
        
        # 配当金情報をマージ
        for r in all_results:
            round_num = to_round_int(r.get("回号", ""))
            if round_num in payouts:
                r.update(payouts[round_num])
        
        print(f"配当金情報を取得: {len(payouts)}件")
    else:
        print("配当金情報はスキップ（--with-payouts で取得可能）")

    # 4) 重複除去と並び替え
    for r in all_results:
        if 'round_int' not in r:
            r["round_int"] = to_round_int(r.get("回号", ""))

    df_new = pd.DataFrame(all_results)
    
    # 重複除去（同じ回号の場合は後の方を残す）
    if not df_new.empty:
        df_new.drop_duplicates(subset=["round_int"], keep="last", inplace=True)
    
    # 新規データが空の場合、既存CSVをそのまま出力
    if df_new.empty:
        print("新規データはありません。既存CSVは変更されませんでした。")
        exit(0)
    
    # 5) 結合処理: 追記モードか否かで挙動を変える
    if args.append and existing_df is not None:
        # 既存データのカラムを正規化
        for col in CSV_COLUMNS:
            if col not in existing_df.columns:
                existing_df[col] = None
        
        existing_norm = existing_df[CSV_COLUMNS].copy()
        existing_norm["round_int"] = existing_df["回号"].astype(str).apply(to_round_int)

        # 新規データのカラムも正規化
        for col in CSV_COLUMNS:
            if col not in df_new.columns:
                df_new[col] = None

        combined = pd.concat([existing_norm, df_new], ignore_index=True)
        combined.sort_values(["round_int", "抽せん日"], inplace=True)
        combined.drop_duplicates(subset=["round_int"], keep="last", inplace=True)
        out_df = combined[CSV_COLUMNS]
    else:
        # 新規データのカラムを正規化
        for col in CSV_COLUMNS:
            if col not in df_new.columns:
                df_new[col] = None
        
        df_new.sort_values(["round_int", "抽せん日"], inplace=True)
        df_new.drop_duplicates(subset=["round_int"], keep="last", inplace=True)
        out_df = df_new[CSV_COLUMNS]

    out_df.to_csv("numbers4_results.csv", index=False, encoding="utf-8-sig")
    print(f"\n✅ 保存完了 → numbers4_results.csv ({len(out_df)}件)")
    
    # 配当金の統計を表示
    payout_cols = ["straight_payout", "box_payout", "set_straight_payout", "set_box_payout"]
    filled = out_df[payout_cols].notna().all(axis=1).sum()
    total = len(out_df)
    print(f"📊 配当金情報: {filled}/{total}件 ({filled/total*100:.1f}%)")

