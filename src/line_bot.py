import os

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    ImageMessage,
)


def send_price_message(date_str, price, imgur_url=None, note=None):
    """LINEプッシュメッセージでガソリン価格を送信する。"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")

    if not token or not user_id:
        print("LINE認証情報が設定されていません")
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

    messages = [TextMessage(text=text)]
    if imgur_url:
        messages.append(
            ImageMessage(
                original_content_url=imgur_url,
                preview_image_url=imgur_url,
            )
        )

    try:
        config = Configuration(access_token=token)
        with ApiClient(config) as api_client:
            api = MessagingApi(api_client)
            api.push_message(
                PushMessageRequest(to=user_id, messages=messages)
            )
        print("LINE送信成功")
        return True
    except Exception as e:
        print(f"LINE送信エラー: {e}")
        return False
