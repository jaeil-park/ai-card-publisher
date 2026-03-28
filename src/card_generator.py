import os
import base64
import platform
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

SLIDE_SIZE = (1024, 1024)
BRAND      = "ai-card-publisher | AI & Crypto Daily"


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


def _font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    """폰트 로드 헬퍼 (실패 시 기본 폰트 반환)"""
    path = get_font_path(bold=bold)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def wrap_text_by_pixels(text: str, font, max_width: int, draw: ImageDraw.Draw) -> list[str]:
    """지정된 픽셀 너비를 넘지 않게 자동 줄바꿈"""
    lines = []
    for paragraph in text.split("\n"):
        current_line = ""
        for char in paragraph:
            test_line = current_line + char
            if draw.textlength(test_line, font=font) <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
    return lines


def generate_background(dalle_prompt: str) -> Image.Image:
    """DALL-E 3 HD + photorealistic 뉴스 배경 이미지 생성

    Instagram 가이드라인: 고품질 이미지 (720px+, 적절한 조명)
    """
    enhanced = f"""
{dalle_prompt}

Style requirements:
- Photorealistic, high resolution news photograph quality
- Professional journalism photo style
- Dark moody cinematic lighting with subtle blue/orange tones
- No text overlays, no graphics, no UI elements
- No abstract art, no illustrations
- Real-world scene that directly represents the news topic
- Shot as if taken by a professional news photographer
- Sharp focus on main subject
"""
    response = client.images.generate(
        model="dall-e-3",
        prompt=enhanced,
        size="1024x1024",
        quality="hd",       # Instagram 고품질 권장 사항 반영
        style="natural",    # photorealistic 스타일
        n=1
    )
    img_data = requests.get(response.data[0].url, timeout=30).content
    return Image.open(BytesIO(img_data)).convert("RGBA")


# ── 슬라이드 1: 훅 (첫 3초 안에 관심 유도) ────────────────

def create_slide1(stat: str, headline: str, sub: str, bg: Image.Image) -> Image.Image:
    """슬라이드 1 - 큰 수치/팩트로 첫 3초 안에 관심 유도

    Instagram 가이드라인:
    - 첫 슬라이드에 텍스트 추가로 맥락 설정
    - 3초 안에 관심 유도
    - 매 초를 의미있게 채우기
    """
    img = bg.copy()

    # 전체 약한 어둠 + 하단 강한 그라데이션
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, 0, 1024, 1024], fill=(0, 0, 0, 80))
    for i in range(480, 1024):
        alpha = int(190 * (i - 480) / 544)
        od.line([(0, i), (1024, i)], fill=(0, 0, 0, min(alpha, 190)))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # 폰트
    f_stat     = _font(bold=True,  size=110)
    f_headline = _font(bold=True,  size=56)
    f_sub      = _font(bold=False, size=28)
    f_xs       = _font(bold=False, size=20)

    # 상단 카테고리 배지
    draw.rectangle([30, 28, 228, 60], fill=(30, 120, 255, 220))
    draw.text((42, 33), "📊 AI FACT CHECK", font=f_xs, fill=(255, 255, 255, 255))

    # BIG STAT (중앙 상단 - 임팩트 최대화)
    stat_bbox = draw.textbbox((0, 0), stat, font=f_stat)
    stat_w    = stat_bbox[2] - stat_bbox[0]
    stat_x    = (1024 - stat_w) // 2
    # 그림자 효과
    draw.text((stat_x + 3, 313), stat, font=f_stat, fill=(0, 0, 0, 160))
    draw.text((stat_x, 310), stat, font=f_stat, fill=(255, 220, 0, 255))

    # Sub 텍스트 (수치 바로 아래, 흰색)
    sub_bbox = draw.textbbox((0, 0), sub, font=f_sub)
    sub_w    = sub_bbox[2] - sub_bbox[0]
    draw.text(((1024 - sub_w) // 2, 448), sub, font=f_sub, fill=(200, 200, 200, 220))

    # 헤드라인 (하단 좌측 정렬)
    draw.text((40, 680), headline, font=f_headline, fill=(255, 255, 255, 255))

    # 구분선
    draw.line([(40, 752), (984, 752)], fill=(255, 255, 255, 70), width=1)

    # 스와이프 유도 (Instagram 가이드라인: 계속 스크롤하도록 유도)
    draw.text((40, 768), "스와이프해서 자세히 보기 →", font=f_xs, fill=(120, 160, 255, 200))

    # 슬라이드 진행 표시 (1/3)
    draw.text((984 - 40, 768), "1/3", font=f_xs, fill=(160, 160, 160, 180))

    # 하단 브랜드
    draw.text((40, 992), BRAND, font=f_xs, fill=(140, 140, 140, 130))

    return img.convert("RGB")


# ── 슬라이드 2: 상세 내용 (맥락 + 데이터) ─────────────────

def create_slide2(headline: str, points: list[str], bg: Image.Image) -> Image.Image:
    """슬라이드 2 - 왜/어떻게: 상세 팩트로 계속 읽도록 유도

    Instagram 가이드라인:
    - 슬라이드마다 다른 정보로 계속 스크롤 유도
    - 수치/팩트 기반으로 낚시성 콘텐츠 방지
    """
    img = bg.copy()

    # 강한 어두운 오버레이 (텍스트 가독성 확보)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, 0, 1024, 1024], fill=(0, 0, 0, 175))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # 폰트
    f_headline = _font(bold=True,  size=48)
    f_point    = _font(bold=False, size=30)
    f_num      = _font(bold=True,  size=22)
    f_xs       = _font(bold=False, size=20)

    # 상단 진행 표시
    draw.rectangle([30, 28, 90, 56], fill=(60, 60, 80, 200))
    draw.text((40, 33), "2/3", font=f_xs, fill=(160, 160, 160, 220))

    # 헤드라인 (노란색)
    draw.text((40, 90), headline, font=f_headline, fill=(255, 220, 0, 255))

    # 구분선
    draw.line([(40, 154), (984, 154)], fill=(255, 255, 255, 70), width=1)

    # 데이터 포인트 3개 (각각 번호 원형 배지 + 텍스트)
    y_starts = [200, 400, 600]
    for i, (point, y) in enumerate(zip(points[:3], y_starts)):
        # 번호 원형 배지
        draw.ellipse([40, y, 82, y + 42], fill=(30, 120, 255, 210))
        num_bbox = draw.textbbox((0, 0), str(i + 1), font=f_num)
        num_w = num_bbox[2] - num_bbox[0]
        draw.text((61 - num_w // 2, y + 8), str(i + 1), font=f_num, fill=(255, 255, 255, 255))

        # 포인트 텍스트 (자동 줄바꿈)
        wrapped = wrap_text_by_pixels(point, f_point, 860, draw)
        for j, line in enumerate(wrapped[:2]):
            draw.text((100, y + j * 42), line, font=f_point, fill=(255, 255, 255, 230))

    # 스와이프 유도
    draw.line([(40, 790), (984, 790)], fill=(255, 255, 255, 50), width=1)
    draw.text((40, 806), "마지막 슬라이드에서 결론 확인 →", font=f_xs, fill=(120, 160, 255, 190))

    # 하단 브랜드
    draw.text((40, 992), BRAND, font=f_xs, fill=(140, 140, 140, 130))

    return img.convert("RGB")


# ── 슬라이드 3: 핵심 요약 + 댓글/팔로우 CTA ───────────────

def create_slide3(takeaway: str, cta_question: str, follow_cta: str) -> Image.Image:
    """슬라이드 3 - 요약 + 댓글 CTA: 깊은 참여 유도

    Instagram 가이드라인:
    - 깊이 있는 참여(댓글, 저장, 공유)에 집중
    - 청중과 소통하는 열린 질문으로 대화 유도
    - 팔로우 유도로 지속적인 도달 확보
    - 워터마크 없음 (자체 브랜드만)
    """
    # 다크 배경 프로그래밍으로 생성 (DALL-E 호출 없음 - 비용 절약)
    img = Image.new("RGBA", SLIDE_SIZE, (8, 10, 24, 255))

    # 상단 미묘한 그라데이션 (파란빛)
    overlay = Image.new("RGBA", SLIDE_SIZE, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(350):
        alpha = int(25 * (1 - i / 350))
        od.line([(0, i), (1024, i)], fill=(40, 70, 130, alpha))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # 폰트
    f_takeaway = _font(bold=True,  size=52)
    f_cta      = _font(bold=True,  size=34)
    f_follow   = _font(bold=False, size=28)
    f_label    = _font(bold=False, size=20)

    # 상단 진행 표시
    draw.rectangle([30, 28, 90, 56], fill=(60, 60, 80, 200))
    draw.text((40, 33), "3/3", font=f_label, fill=(160, 160, 160, 220))

    # 핵심 정리 레이블 배지
    draw.rectangle([40, 110, 196, 142], fill=(30, 120, 255, 220))
    draw.text((52, 116), "✓ 핵심 정리", font=f_label, fill=(255, 255, 255, 255))

    # Takeaway (노란색, 자동 줄바꿈)
    wrapped_tw = wrap_text_by_pixels(takeaway, f_takeaway, 944, draw)
    y = 180
    for line in wrapped_tw[:3]:
        draw.text((40, y), line, font=f_takeaway, fill=(255, 220, 0, 255))
        y += 68

    # 구분선
    divider_y = y + 24
    draw.line([(40, divider_y), (984, divider_y)], fill=(255, 255, 255, 50), width=1)

    # CTA 박스 (댓글 유도 - Instagram 깊은 참여 가이드라인)
    cta_y = divider_y + 40
    draw.rectangle(
        [40, cta_y, 984, cta_y + 140],
        fill=(20, 80, 180, 50),
        outline=(30, 120, 255, 100),
        width=1
    )
    draw.text((56, cta_y + 14), "💬 여러분의 생각은?", font=f_label, fill=(100, 170, 255, 255))
    wrapped_cta = wrap_text_by_pixels(cta_question, f_cta, 900, draw)
    cta_text_y = cta_y + 44
    for line in wrapped_cta[:2]:
        draw.text((56, cta_text_y), line, font=f_cta, fill=(255, 255, 255, 240))
        cta_text_y += 48

    # 팔로우 유도 (Instagram 가이드라인: 지속적인 도달 확보)
    follow_y = cta_y + 168
    draw.text((40, follow_y), "👉 " + follow_cta, font=f_follow, fill=(140, 190, 255, 200))

    # 하단 브랜드
    draw.text((40, 992), BRAND, font=f_label, fill=(140, 140, 140, 130))

    return img.convert("RGB")


# ── 캐러셀 생성 파이프라인 ────────────────────────────────

def generate_carousel(content: dict) -> list[str]:
    """3장 캐러셀 이미지 생성 → Cloudinary URL 리스트 반환

    Instagram 가이드라인:
    - 슬라이드는 단일 사진보다 도달 성과가 더 좋음
    - 슬라이드 1에서 맥락 설정 → 계속 스크롤 유도
    - 고품질 이미지 (HD DALL-E, 1024x1024)
    """
    s1 = content["slide1"]
    s2 = content["slide2"]
    s3 = content["slide3"]

    print("🎨 배경 이미지 생성 중... (DALL-E 3 HD)")
    bg = generate_background(s1["dalle_prompt"])

    print("🖼️  슬라이드 1/3: 훅 생성 중...")
    slide1 = create_slide1(s1["stat"], s1["headline"], s1["sub"], bg)

    print("🖼️  슬라이드 2/3: 상세 내용 생성 중...")
    slide2 = create_slide2(s2["headline"], s2["points"], bg)

    print("🖼️  슬라이드 3/3: CTA 생성 중...")
    slide3 = create_slide3(
        s3["takeaway"],
        s3["cta_question"],
        s3.get("follow_cta", "팔로우하면 매일 AI 소식!")
    )

    print("☁️  Cloudinary 업로드 중...")
    urls = [
        upload_image(slide1),
        upload_image(slide2),
        upload_image(slide3),
    ]
    return urls


# ── 이미지 업로드 ─────────────────────────────────────────

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
    print(f"  ✅ 업로드 완료: {url}")
    return url
