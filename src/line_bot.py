import os
import time

import requests

LINE_TOKEN_URL = "https://api.line.me/v2/oauth/accessToken"
LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
SHOP_URL = "https://gogo.gs/shop/4099000297"


def _issue_access_token():
    """Channel ID + Secret から短期アクセストークンを発行する。"""
    channel_id = os.environ.get("LINE_CHANNEL_ID")
    channel_secret = os.environ.get("LINE_CHANNEL_SECRET")
    if not channel_id or not channel_secret:
        print("LINE_CHANNEL_ID / LINE_CHANNEL_SECRET が設定されていません")
        return None

    resp = requests.post(
        LINE_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": channel_id,
            "client_secret": channel_secret,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"トークン発行失敗: {resp.status_code} {resp.text}")
        return None

    token = resp.json().get("access_token")
    print("LINE アクセストークン発行成功")
    return token


def _build_flex_bubble(date_str, price, imgur_url, posted_time, prev_date, prev_price):
    """Flex Message bubbleを構築する。"""
    price_text = f"{price:.0f}" if price == int(price) else f"{price}"
    date_line = f"📅 {date_str}"
    if posted_time:
        date_line += f"  ({posted_time}投稿)"

    body_contents = [
        {
            "type": "text",
            "text": date_line,
            "size": "sm",
            "color": "#888888",
        },
        {
            "type": "box",
            "layout": "baseline",
            "margin": "md",
            "contents": [
                {
                    "type": "text",
                    "text": price_text,
                    "size": "4xl",
                    "weight": "bold",
                    "color": "#1DB446",
                    "flex": 0,
                },
                {
                    "type": "text",
                    "text": "円/L",
                    "size": "md",
                    "color": "#1DB446",
                    "margin": "sm",
                    "flex": 0,
                },
            ],
        },
        {
            "type": "text",
            "text": "レギュラー(会員価格)",
            "size": "xs",
            "color": "#aaaaaa",
        },
    ]

    if prev_price is not None:
        diff = price - prev_price
        if diff > 0:
            arrow, color = "↑", "#E02020"
        elif diff < 0:
            arrow, color = "↓", "#1DB446"
        else:
            arrow, color = "→", "#888888"
        prev_text = f"前回({prev_date}) {prev_price:g}円 {arrow} {abs(diff):.1f}円"
        body_contents.append({
            "type": "separator",
            "margin": "lg",
        })
        body_contents.append({
            "type": "text",
            "text": prev_text,
            "size": "sm",
            "color": color,
            "margin": "md",
            "wrap": True,
        })

    bubble = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "⛽ コストコ久山 ガソリン価格",
                    "weight": "bold",
                    "color": "#ffffff",
                    "size": "md",
                }
            ],
            "backgroundColor": "#3A7BD5",
            "paddingAll": "md",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": body_contents,
            "spacing": "sm",
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "uri",
                        "label": "データ元: gogo.gs",
                        "uri": SHOP_URL,
                    },
                }
            ],
        },
    }

    if imgur_url:
        bubble["hero"] = {
            "type": "image",
            "url": imgur_url,
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover",
            "action": {
                "type": "uri",
                "uri": imgur_url,
            },
        }

    return bubble


def send_price_message(date_str, price, imgur_url=None, note=None, posted_time=None,
                       prev_date=None, prev_price=None):
    """LINE broadcast で友だち全員にFlex Messageを送信する。"""
    token = _issue_access_token()
    if not token:
        return False

    price_text = f"{price:.0f}" if price == int(price) else f"{price}"
    alt_parts = [f"⛽コストコ久山 {price_text}円/L"]
    if prev_price is not None:
        diff = price - prev_price
        if diff > 0:
            alt_parts.append(f"(↑{abs(diff):.1f}円)")
        elif diff < 0:
            alt_parts.append(f"(↓{abs(diff):.1f}円)")
    alt_text = " ".join(alt_parts)

    bubble = _build_flex_bubble(date_str, price, imgur_url, posted_time, prev_date, prev_price)

    messages = [{
        "type": "flex",
        "altText": alt_text,
        "contents": bubble,
    }]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = {"messages": messages}

    for attempt in range(3):
        try:
            resp = requests.post(LINE_BROADCAST_URL, headers=headers, json=body, timeout=30)
            if resp.status_code == 200:
                print("LINE broadcast送信成功")
                return True
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                wait = 2 ** attempt
                print(f"LINE送信リトライ{attempt + 1}/3: {resp.status_code} {resp.text} ({wait}s待機)")
                time.sleep(wait)
                continue
            print(f"LINE送信エラー: {resp.status_code} {resp.text}")
            return False
        except Exception as e:
            wait = 2 ** attempt
            print(f"LINE送信例外リトライ{attempt + 1}/3: {e} ({wait}s待機)")
            time.sleep(wait)

    print("LINE送信失敗（リトライ上限）")
    return False
