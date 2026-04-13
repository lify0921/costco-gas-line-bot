import argparse
import csv
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from scraper import scrape_current_price, scrape_price_history
from graph import generate_graph, cleanup_old_graphs
from line_bot import send_price_message

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT_DIR, "data", "prices.csv")
LAST_NOTIFIED_PATH = os.path.join(ROOT_DIR, "data", "last_notified.json")
STATE_PATH = "/tmp/costco-gas-state.json"
TZ = ZoneInfo("Asia/Tokyo")

GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "lify0921/costco-gas-line-bot")
GITHUB_BRANCH = os.environ.get("GITHUB_REF_NAME", "main")


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


def write_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"state保存: {state}")


def read_state():
    if not os.path.exists(STATE_PATH):
        print(f"state.json が存在しません: {STATE_PATH}")
        return None
    with open(STATE_PATH, "r") as f:
        return json.load(f)


def build_raw_url(graph_path):
    """data/graphs/graph-YYYY-MM-DD.png → raw.githubusercontent.com URL"""
    rel = os.path.relpath(graph_path, ROOT_DIR)
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{rel}"


def stage_prepare():
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    print(f"[prepare] 実行日: {today}")

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
        print("価格取得失敗。通知スキップ")
        write_state({"notify": False})
        return

    data[today] = current_price
    print(f"今日の価格: {current_price}円")
    save_csv(data)

    last = load_last_notified()
    if last and last.get("price") == current_price:
        print(f"前回通知価格と同じ({current_price}円)のため通知スキップ")
        write_state({"notify": False})
        return

    prev_price = last.get("price") if last else None
    prev_date = last.get("date") if last else None

    cleanup_old_graphs()

    sorted_items = sorted(data.items())
    dates = [d for d, _ in sorted_items]
    prices = [p for _, p in sorted_items]

    graph_url = None
    if len(dates) >= 2:
        graph_path = generate_graph(dates, prices, date_str=today)
        graph_url = build_raw_url(graph_path)
        print(f"グラフURL: {graph_url}")
    else:
        print("データが2件未満のためグラフ生成スキップ")

    write_state({
        "notify": True,
        "date": today,
        "price": current_price,
        "posted_time": posted_time,
        "prev_date": prev_date,
        "prev_price": prev_price,
        "graph_url": graph_url,
    })


def stage_notify():
    state = read_state()
    if state is None or not state.get("notify"):
        print("[notify] 通知不要")
        return

    print(f"[notify] 送信: {state['date']} {state['price']}円")
    ok = send_price_message(
        state["date"], state["price"],
        imgur_url=state.get("graph_url"),
        posted_time=state.get("posted_time"),
        prev_date=state.get("prev_date"),
        prev_price=state.get("prev_price"),
    )
    if ok:
        save_last_notified(state["date"], state["price"])
    else:
        print("送信失敗のためlast_notifiedは更新しない")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["prepare", "notify"], required=True)
    args = parser.parse_args()

    if args.stage == "prepare":
        stage_prepare()
    else:
        stage_notify()
    print("完了")


if __name__ == "__main__":
    main()
