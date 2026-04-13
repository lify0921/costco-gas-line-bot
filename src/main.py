import csv
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from scraper import scrape_current_price, scrape_price_history
from graph import generate_graph, GRAPH_PATH
from imgur import upload_image
from line_bot import send_price_message

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT_DIR, "data", "prices.csv")
LAST_NOTIFIED_PATH = os.path.join(ROOT_DIR, "data", "last_notified.json")
TZ = ZoneInfo("Asia/Tokyo")


def load_csv():
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
    sorted_items = sorted(data.items())
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "price"])
        for date_str, price in sorted_items:
            writer.writerow([date_str, price])
    print(f"CSV保存完了: {len(sorted_items)}件")


def load_last_notified():
    if not os.path.exists(LAST_NOTIFIED_PATH):
        return None
    try:
        with open(LAST_NOTIFIED_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"last_notified.json読み込み失敗: {e}")
        return None


def save_last_notified(date_str, price):
    with open(LAST_NOTIFIED_PATH, "w") as f:
        json.dump({"date": date_str, "price": price}, f, ensure_ascii=False, indent=2)
    print(f"last_notified.json保存: {date_str} {price}円")


def main():
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    print(f"実行日: {today}")

    data = load_csv()
    print(f"既存データ: {len(data)}件")

    if len(data) == 0:
        print("バックフィル開始...")
        history = scrape_price_history()
        for date_str, price in history:
            data[date_str] = price
        print(f"バックフィル完了: {len(history)}件取得")

    current_price, posted_time = scrape_current_price()
    if current_price is None:
        print("今日の価格取得失敗。CSV更新・通知ともにスキップ（翌日再試行）")
        sys.exit(0)

    data[today] = current_price
    print(f"今日の価格: {current_price}円")
    save_csv(data)

    last = load_last_notified()
    if last and last.get("price") == current_price:
        print(f"前回通知価格と同じ({current_price}円)のため通知スキップ")
        sys.exit(0)

    prev_price = last.get("price") if last else None
    prev_date = last.get("date") if last else None

    sorted_items = sorted(data.items())
    dates = [d for d, _ in sorted_items]
    prices = [p for _, p in sorted_items]

    imgur_url = None
    if len(dates) >= 2:
        generate_graph(dates, prices)
        imgur_url = upload_image(GRAPH_PATH)
        if imgur_url is None:
            print("画像アップロード失敗、テキストのみ送信")
    else:
        print("データが2件未満のためグラフ生成スキップ")

    ok = send_price_message(
        today, current_price,
        imgur_url=imgur_url,
        posted_time=posted_time,
        prev_date=prev_date,
        prev_price=prev_price,
    )
    if ok:
        save_last_notified(today, current_price)
    else:
        print("送信失敗のためlast_notifiedは更新しない")

    print("完了")


if __name__ == "__main__":
    main()
