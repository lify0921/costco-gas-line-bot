import requests

CATBOX_API_URL = "https://catbox.moe/user/api.php"


def upload_image(image_path):
    """画像をcatbox.moeにアップロードしてURLを返す。失敗時はNoneを返す。"""
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                CATBOX_API_URL,
                data={"reqtype": "fileupload"},
                files={"fileToUpload": ("graph.png", f, "image/png")},
                timeout=60,
            )
        resp.raise_for_status()

        url = resp.text.strip()
        if url.startswith("https://"):
            print(f"画像アップロード成功: {url}")
            return url

        print(f"アップロード失敗: {resp.text}")
        return None
    except Exception as e:
        print(f"画像アップロードエラー: {e}")
        return None
