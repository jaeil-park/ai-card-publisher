import os
from PIL import Image
import base64
import hashlib
import time
import requests
from io import BytesIO

# ── Image Uploader ─────────────────────────────────────────────
def upload_image(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode()

    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    api_key    = os.environ.get("CLOUDINARY_API_KEY", "")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "")
    if not all([cloud_name, api_key, api_secret]):
        raise ValueError("Cloudinary 환경 변수가 설정되지 않았습니다.")

    timestamp = str(int(time.time()))
    signature = hashlib.sha1(f"timestamp={timestamp}{api_secret}".encode()).hexdigest()

    res = requests.post(
        f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
        data={
            "file": f"data:image/png;base64,{b64}", "timestamp": timestamp,
            "api_key": api_key, "signature": signature,
        },
        timeout=60,
    )
    res.raise_for_status()
    url = res.json()["secure_url"]
    print(f"  ☁️ Cloudinary 업로드 완료: {url}")
    return url