import os

import requests

LINE_TOKEN_URL = "https://api.line.me/v2/oauth/accessToken"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


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


def send_price_message(date_str, price, imgur_url=None, note=None):
    """LINEプッシュメッセージでガソリン価格を送信する。"""
    user_id = os.environ.get("LINE_USER_ID")
    if not user_id:
        print("LINE_USER_ID が設定されていません")
        return False

    token = _issue_access_token()
    if not token:
        return False

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

    try:
        resp = requests.post(
            LINE_PUSH_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={"to": user_id, "messages": messages},
            timeout=30,
        )
        if resp.status_code == 200:
            print("LINE送信成功")
            return True
        print(f"LINE送信エラー: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        print(f"LINE送信エラー: {e}")
        return False
