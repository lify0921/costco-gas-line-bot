import os
import json

import requests

LINE_API_URL = "https://api.line.me/v2/bot/message/push"


def send_price_message(date_str, price, imgur_url=None, note=None):
    """LINEプッシュメッセージでガソリン価格を送信する。"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")

    if not token or not user_id:
        print("LINE認証情報が設定されていません")
        return False

    print(f"トークン長: {len(token)}, 先頭: {token[:5]}..., 末尾: ...{token[-5:]}")

    # トークン検証
    verify_resp = requests.get(
        "https://api.line.me/v2/bot/info",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    print(f"トークン検証: status={verify_resp.status_code}, body={verify_resp.text[:200]}")

    price_text = f"{price:.0f}" if price == int(price) else f"{price}"
    text = (
        f"\u26fd コストコ久山 ガソリン価格\n"
        f"\U0001f4c5 {date_str}\n"
        f"\n"
        f"レギュラー(会員価格): {price_text}円/L"
    )
    if note:
        text += f"\n\n{note}"

    messages = [{"type": "text", "text": text}]
    if imgur_url:
        messages.append({
            "type": "image",
            "originalContentUrl": imgur_url,
            "previewImageUrl": imgur_url,
        })

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = {"to": user_id, "messages": messages}

    try:
        resp = requests.post(LINE_API_URL, headers=headers, json=body, timeout=30)
        print(f"LINE API status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"LINE API response: {resp.text}")
        if resp.status_code == 200:
            print("LINE送信成功")
            return True
        return False
    except Exception as e:
        print(f"LINE送信エラー: {e}")
        return False
