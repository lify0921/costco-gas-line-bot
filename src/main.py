import csv
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from scraper import scrape_current_price, scrape_price_history
from graph import generate_graph, GRAPH_PATH
from imgur import upload_image
from line_bot import send_price_message

CSV_PATH = "data/prices.csv"
TZ = ZoneInfo("Asia/Tokyo")


def load_csv():
    """CSVから価格データを読み込む。Returns: dict {date_str: price}"""
    data = {}
    if not os.path.exists(CSV_PATH):
        return data
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("date") and row.get("price"):
                try:
                    data[row["date"]] = float(row["price"])
                except ValueError:
                    pass
    return data


def save_csv(data):
    """価格データをCSVに保存する。"""
    sorted_items = sorted(data.items())
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "price"])
        for date_str, price in sorted_items:
            writer.writerow([date_str, price])
    print(f"CSV保存完了: {len(sorted_items)}件")


def main():
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    print(f"実行日: {today}")

    # 1. CSV読み込み
    data = load_csv()
    print(f"既存データ: {len(data)}件")

    # 2. CSVが空ならバックフィル
    if len(data) == 0:
        print("バックフィル開始...")
        history = scrape_price_history()
        for date_str, price in history:
            data[date_str] = price
        print(f"バックフィル完了: {len(history)}件取得")

    # 3. 今日の価格取得
    note = None
    current_price = scrape_current_price()
    if current_price is not None:
        data[today] = current_price
        print(f"今日の価格: {current_price}円")
    else:
        print("今日の価格取得失敗、前回価格を使用")
        note = "※価格取得失敗のため前回価格を表示"
        if today not in data and data:
            # 最新の価格を使用
            latest_date = max(data.keys())
            current_price = data[latest_date]
            data[today] = current_price
        elif today in data:
            current_price = data[today]
        else:
            print("価格データが存在しません。終了します。")
            sys.exit(1)

    # 4. CSV保存
    save_csv(data)

    # 5. グラフ生成
    sorted_items = sorted(data.items())
    dates = [d for d, _ in sorted_items]
    prices = [p for _, p in sorted_items]

    imgur_url = None
    if len(dates) >= 2:
        generate_graph(dates, prices)

        # 6. 画像アップロード
        imgur_url = upload_image(GRAPH_PATH)
        if imgur_url is None:
            print("画像アップロード失敗、テキストのみ送信")
    else:
        print("データが2件未満のためグラフ生成スキップ")

    # 7. LINE送信
    display_price = data[today]
    send_price_message(today, display_price, imgur_url=imgur_url, note=note)

    print("完了")


if __name__ == "__main__":
    main()
