import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

SHOP_URL = "https://gogo.gs/shop/4099000297"
HISTORY_URL = "https://gogo.gs/shop/price/4099000297"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
PRICE_MIN = 100
PRICE_MAX = 250


def scrape_current_price():
    """店舗ページから今日の会員レギュラー価格を取得する。失敗時はNoneを返す。"""
    try:
        resp = requests.get(SHOP_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 会員価格セクションの次のテーブルを探す
        member_h5 = None
        for h5 in soup.find_all("h5"):
            if "会員" in h5.get_text():
                member_h5 = h5
                break

        if member_h5 is None:
            print("会員価格セクションが見つかりません")
            return None

        # h5の後にあるテーブルを取得
        table = member_h5.find_next("table")
        if table is None:
            print("会員価格テーブルが見つかりません")
            return None

        # レギュラー価格を探す
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            label = cells[0].get_text(strip=True)
            if "レギュラー" in label:
                price_text = cells[1].get_text(strip=True)
                match = re.search(r"(\d+(?:\.\d+)?)", price_text)
                if match:
                    price = float(match.group(1))
                    if PRICE_MIN <= price <= PRICE_MAX:
                        return price
                    print(f"異常値を検出: {price}円")
                    return None

        print("レギュラー価格が見つかりません")
        return None
    except Exception as e:
        print(f"スクレイピングエラー: {e}")
        return None


def scrape_price_history():
    """価格履歴ページから会員レギュラー価格の履歴を取得する。
    Returns: list of (date_str, price) tuples, e.g. [("2026-02-01", 133.0), ...]
    """
    try:
        resp = requests.get(HISTORY_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        table = soup.find("table")
        if table is None:
            print("価格履歴テーブルが見つかりません")
            return results

        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            # 価格区分が「会員」かチェック
            category = cells[-1].get_text(strip=True) if cells else ""
            if "会員" not in category:
                continue

            # 日付を取得
            date_text = cells[0].get_text(strip=True)
            date_match = re.search(r"(\d{4})[/\-年](\d{1,2})[/\-月](\d{1,2})", date_text)
            if not date_match:
                continue
            date_str = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"

            # レギュラー価格を取得
            price_text = cells[1].get_text(strip=True)
            price_match = re.search(r"(\d+(?:\.\d+)?)", price_text)
            if not price_match:
                continue

            price = float(price_match.group(1))
            if PRICE_MIN <= price <= PRICE_MAX:
                results.append((date_str, price))

        # 日付で重複排除（最新を優先）
        seen = {}
        for date_str, price in results:
            seen[date_str] = price
        return sorted(seen.items(), key=lambda x: x[0])

    except Exception as e:
        print(f"履歴スクレイピングエラー: {e}")
        return []
