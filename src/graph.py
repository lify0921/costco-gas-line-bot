import glob
import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPHS_DIR = os.path.join(ROOT_DIR, "data", "graphs")
GRAPH_PATH = os.path.join(ROOT_DIR, "data", "graph.png")  # 互換用（使わない）
GRAPH_RETENTION_DAYS = 30


def cleanup_old_graphs():
    """GRAPH_RETENTION_DAYS より古いグラフ画像を削除する。"""
    if not os.path.isdir(GRAPHS_DIR):
        return
    cutoff = datetime.now() - timedelta(days=GRAPH_RETENTION_DAYS)
    removed = 0
    for path in glob.glob(os.path.join(GRAPHS_DIR, "graph-*.png")):
        name = os.path.basename(path)
        try:
            d = datetime.strptime(name[len("graph-"):-len(".png")], "%Y-%m-%d")
        except ValueError:
            continue
        if d < cutoff:
            os.remove(path)
            removed += 1
    if removed:
        print(f"古いグラフを削除: {removed}件")


def generate_graph(dates, prices, date_str=None):
    """年間推移と直近2週間の2段グラフを生成する。
    Args:
        dates: list of date strings "YYYY-MM-DD"
        prices: list of float prices
    Returns: 出力ファイルパス
    """
    # 日本語フォント設定
    try:
        plt.rcParams["font.family"] = "Noto Sans CJK JP"
    except Exception:
        plt.rcParams["font.family"] = "sans-serif"

    dt_dates = [datetime.strptime(d, "%Y-%m-%d") for d in dates]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), dpi=150)
    fig.suptitle("コストコ久山 レギュラーガソリン価格（会員）", fontsize=14, fontweight="bold")

    # 上段: 全期間推移
    ax1.plot(dt_dates, prices, color="#2196F3", linewidth=1.5, marker="o", markersize=3)
    ax1.set_title("全期間推移", fontsize=11)
    ax1.set_ylabel("価格（円/L）", fontsize=10)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y/%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.tick_params(axis="x", rotation=45)
    ax1.grid(True, alpha=0.3)
    if prices:
        margin = max((max(prices) - min(prices)) * 0.1, 2)
        ax1.set_ylim(min(prices) - margin, max(prices) + margin)

    # 下段: 直近2週間
    cutoff = datetime.now() - timedelta(days=14)
    recent_idx = [i for i, d in enumerate(dt_dates) if d >= cutoff]
    if recent_idx:
        r_dates = [dt_dates[i] for i in recent_idx]
        r_prices = [prices[i] for i in recent_idx]
    else:
        # データが2週間以内にない場合は直近7点を表示
        r_dates = dt_dates[-7:]
        r_prices = prices[-7:]

    ax2.plot(r_dates, r_prices, color="#F44336", linewidth=2, marker="o", markersize=6)
    for d, p in zip(r_dates, r_prices):
        ax2.annotate(f"{p:.0f}", (d, p), textcoords="offset points",
                     xytext=(0, 10), ha="center", fontsize=8, fontweight="bold")
    ax2.set_title("直近2週間", fontsize=11)
    ax2.set_ylabel("価格（円/L）", fontsize=10)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax2.xaxis.set_major_locator(mdates.DayLocator())
    ax2.tick_params(axis="x", rotation=45)
    ax2.grid(True, alpha=0.3)
    if r_prices:
        margin = max((max(r_prices) - min(r_prices)) * 0.1, 2)
        ax2.set_ylim(min(r_prices) - margin, max(r_prices) + margin)

    fig.tight_layout()
    os.makedirs(GRAPHS_DIR, exist_ok=True)
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = os.path.join(GRAPHS_DIR, f"graph-{date_str}.png")
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"グラフ生成完了: {out_path}")
    return out_path
