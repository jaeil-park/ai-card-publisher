import os
import base64
import platform
import requests
from io import BytesIO
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))


def get_font_path(bold: bool = False) -> str | None:
    """OS별 한글 폰트 경로 자동 감지"""
    system    = platform.system()
    font_name = "NanumGothicBold.ttf" if bold else "NanumGothic.ttf"

    if system == "Linux":
        return f"/usr/share/fonts/truetype/nanum/{font_name}"
    elif system == "Windows":
        path = f"C:\\Windows\\Fonts\\{font_name}"
        return path if os.path.exists(path) else None
    else:
        return f"/Library/Fonts/{font_name}"


def generate_background(dalle_prompt: str) -> Image.Image:
    """DALL-E 3으로 배경 이미지 생성"""
    response = client.images.generate(
        model="dall-e-3",
        prompt=dalle_prompt + ", card news layout, dark futuristic background, neon accent, modern minimal UI",
        size="1024x1024",
        quality="standard",
        n=1
    )
    img_data = requests.get(response.data[0].url, timeout=30).content
    return Image.open(BytesIO(img_data)).convert("RGBA")


def overlay_text(img: Image.Image, title: str, summary: str) -> Image.Image:
    """Pillow로 한글 텍스트 오버레이 + AI 워터마크"""
    # 하단 어두운 그라데이션 패널
    overlay      = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [0, int(img.height * 0.55), img.width, img.height],
        fill=(0, 0, 0, 185)
    )
    # 상단 반투명 배지 배경
    overlay_draw.rectangle(
        [0, 0, img.width, 56],
        fill=(0, 0, 0, 140)
    )
    img  = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    try:
        title_path  = get_font_path(bold=True)
        body_path   = get_font_path(bold=False)
        font_title  = ImageFont.truetype(title_path, 52) if title_path else ImageFont.load_default()
        font_body   = ImageFont.truetype(body_path, 30)  if body_path  else ImageFont.load_default()
        font_badge  = ImageFont.truetype(body_path, 22)  if body_path  else ImageFont.load_default()
    except Exception:
        font_title = font_body = font_badge = ImageFont.load_default()

    kst_date = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y.%m.%d")

    # 상단 좌: 🤖 AI DAILY 배지
    draw.text((16, 14), "🤖 AI DAILY", font=font_badge, fill=(80, 220, 255, 255))

    # 상단 우: 날짜
    date_bbox = draw.textbbox((0, 0), kst_date, font=font_badge)
    date_w    = date_bbox[2] - date_bbox[0]
    draw.text((img.width - date_w - 16, 14), kst_date, font=font_badge, fill=(200, 200, 200, 220))

    # 제목 (노란색 강조)
    draw.text((50, int(img.height * 0.58)), title,
              font=font_title, fill=(255, 220, 0, 255))

    # 본문 3줄 (흰색)
    for i, line in enumerate(summary.split("\n")[:3]):
        draw.text((50, int(img.height * 0.68) + i * 52), line,
                  font=font_body, fill=(255, 255, 255, 230))

    # 하단 우: AI Generated 워터마크
    wm_text  = "✨ AI Generated Content"
    wm_bbox  = draw.textbbox((0, 0), wm_text, font=font_badge)
    wm_w     = wm_bbox[2] - wm_bbox[0]
    draw.text((img.width - wm_w - 16, img.height - 30), wm_text,
              font=font_badge, fill=(160, 160, 160, 180))

    return img.convert("RGB")


def upload_image(image: Image.Image) -> str:
    """Cloudinary에 업로드 후 Public URL 반환 (Instagram/Threads API 호환)"""
    import hashlib, time

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode()

    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    api_key    = os.environ.get("CLOUDINARY_API_KEY", "")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "")

    if not all([cloud_name, api_key, api_secret]):
        raise ValueError("CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET 미설정")

    timestamp = str(int(time.time()))
    signature = hashlib.sha1(f"timestamp={timestamp}{api_secret}".encode()).hexdigest()

    res = requests.post(
        f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
        data={
            "file":      f"data:image/png;base64,{b64}",
            "timestamp": timestamp,
            "api_key":   api_key,
            "signature": signature,
        },
        timeout=60
    )
    res.raise_for_status()
    url = res.json()["secure_url"]
    print(f"✅ Image uploaded: {url}")
    return url


def create_card(content: dict) -> str:
    """전체 카드 생성 파이프라인 → Public URL 반환"""
    bg   = generate_background(content["dalle_prompt"])
    card = overlay_text(bg, content["title"], content["summary"])
    return upload_image(card)
