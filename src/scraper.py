import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

SHOP_URL = "https://gogo.gs/shop/4099000297"
HISTORY_URL = "https://gogo.gs/shop/price/4099000297"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
PRICE_MIN = 80
PRICE_MAX = 300

# 「134円」「134.5 円」などから価格だけを抽出（円直前の数字に限定）
PRICE_CIRCLE_RE = re.compile(r"(\d{2,3}(?:\.\d+)?)\s*円")
DATE_RE = re.compile(r"(\d{4})[/\-年](\d{1,2})[/\-月](\d{1,2})")
TIME_RE = re.compile(r"(\d{1,2})\s*時")


def _extract_price(text):
    """テキストから円直前の数値を抽出。範囲チェック済みのfloatを返す。"""
    match = PRICE_CIRCLE_RE.search(text)
    if not match:
        # フォールバック: 円が無い場合の生数値（数字のみのセル向け）
        fallback = re.search(r"(\d{2,3}(?:\.\d+)?)", text)
        if not fallback:
            return None
        try:
            price = float(fallback.group(1))
        except ValueError:
            return None
    else:
        try:
            price = float(match.group(1))
        except ValueError:
            return None
    if PRICE_MIN <= price <= PRICE_MAX:
        return price
    print(f"異常値を除外: {price}")
    return None


def _extract_date(text):
    """テキストから日付をYYYY-MM-DD形式で抽出。失敗時None。"""
    m = DATE_RE.search(text)
    if not m:
        return None
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def _extract_time(text):
    """テキストから『7時』のような時刻を抽出。失敗時None。"""
    m = TIME_RE.search(text)
    if not m:
        return None
    return f"{int(m.group(1))}時"


def scrape_current_price():
    """店舗ページから今日の会員レギュラー価格を取得する。
    Returns: (price, posted_time_str) または (None, None)
    最新日付の行を優先する。
    """
    try:
        resp = requests.get(SHOP_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 会員価格セクションを特定
        member_h5 = None
        for h5 in soup.find_all("h5"):
            if "会員" in h5.get_text():
                member_h5 = h5
                break

        if member_h5 is None:
            print("会員価格セクションが見つかりません")
            return None, None

        table = member_h5.find_next("table")
        if table is None:
            print("会員価格テーブルが見つかりません")
            return None, None

        # 全行を (date, time, price) に正規化し、最新日付を選択
        candidates = []
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            date_cell = cells[0].get_text(" ", strip=True)
            price_cell = cells[1].get_text(" ", strip=True)
            date_str = _extract_date(date_cell)
            price = _extract_price(price_cell)
            posted_time = _extract_time(date_cell)
            if date_str and price is not None:
                candidates.append((date_str, posted_time, price))

        if not candidates:
            print("価格が見つかりません")
            return None, None

        candidates.sort(key=lambda x: x[0], reverse=True)
        latest_date, posted_time, latest_price = candidates[0]
        print(f"最新会員価格: {latest_price}円 (日付: {latest_date}, 投稿: {posted_time})")
        return latest_price, posted_time
    except Exception as e:
        print(f"スクレイピングエラー: {e}")
        return None, None


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

            category = cells[-1].get_text(strip=True) if cells else ""
            if "会員" not in category:
                continue

            date_str = _extract_date(cells[0].get_text(strip=True))
            if not date_str:
                continue

            price = _extract_price(cells[1].get_text(strip=True))
            if price is None:
                continue

            results.append((date_str, price))

        seen = {}
        for date_str, price in results:
            seen[date_str] = price
        return sorted(seen.items(), key=lambda x: x[0])

    except Exception as e:
        print(f"履歴スクレイピングエラー: {e}")
        return []
