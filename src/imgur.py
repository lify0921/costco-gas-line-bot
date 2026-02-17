import base64
import os

import requests

IMGUR_UPLOAD_URL = "https://api.imgur.com/3/image"


def upload_to_imgur(image_path):
    """画像をImgurにアップロードしてURLを返す。失敗時はNoneを返す。"""
    client_id = os.environ.get("IMGUR_CLIENT_ID")
    if not client_id:
        print("IMGUR_CLIENT_ID が設定されていません")
        return None

    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        resp = requests.post(
            IMGUR_UPLOAD_URL,
            headers={"Authorization": f"Client-ID {client_id}"},
            data={"image": image_data, "type": "base64"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("success"):
            url = data["data"]["link"]
            # HTTPSを強制
            url = url.replace("http://", "https://")
            print(f"Imgur アップロード成功: {url}")
            return url

        print(f"Imgur アップロード失敗: {data}")
        return None
    except Exception as e:
        print(f"Imgur エラー: {e}")
        return None
