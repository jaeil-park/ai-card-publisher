import os
import math
import base64
import platform
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

W, H = 1024, 1024
SLIDE_SIZE = (W, H)
BRAND = "HaeWooSo  |  @jaeil.park"

# ── 색상 팔레트 ─────────────────────────────────────────────────
YELLOW = (255, 215, 0)
CYAN   = (0, 210, 255)
BLUE   = (30, 120, 255)
WHITE  = (255, 255, 255)
GRAY   = (160, 165, 185)
DARK   = (8, 10, 24)
GREEN  = (0, 200, 110)


# ── 폰트 ────────────────────────────────────────────────────────

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


# ── 시각 효과 헬퍼 ──────────────────────────────────────────────

def _rounded_box(draw, xy, fill=None, outline=None, radius=10, width=2):
    """Pillow 9+ rounded_rectangle 래퍼"""
    try:
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    except AttributeError:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)


def _glow_composite(base: Image.Image, text: str, pos: tuple,
                    font, color: tuple, radius: int = 20) -> Image.Image:
    """텍스트 글로우 레이어를 블러 후 base에 합성"""
    r, g, b = color[:3]
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    gd.text(pos, text, font=font, fill=(r, g, b, 200))
    glow = glow.filter(ImageFilter.GaussianBlur(radius))
    return Image.alpha_composite(base, glow)


def _accent_hline(draw, x1: int, y: int, x2: int, color: tuple, lw: int = 2):
    """중앙 밝고 양 끝 페이드아웃 수평 액센트 라인"""
    r, g, b = color[:3]
    length = x2 - x1
    for step in range(0, length, 3):
        t     = step / length
        alpha = int(230 * math.sin(t * math.pi))
        x     = x1 + step
        draw.line([(x, y), (x + 3, y)], fill=(r, g, b, alpha), width=lw)


def _dot_grid(draw, spacing: int = 52, alpha: int = 10):
    """미묘한 닷 그리드 배경 패턴"""
    for x in range(spacing // 2, W, spacing):
        for y in range(spacing // 2, H, spacing):
            draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(255, 255, 255, alpha))


def _progress_dots(draw, current: int, total: int, cx: int, y: int):
    """Instagram 스타일 진행 점 표시"""
    gap = 24
    sx  = cx - (total - 1) * gap // 2
    for i in range(total):
        x = sx + i * gap
        if i == current - 1:
            _rounded_box(draw, [x - 11, y - 5, x + 11, y + 5],
                         fill=(*BLUE, 240), radius=5)
        else:
            draw.ellipse([x - 4, y - 4, x + 4, y + 4],
                         fill=(100, 105, 130, 150))


def _text_w(draw_or_img, text: str, font) -> int:
    """텍스트 렌더링 너비 측정 (draw 객체 없이도 사용 가능)"""
    tmp  = Image.new("RGBA", (1, 1))
    tmp_d = ImageDraw.Draw(tmp)
    bb   = tmp_d.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


# ── DALL-E 3 배경 생성 ──────────────────────────────────────────

def generate_background(dalle_prompt: str) -> Image.Image:
    """DALL-E 3 HD + photorealistic 뉴스 배경 이미지 생성"""
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
        quality="hd",
        style="natural",
        n=1,
    )
    img_data = requests.get(response.data[0].url, timeout=30).content
    return Image.open(BytesIO(img_data)).convert("RGBA")


# ── 슬라이드 1 (GIF 지원 프레임 렌더러) ─────────────────────────

def _build_slide1_frame(stat: str, headline: str, sub: str,
                        bg: Image.Image, glow_r: int = 18) -> Image.Image:
    """슬라이드 1 단일 프레임 — glow_r 을 바꿔 GIF 애니메이션 생성"""
    img = bg.copy()

    # ─ 오버레이 ─
    ov  = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od  = ImageDraw.Draw(ov)
    od.rectangle([0, 0, W, H], fill=(0, 0, 0, 70))
    for i in range(360, H):                          # 하단 그라데이션
        a = int(210 * ((i - 360) / (H - 360)) ** 1.3)
        od.line([(0, i), (W, i)], fill=(0, 0, 0, min(a, 210)))
    for i in range(130):                             # 상단 청빛 tint
        od.line([(0, i), (W, i)], fill=(10, 20, 70, int(45 * (1 - i / 130))))
    _dot_grid(od, alpha=9)
    img = Image.alpha_composite(img, ov)

    # ─ STAT 글로우 (2겹) ─
    f_stat = _font(bold=True, size=130)
    sw     = _text_w(None, stat, f_stat)
    sx, sy = (W - sw) // 2, 275
    img = _glow_composite(img, stat, (sx, sy), f_stat, YELLOW,              radius=glow_r)
    img = _glow_composite(img, stat, (sx, sy), f_stat, (255, 255, 200),    radius=max(4, glow_r // 4))

    draw = ImageDraw.Draw(img)

    f_hl  = _font(bold=True,  size=58)
    f_sub = _font(bold=False, size=32)
    f_sm  = _font(bold=False, size=22)
    f_xs  = _font(bold=False, size=18)

    # ─ 카테고리 배지 ─
    _rounded_box(draw, [32, 30, 228, 66], fill=(*CYAN, 215), radius=8)
    draw.text((46, 38), "AI FACT CHECK", font=f_xs, fill=(8, 8, 28, 255))

    # ─ BIG STAT ─
    draw.text((sx + 3, sy + 4), stat, font=f_stat, fill=(0, 0, 0, 150))
    draw.text((sx,     sy),     stat, font=f_stat, fill=(*YELLOW, 255))

    # ─ stat 아래 사이언 액센트 라인 ─
    tmp_d   = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    stat_h  = tmp_d.textbbox((0, 0), stat, font=f_stat)[3]
    acc_y   = sy + stat_h + 18
    _accent_hline(draw, 100, acc_y, W - 100, CYAN)

    # ─ Sub 텍스트 (수치 맥락) ─
    sub_y = acc_y + 22
    sub_w = draw.textlength(sub, font=f_sub)
    draw.text(((W - sub_w) // 2, sub_y), sub, font=f_sub, fill=(210, 230, 255, 225))

    # ─ 두 번째 액센트 라인 (희미) ─
    draw.line([(80, sub_y + 50), (W - 80, sub_y + 50)], fill=(*BLUE, 50), width=1)

    # ─ 헤드라인 (하단 강조 영역) ─
    hl_y     = 688
    draw.rectangle([32, hl_y - 8, 40, hl_y + 78], fill=(*CYAN, 200))  # 왼쪽 바
    wrapped  = wrap_text_by_pixels(headline, f_hl, W - 80, draw)
    for idx, line in enumerate(wrapped[:2]):
        draw.text((54, hl_y + idx * 76), line, font=f_hl, fill=(*WHITE, 255))

    # ─ 구분선 ─
    div_y = hl_y + len(wrapped[:2]) * 76 + 24
    draw.line([(32, div_y), (W - 32, div_y)], fill=(255, 255, 255, 40), width=1)

    # ─ CTA + 진행 점 ─
    cta_y = div_y + 18
    draw.text((54, cta_y), "스와이프해서 자세히 보기  ›", font=f_sm, fill=(*CYAN, 195))
    _progress_dots(draw, 1, 3, W // 2, cta_y + 38)

    # ─ 브랜드 ─
    draw.text((54, H - 26), BRAND, font=f_xs, fill=(120, 125, 150, 130))

    return img.convert("RGB")


def create_slide1(stat: str, headline: str, sub: str, bg: Image.Image) -> Image.Image:
    return _build_slide1_frame(stat, headline, sub, bg, glow_r=18)


def create_slide1_gif(stat: str, headline: str, sub: str,
                      bg: Image.Image) -> list[Image.Image]:
    """4프레임 펄싱 글로우 GIF 프레임 리스트"""
    return [_build_slide1_frame(stat, headline, sub, bg, glow_r=r)
            for r in [8, 20, 32, 20]]


# ── 슬라이드 2: 상세 내용 ──────────────────────────────────────

def create_slide2(headline: str, points: list[str], bg: Image.Image) -> Image.Image:
    img = bg.copy()

    ov  = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od  = ImageDraw.Draw(ov)
    od.rectangle([0, 0, W, H], fill=(0, 0, 0, 178))
    for i in range(200):
        od.line([(0, i), (W, i)], fill=(15, 35, 90, int(35 * (1 - i / 200))))
    _dot_grid(od, alpha=8)
    img = Image.alpha_composite(img, ov)
    draw = ImageDraw.Draw(img)

    f_hl     = _font(bold=True,  size=50)
    f_point  = _font(bold=True,  size=30)
    f_num    = _font(bold=True,  size=24)
    f_sm     = _font(bold=False, size=22)
    f_xs     = _font(bold=False, size=18)

    # ─ 상단 진행 + 섹션 레이블 ─
    _progress_dots(draw, 2, 3, W // 2, 46)
    draw.text((54, 36), "왜 이런 일이?", font=f_xs, fill=(*GRAY, 175))

    # ─ 헤드라인 ─
    draw.rectangle([32, 86, 42, 152], fill=(*YELLOW, 210))
    wrapped_hl = wrap_text_by_pixels(headline, f_hl, W - 80, draw)
    for idx, line in enumerate(wrapped_hl[:2]):
        draw.text((58, 90 + idx * 62), line, font=f_hl, fill=(*YELLOW, 255))

    hl_bottom = 90 + len(wrapped_hl[:2]) * 62 + 12
    _accent_hline(draw, 32, hl_bottom, W - 32, BLUE)

    # ─ 3개 포인트 카드 ─
    pt_colors = [CYAN, YELLOW, GREEN]
    y_starts  = [hl_bottom + 32, hl_bottom + 210, hl_bottom + 388]
    BOX_H     = 162

    for i, (point, c, y) in enumerate(zip(points[:3], pt_colors, y_starts)):
        # 박스 배경 + 테두리
        _rounded_box(draw, [32, y, W - 32, y + BOX_H],
                     fill=(255, 255, 255, 9), outline=(*c[:3], 55), radius=12, width=1)
        # 왼쪽 색상 강조 바
        draw.rectangle([32, y, 42, y + BOX_H], fill=(*c[:3], 210))
        # 번호 배지
        _rounded_box(draw, [56, y + 20, 96, y + 60], fill=(*BLUE, 220), radius=8)
        bw = draw.textlength(str(i + 1), font=f_num)
        draw.text((76 - bw // 2, y + 27), str(i + 1), font=f_num, fill=(*WHITE, 255))
        # 포인트 메인 텍스트
        wrapped = wrap_text_by_pixels(point, f_point, W - 150, draw)
        for j, line in enumerate(wrapped[:2]):
            draw.text((108, y + 22 + j * 42), line, font=f_point, fill=(*WHITE, 240))
        # 아이콘 힌트 (오른쪽 하단)
        draw.text((W - 80, y + BOX_H - 28), "›", font=f_sm, fill=(*c[:3], 120))

    # ─ 하단 CTA ─
    bot_y = y_starts[-1] + BOX_H + 22
    draw.line([(32, bot_y), (W - 32, bot_y)], fill=(255, 255, 255, 30), width=1)
    draw.text((54, bot_y + 18), "마지막 슬라이드에서 결론 확인  ›", font=f_xs,
              fill=(*CYAN, 185))

    draw.text((54, H - 26), BRAND, font=f_xs, fill=(120, 125, 150, 130))

    return img.convert("RGB")


# ── 슬라이드 3: 핵심 요약 + CTA ────────────────────────────────

def _make_particle_bg() -> Image.Image:
    """파티클 + 미묘 그라데이션 배경 (프로그래밍 생성)"""
    img  = Image.new("RGBA", SLIDE_SIZE, (*DARK, 255))
    draw = ImageDraw.Draw(img)
    # 상단 청색 그라데이션
    for i in range(H):
        t = i / H
        b = int(60 * (1 - t) ** 1.5)
        draw.line([(0, i), (W, i)], fill=(6, 12, 8 + b, 255))
    # 파티클 점
    rng = random.Random(42)
    for _ in range(100):
        x, y   = rng.randint(0, W), rng.randint(0, H)
        size   = rng.choice([1, 1, 2, 2, 3])
        alpha  = rng.randint(25, 90)
        color  = rng.choice([CYAN, BLUE, WHITE, YELLOW, GREEN])
        draw.ellipse([x - size, y - size, x + size, y + size],
                     fill=(*color[:3], alpha))
    # 희미한 수평선들
    for _ in range(8):
        hy    = rng.randint(40, H - 80)
        alpha = rng.randint(10, 35)
        draw.line([(0, hy), (W, hy)], fill=(40, 70, 180, alpha), width=1)
    return img


def create_slide3(takeaway: str, cta_question: str, follow_cta: str) -> Image.Image:
    img  = _make_particle_bg()
    f_tw = _font(bold=True, size=58)
    img  = _glow_composite(img, takeaway, (42, 148), f_tw, YELLOW, radius=28)
    draw = ImageDraw.Draw(img)

    f_cta    = _font(bold=True,  size=38)
    f_follow = _font(bold=True,  size=30)
    f_sm     = _font(bold=False, size=24)
    f_xs     = _font(bold=False, size=18)

    # ─ 상단 ─
    _progress_dots(draw, 3, 3, W // 2, 46)
    _rounded_box(draw, [32, 80, 190, 118], fill=(*BLUE, 215), radius=8)
    draw.text((46, 87), "핵심 정리", font=f_xs, fill=(*WHITE, 255))

    # ─ Takeaway 텍스트 (글로우 위에 선명하게) ─
    wrapped_tw = wrap_text_by_pixels(takeaway, f_tw, W - 80, draw)
    y = 148
    for line in wrapped_tw[:3]:
        draw.text((42, y), line, font=f_tw, fill=(*YELLOW, 255))
        y += 74

    # ─ 구분선 ─
    div_y = y + 22
    _accent_hline(draw, 32, div_y, W - 32, BLUE)

    # ─ CTA 박스 ─
    cta_y = div_y + 30
    CTA_H = 205
    _rounded_box(draw, [32, cta_y, W - 32, cta_y + CTA_H],
                 fill=(18, 55, 150, 55), outline=(*BLUE, 145), radius=14, width=2)
    # 내부 상단 배지
    _rounded_box(draw, [52, cta_y + 16, 220, cta_y + 46],
                 fill=(*CYAN[:3], 55), radius=6)
    draw.text((62, cta_y + 22), "여러분의 생각은?", font=f_xs, fill=(*CYAN, 230))
    # CTA 질문
    wrapped_cta = wrap_text_by_pixels(cta_question, f_cta, W - 120, draw)
    cta_text_y  = cta_y + 60
    for line in wrapped_cta[:2]:
        draw.text((52, cta_text_y), line, font=f_cta, fill=(*WHITE, 250))
        cta_text_y += 58
    draw.text((52, cta_y + CTA_H - 30), "댓글로 알려주세요  ›", font=f_xs,
              fill=(*CYAN, 200))

    # ─ 팔로우 유도 ─
    fol_div_y = cta_y + CTA_H + 26
    draw.line([(32, fol_div_y), (W - 32, fol_div_y)], fill=(255, 255, 255, 25), width=1)
    fol_y = fol_div_y + 24
    draw.text((42, fol_y),      "▶  " + follow_cta,              font=f_follow,
              fill=(140, 190, 255, 215))
    draw.text((42, fol_y + 48), "매일 AI · 코인 · 증시 트렌드 업데이트", font=f_xs,
              fill=(*GRAY, 168))

    draw.text((54, H - 26), BRAND, font=f_xs, fill=(120, 125, 150, 130))

    return img.convert("RGB")


# ── 캐러셀 생성 파이프라인 ─────────────────────────────────────

def generate_carousel(content: dict) -> list[str]:
    """3장 캐러셀 생성 + 슬라이드1 GIF 저장 → Cloudinary URL 리스트 반환"""
    import pathlib

    s1 = content["slide1"]
    s2 = content["slide2"]
    s3 = content["slide3"]

    print("🎨 배경 이미지 생성 중... (DALL-E 3 HD)")
    bg = generate_background(s1["dalle_prompt"])

    print("🖼️  슬라이드 1/3: 훅 생성 중...")
    slide1 = create_slide1(s1["stat"], s1["headline"], s1["sub"], bg)

    print("🎞️  슬라이드 1 GIF 생성 중... (4프레임 글로우 펄싱)")
    gif_frames = create_slide1_gif(s1["stat"], s1["headline"], s1["sub"], bg)
    out_dir    = pathlib.Path("output")
    out_dir.mkdir(exist_ok=True)
    gif_path   = out_dir / "slide1_hook.gif"
    gif_frames[0].save(
        gif_path, save_all=True, append_images=gif_frames[1:],
        loop=0, duration=500, optimize=False,
    )
    print(f"  💾 GIF 저장: {gif_path}")

    print("🖼️  슬라이드 2/3: 상세 내용 생성 중...")
    slide2 = create_slide2(s2["headline"], s2["points"], bg)

    print("🖼️  슬라이드 3/3: CTA 생성 중...")
    slide3 = create_slide3(
        s3["takeaway"],
        s3["cta_question"],
        s3.get("follow_cta", "팔로우하면 매일 AI 소식!"),
    )

    print("☁️  Cloudinary 업로드 중...")
    urls = [
        upload_image(slide1),
        upload_image(slide2),
        upload_image(slide3),
    ]
    return urls


# ── 이미지 업로드 ─────────────────────────────────────────────

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
        timeout=60,
    )
    res.raise_for_status()
    url = res.json()["secure_url"]
    print(f"  ✅ 업로드 완료: {url}")
    return url
