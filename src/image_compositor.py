import os
import platform
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import base64
import hashlib
import time
import requests
from io import BytesIO

# ── Constants & Colors ─────────────────────────────────────────
W, H = 1080, 1920
PAD = 60
WHITE = (255, 255, 255)
CYAN = (0, 220, 255)
GOLD = (255, 215, 0)
STEEL = (130, 145, 170)
FONTS_DIR = Path("fonts")

# ── Font System ────────────────────────────────────────────────
_fcache: dict = {}

def _get_font_path(weight: str) -> str | None:
    """Finds a suitable Korean font path."""
    mapping = {"bold": "Pretendard-Bold.otf", "regular": "Pretendard-Regular.otf"}
    p = FONTS_DIR / mapping.get(weight, "Pretendard-Regular.otf")
    if p.exists(): return str(p)

    s = platform.system()
    if s == "Linux":
        name = "NanumGothicBold.ttf" if weight == "bold" else "NanumGothic.ttf"
        p = Path(f"/usr/share/fonts/truetype/nanum/{name}")
        return str(p) if p.exists() else None
    if s == "Windows":
        name = "malgunbd.ttf" if weight == "bold" else "malgun.ttf"
        p = Path(f"C:/Windows/Fonts/{name}")
        return str(p) if p.exists() else None
    return None

def _load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    key = (weight, size)
    if key in _fcache: return _fcache[key]
    path = _get_font_path(weight)
    if path:
        try:
            f = ImageFont.truetype(path, size)
            _fcache[key] = f
            return f
        except Exception: pass
    return ImageFont.load_default()

def fb(sz): return _load_font("bold", sz)
def fr(sz): return _load_font("regular", sz)

# ── Drawing Helpers ────────────────────────────────────────────
def wrap_text(text: str, font, max_w: int, draw: ImageDraw.Draw) -> list[str]:
    lines = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            test = cur + ch
            w = draw.textlength(test, font=font)
            if w <= max_w: cur = test
            else:
                if cur: lines.append(cur)
                cur = ch
        if cur: lines.append(cur)
    return lines

def draw_glass_panel(draw, bbox, radius=20, fill=(15, 20, 40, 180), outline=CYAN, width=2):
    x0, y0, x1, y1 = bbox
    cropped_bg = draw.im.crop(bbox)
    blurred_bg = cropped_bg.filter(ImageFilter.GaussianBlur(15))
    
    panel_mask = Image.new("L", (x1 - x0, y1 - y0), 0)
    mask_draw = ImageDraw.Draw(panel_mask)
    mask_draw.rounded_rectangle((0, 0, x1 - x0, y1 - y0), radius=radius, fill=255)
    
    draw.im.paste(blurred_bg, bbox, mask=panel_mask)
    draw.rounded_rectangle(bbox, radius=radius, outline=outline, width=width)

# ── Main Compositor ────────────────────────────────────────────
def compose_image(bg_image: Image.Image, facts: dict) -> Image.Image:
    img = bg_image.copy().convert("RGBA")
    draw = ImageDraw.Draw(img)

    title_font = fb(64)
    title_text = facts.get("title", "AI-FinTech 핵심 동향")
    wrapped_title = wrap_text(title_text, title_font, W - PAD * 2, draw)
    y_cursor = 160
    for line in wrapped_title:
        tw = draw.textlength(line, font=title_font)
        draw.text(((W - tw) / 2, y_cursor), line, font=title_font, fill=WHITE)
        y_cursor += title_font.size + 15
    y_cursor += 40

    panel_w, panel_h, panel_gap = W - PAD * 2, 380, 30
    subtitle_font, content_font, source_font = fb(36), fr(30), fr(24)

    for point in facts.get("points", [])[:3]:
        bbox = (PAD, y_cursor, PAD + panel_w, y_cursor + panel_h)
        draw_glass_panel(draw, bbox, outline=CYAN)

        inner_pad, text_x, text_y, text_w = 30, PAD + 30, y_cursor + 30, panel_w - 60

        draw.text((text_x, text_y), point.get("subtitle", ""), font=subtitle_font, fill=WHITE)
        text_y += subtitle_font.size + 20

        wrapped_content = wrap_text(point.get("content", ""), content_font, text_w, draw)
        for line in wrapped_content:
            draw.text((text_x, text_y), line, font=content_font, fill=WHITE)
            text_y += content_font.size + 10
        
        source = f"출처: {point.get('source', '')}"
        sw = draw.textlength(source, font=source_font)
        draw.text((PAD + panel_w - inner_pad - sw, y_cursor + panel_h - inner_pad - source_font.size),
                  source, font=source_font, fill=STEEL)
        y_cursor += panel_h + panel_gap

    brand_font = fr(28)
    brand_text = "Gems  |  @gems.official"
    bw = draw.textlength(brand_text, font=brand_font)
    draw.text(((W - bw) / 2, H - 80), brand_text, font=brand_font, fill=STEEL)

    print("✅ 이미지 합성 완료")
    return img.convert("RGB")

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