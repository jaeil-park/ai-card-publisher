import os
import base64
import platform
import requests
from io import BytesIO
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


def wrap_text_by_pixels(text: str, font, max_width: int, draw: ImageDraw.Draw) -> list[str]:
    """Pillow의 textlength를 사용해 지정된 픽셀 너비를 넘지 않게 자동 줄바꿈합니다."""
    lines = []
    for paragraph in text.split("\n"):
        current_line = ""
        for char in paragraph:
            test_line = current_line + char
            # Pillow 10.0.0 이상에서는 getlength가 제거됨. draw.textlength()가 권장됨.
            length = draw.textlength(test_line, font=font)
            if length <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
    return lines


def generate_background(dalle_prompt: str) -> Image.Image:
    """
    DALL-E 3으로 사실적 뉴스 배경 이미지 생성
    - photorealistic 스타일 강제
    - 텍스트/그래픽 오버레이 제거
    - HD 품질 적용
    """
    # 사실성 강화 프롬프트 후처리
    enhanced_prompt = f"""
{dalle_prompt}

Style requirements:
- Photorealistic, high resolution news photograph quality
- Professional journalism photo style
- Dark moody cinematic lighting with subtle blue/orange tones
- No text overlays, no graphics, no UI elements
- No abstract art, no illustrations
- Real-world scene that directly represents the news topic
- Shot as if taken by a professional news photographer
- 16:9 composition, sharp focus on main subject
"""
    response = client.images.generate(
        model="dall-e-3",
        prompt=enhanced_prompt,
        size="1024x1024",
        quality="hd",
        style="natural",
        n=1
    )
    img_data = requests.get(response.data[0].url, timeout=30).content
    return Image.open(BytesIO(img_data)).convert("RGBA")


def overlay_text(img: Image.Image, title: str, summary: str) -> Image.Image:
    """
    Pillow로 한글 텍스트 오버레이
    - 중복 단어 최종 체크
    - 가독성 향상된 레이아웃
    - 팩트 강조 디자인
    """
    # 중복 단어 최종 체크 및 제거
    def clean_text(text: str, used_words: set) -> tuple[str, set]:
        import re
        words = re.findall(r'[가-힣a-zA-Z]{2,}', text)
        for word in words:
            if word in used_words:
                # 중복 단어 발견 시 경고만 출력 (자동 제거는 GPT 단에서 처리)
                print(f"⚠️ 중복 단어 발견: '{word}'")
            used_words.add(word)
        return text, used_words

    used_words = set()
    title, used_words   = clean_text(title, used_words)
    lines = summary.split("\n")

    # 반투명 그라데이션 오버레이 (하단 60%)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # 그라데이션 효과 (위→아래로 점점 진하게)
    for i in range(int(img.height * 0.40), img.height):
        alpha = int(200 * (i - img.height * 0.40) / (img.height * 0.60))
        overlay_draw.line(
            [(0, i), (img.width, i)],
            fill=(0, 0, 0, min(alpha, 200))
        )

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # 폰트 로드
    try:
        title_path = get_font_path(bold=True)
        body_path  = get_font_path(bold=False)
        font_title  = ImageFont.truetype(title_path, 48) if title_path else ImageFont.load_default()
        font_body   = ImageFont.truetype(body_path, 28)  if body_path  else ImageFont.load_default()
        font_label  = ImageFont.truetype(body_path, 22)  if body_path  else ImageFont.load_default()
    except Exception:
        font_title = ImageFont.load_default()
        font_body  = ImageFont.load_default()
        font_label = ImageFont.load_default()

    # 상단 카테고리 라벨 (파란색 배지)
    draw.rectangle([30, 30, 180, 62], fill=(30, 120, 255, 230))
    draw.text((40, 35), "📊 AI FACT CHECK", font=font_label, fill=(255, 255, 255, 255))

    # 제목 (노란색 강조 - 수치/팩트 포함)
    draw.text(
        (40, int(img.height * 0.60)),
        title,
        font=font_title,
        fill=(255, 220, 0, 255)
    )

    # 구분선
    draw.line(
        [(40, int(img.height * 0.60) + 58),
         (img.width - 40, int(img.height * 0.60) + 58)],
        fill=(255, 255, 255, 100), width=1
    )

    # 본문 3줄 (각 줄 앞에 아이콘 추가)
    icons = ["▶", "▶", "▶"]
    for i, line in enumerate(lines[:3]):
        _, used_words = clean_text(line, used_words)
        y_pos = int(img.height * 0.67) + i * 48
        # 아이콘 (흰색)
        draw.text((40, y_pos), icons[i], font=font_body, fill=(100, 180, 255, 255))
        # 본문 텍스트 (흰색)
        draw.text((65, y_pos), line, font=font_body, fill=(255, 255, 255, 230))

    # 하단 출처 표시
    draw.text(
        (40, img.height - 40),
        "ai-card-publisher | AI & Crypto Daily",
        font=font_label,
        fill=(200, 200, 200, 160)
    )

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
