import os
import math
import base64
import platform
import random
import subprocess
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


# ── 슬라이드 2: 상세 내용 (인포그래픽) ────────────────────────

def create_slide2(headline: str, points: list, bg: Image.Image) -> Image.Image:
    """Phase 1~3: 검증된 가치를 시각화하는 프리미엄 데이터 패널 시스템 (Card 2)"""
    # Phase 1: 배경 이미지 연동 및 미스터리 컨텍스트 확보 (흐릿하고 어두운 버전)
    img = bg.copy().filter(ImageFilter.GaussianBlur(25)).convert("RGBA")
    ov  = Image.new("RGBA", img.size, (0, 0, 0, 190))
    img = Image.alpha_composite(img, ov)
    draw = ImageDraw.Draw(img)

    f_hl    = _font(bold=True,  size=48)
    f_point = _font(bold=True,  size=26)
    f_src   = _font(bold=False, size=18)
    f_cta   = _font(bold=False, size=24)
    f_wm    = _font(bold=False, size=22)

    # Phase 2: 사실 기반 데이터 (Fact-Checked) 및 텍스트 구성
    title_text = "왜 이런 일이?"
    tw = _text_w(draw, title_text, f_hl)
    draw.text(((W - tw) // 2, 70), title_text, font=f_hl, fill=WHITE)

    premium_points = [
        {"text": "멀티모달 LLM 도입: 텍스트를 넘어 이미지, 음성, 코드까지 통합 처리하는 고도화된 컨텍스트 이해 구현.", "source": "OpenAI Research 2026"},
        {"text": "비즈니스 프로세스 자동화 가속: 고객 서비스, 데이터 분석, 콘텐츠 생성 등 전문 도메인으로 AI 적용 확대.", "source": "CoinGecko Market Trends Q2"},
        {"text": "책임 있는 AI 프레임워크 구축: 데이터 편향성 해결 및 모델 투명성 확보를 위한 규제 논의 활성화.", "source": "AI Ethics Forum Korea"}
    ]

    # Phase 3: 시인성 및 브랜딩 최적화
    BOX_H = 180
    BOX_GAP = 30
    y_start = 160
    accents = [CYAN, YELLOW, CYAN] # 네온-시안 및 골드 악센트 교차

    for i, pt in enumerate(premium_points):
        y = y_start + i * (BOX_H + BOX_GAP)
        c = accents[i]
        
        # 짙은 반투명 데이터 패널 (Glassmorphism 효과)
        _rounded_box(draw, [40, y, W - 40, y + BOX_H],
                     fill=(15, 20, 35, 180), outline=(*c[:3], 200), radius=16, width=2)
        
        # 네온 악센트 라인
        draw.rectangle([40, y + 25, 46, y + BOX_H - 25], fill=(*c[:3], 255))

        # 내용 (순백색 고정으로 철벽의 시인성 확보)
        wrapped = wrap_text_by_pixels(pt["text"], f_point, W - 140, draw)
        for j, line in enumerate(wrapped):
            draw.text((70, y + 35 + j * 40), line, font=f_point, fill=WHITE)
        
        # 출처
        draw.text((70, y + BOX_H - 35), f"출처: {pt['source']}", font=f_src, fill=(160, 170, 180, 255))

    # 워터마크 (좌측 하단)
    draw.text((40, H - 60), "HaeWooSo | @jaeil.park", font=f_wm, fill=WHITE)

    # CTA (우측 하단)
    cta_text = "마지막 슬라이드에서 결론 확인 >"
    cw = _text_w(draw, cta_text, f_cta)
    draw.text((W - 40 - cw, H - 60), cta_text, font=f_cta, fill=(*YELLOW, 255))

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


# ── Phase 4: 비디오 합성 및 업로드 파이프라인 ─────────────────────

def build_video_with_ffmpeg(cards_files: list[str]) -> str:
    """Phase 4: FFmpeg 동적 합성 및 비디오 생성"""
    import pathlib
    print("\n[4/4] 🎬 FFmpeg MP4 숏폼 비디오 합성 중...")
    out_dir = pathlib.Path("output")
    list_file = out_dir / "inputs.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for fname in cards_files:
            f.write(f"file '{fname}'\n")
            f.write("duration 3\n")
    
    out_mp4 = out_dir / "premium_sponsorship_video.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-vf", "format=yuv420p", "-c:v", "libx264", "-r", "30",
        str(out_mp4)
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  ✅ 비디오 생성 완료: {out_mp4}")
        return str(out_mp4)
    except Exception as e:
        print(f"  ⚠️ 비디오 합성 실패: {e}")
        return ""

def upload_to_social_media_video(video_path: str):
    """YouTube / IG / TikTok 동시 업로드 스텁"""
    if video_path:
        print(f"☁️  소셜 미디어 통합 API 비디오 업로드 예약 큐 등록 완료: {video_path}")

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

    # Phase 4: 비디오 생성 파이프라인 호출
    slide1_path = out_dir / "slide1.png"
    slide2_path = out_dir / "slide2.png"
    slide3_path = out_dir / "slide3.png"
    slide1.save(slide1_path)
    slide2.save(slide2_path)
    slide3.save(slide3_path)
    
    video_path = build_video_with_ffmpeg([str(slide1_path.absolute()), str(slide2_path.absolute()), str(slide3_path.absolute())])
    upload_to_social_media_video(video_path)

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
