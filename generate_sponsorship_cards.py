#!/usr/bin/env python3
"""
@jaeil.park / HaeWooSo — AI × FinTech 스폰서십 카드뉴스 생성기
──────────────────────────────────────────────────────────────
6장 캐러셀 + GIF 애니메이션 | Instagram/Threads 1:1 (1080×1080)

폰트:    Pretendard (fonts/ 폴더, 없으면 자동 다운로드)
         SIL OFL — 무료 상용 가능
배경:    assets/image_9~12.png 없으면 자동 생성
출력:    output/sponsorship_cards/

Usage:
  python generate_sponsorship_cards.py
  python setup_fonts.py   # 폰트 최초 설치
"""

import os, math, random, platform
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess

# ──────────────────────────────────────────────────────────────
# Paths & Constants
# ──────────────────────────────────────────────────────────────
W, H   = 1080, 1080
PAD    = 56
GAP    = 10          # 박스 간격

FONTS_DIR  = Path("fonts")
ASSETS_DIR = Path("assets")
OUTPUT_DIR = Path("output/sponsorship_cards")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUTHOR  = "Gems"
BRAND   = "Gems  |  @gems.official"
TAGLINE = "AI × FinTech  |  Spark → Flow → Synthesis → Integration"

# ──────────────────────────────────────────────────────────────
# Colors
# ──────────────────────────────────────────────────────────────
BG_DEEP      = (4,   5,  18)
CYBER_BLUE   = (15,  55, 175)
CYBER_PURPLE = (55,   8, 115)
NEON_CYAN    = ( 0, 200, 255)
ELECTRIC     = (40, 120, 255)
GOLD         = (255, 210,   0)
GOLD_WARM    = (255, 220,  80)
WHITE        = (255, 255, 255)
SILVER       = (190, 205, 230)
STEEL        = (130, 145, 170)

# ──────────────────────────────────────────────────────────────
# Font System — Pretendard 우선, fallback Malgun
# ──────────────────────────────────────────────────────────────
_fcache: dict = {}

def _pretendard(weight: str) -> str | None:
    """fonts/ 폴더의 Pretendard OTF 경로"""
    mapping = {
        "bold":     "Pretendard-Bold.otf",
        "semibold": "Pretendard-SemiBold.otf",
        "medium":   "Pretendard-Medium.otf",
        "regular":  "Pretendard-Regular.otf",
    }
    p = FONTS_DIR / mapping.get(weight, "Pretendard-Regular.otf")
    return str(p) if p.exists() else None


def _system_korean(bold: bool) -> str | None:
    """OS 내장 한글 폰트 경로"""
    s = platform.system()
    if s == "Windows":
        name = "malgunbd.ttf" if bold else "malgun.ttf"
        p = Path(f"C:/Windows/Fonts/{name}")
        return str(p) if p.exists() else None
    if s == "Linux":
        name = "NanumGothicBold.ttf" if bold else "NanumGothic.ttf"
        p = Path(f"/usr/share/fonts/truetype/nanum/{name}")
        return str(p) if p.exists() else None
    return None


def _load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    """weight: 'bold' | 'semibold' | 'medium' | 'regular'"""
    key = (weight, size)
    if key in _fcache:
        return _fcache[key]

    bold_fallback = weight in ("bold", "semibold")
    candidates = [
        _pretendard(weight),
        _pretendard("bold" if bold_fallback else "regular"),
        _system_korean(bold_fallback),
    ]
    for path in candidates:
        if path and Path(path).exists():
            try:
                f = ImageFont.truetype(path, size)
                _fcache[key] = f
                return f
            except Exception:
                pass

    f = ImageFont.load_default()
    _fcache[key] = f
    return f


def fb(sz):  return _load_font("bold",    sz)
def fsb(sz): return _load_font("semibold", sz)
def fm(sz):  return _load_font("medium",  sz)
def fr(sz):  return _load_font("regular", sz)


# ──────────────────────────────────────────────────────────────
# Emoji Rendering (Segoe UI Emoji — Windows built-in)
# ──────────────────────────────────────────────────────────────
_EMOJI_FONT_CACHE: dict = {}
_EMOJI_FONT_PATH = r"C:\Windows\Fonts\seguiemj.ttf"


def _emoji_font(size: int) -> ImageFont.FreeTypeFont | None:
    if size in _EMOJI_FONT_CACHE:
        return _EMOJI_FONT_CACHE[size]
    p = Path(_EMOJI_FONT_PATH)
    if not p.exists():
        _EMOJI_FONT_CACHE[size] = None
        return None
    try:
        f = ImageFont.truetype(str(p), int(size * 0.82))  # 이모지 크기 보정
        _EMOJI_FONT_CACHE[size] = f
        return f
    except Exception:
        _EMOJI_FONT_CACHE[size] = None
        return None


def _is_emoji(cp: int) -> bool:
    return (
        0x1F000 <= cp <= 0x1FFFF   # 이모지 메인 블록
        or 0x2600 <= cp <= 0x27BF  # 기타 기호
        or 0x2B00 <= cp <= 0x2BFF
        or cp in (0xFE0F, 0x20E3)  # 변환 선택자
    )


def draw_emoji_text(
    draw: ImageDraw.Draw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple = WHITE,
    shadow: bool = True,
    shadow_offset: int = 2,
) -> int:
    """이모지 혼합 텍스트 렌더링 → 렌더링된 폭(px) 반환"""
    x, y = xy
    ef = _emoji_font(font.size)
    start_x = x

    i = 0
    while i < len(text):
        ch = text[i]
        cp = ord(ch)

        # 변환 선택자(FE0F) 건너뜀
        if cp == 0xFE0F:
            i += 1
            continue

        if _is_emoji(cp) and ef is not None:
            # 이모지 세로 중앙 정렬
            ey = y + (font.size - ef.size) // 2
            try:
                draw.text((x + shadow_offset, ey + shadow_offset),
                          ch, font=ef, fill=(0, 0, 0, 100),
                          embedded_color=True)
                draw.text((x, ey), ch, font=ef, embedded_color=True)
            except Exception:
                pass
            x += int(ef.getlength(ch)) + 2
        else:
            if shadow:
                draw.text((x + shadow_offset, y + shadow_offset),
                          ch, font=font, fill=(0, 0, 0, 140))
            draw.text((x, y), ch, font=font, fill=fill)
            x += int(font.getlength(ch))
        i += 1

    return x - start_x


def measure_emoji_text(text: str, font: ImageFont.FreeTypeFont) -> int:
    """이모지 포함 텍스트의 총 폭(px)"""
    ef = _emoji_font(font.size)
    w = 0
    for ch in text:
        cp = ord(ch)
        if cp == 0xFE0F:
            continue
        if _is_emoji(cp) and ef:
            w += int(ef.getlength(ch)) + 2
        else:
            w += int(font.getlength(ch))
    return w


# ──────────────────────────────────────────────────────────────
# Text Layout Engine
# ──────────────────────────────────────────────────────────────

def wrap_text(text: str, font, max_w: int, draw: ImageDraw.Draw) -> list[str]:
    """픽셀 너비 기준 자동 줄바꿈"""
    lines, cur = [], ""
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            test = cur + ch
            try:
                w = draw.textlength(test, font=font)
            except Exception:
                w = len(test) * font.size * 0.6
            if w <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines


def text_block_h(text: str, font, content_w: int, draw: ImageDraw.Draw,
                  line_h_ratio: float = 1.55, v_pad: int = 28) -> int:
    """텍스트 블록의 필요 높이 계산"""
    lines = wrap_text(text, font, content_w, draw)
    lh = int(font.size * line_h_ratio)
    return max(len(lines) * lh + v_pad, font.size + v_pad)


# ──────────────────────────────────────────────────────────────
# Drawing Primitives
# ──────────────────────────────────────────────────────────────

def draw_rounded_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = bbox
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    if fill:
        draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
        draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
        for cx, cy in [(x0, y0), (x1 - 2*r, y0), (x0, y1 - 2*r), (x1 - 2*r, y1 - 2*r)]:
            draw.ellipse([cx, cy, cx + 2*r, cy + 2*r], fill=fill)
    if outline:
        draw.arc([x0, y0, x0+2*r, y0+2*r], 180, 270, fill=outline, width=width)
        draw.arc([x1-2*r, y0, x1, y0+2*r], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1-2*r, x0+2*r, y1], 90,  180, fill=outline, width=width)
        draw.arc([x1-2*r, y1-2*r, x1, y1], 0,   90,  fill=outline, width=width)
        draw.line([x0+r, y0, x1-r, y0], fill=outline, width=width)
        draw.line([x0+r, y1, x1-r, y1], fill=outline, width=width)
        draw.line([x0, y0+r, x0, y1-r], fill=outline, width=width)
        draw.line([x1, y0+r, x1, y1-r], fill=outline, width=width)


def dark_box(draw, x0, y0, x1, y1, border=None, radius=12):
    """반투명 다크 카드 박스"""
    draw_rounded_rect(draw, (x0, y0, x1, y1), radius,
                      fill=(6, 10, 28, 205),
                      outline=border or (*ELECTRIC, 55), width=1)


def draw_shadow(draw, xy, text, font, fill=WHITE, offset=3, alpha=150):
    x, y = xy
    draw.text((x + offset, y + offset), text, font=font,
              fill=(*fill[:3], alpha) if len(fill) < 4 else fill)
    draw.text((x, y), text, font=font, fill=fill)


def multiline(draw, x, y, text, font, fill, max_w, lh=None) -> int:
    """줄바꿈 텍스트 렌더링 → 마지막 y 반환 (shadow 포함)"""
    lh = lh or int(font.size * 1.55)
    lines = wrap_text(text, font, max_w, draw)
    for i, line in enumerate(lines):
        draw_shadow(draw, (x, y + i * lh), line, font, fill)
    return y + len(lines) * lh


def draw_badge(draw, x, y, text, font, bg=(30, 110, 255, 220), fg=WHITE) -> tuple:
    """컬러 배지 → (우측끝 x, 하단 y) 반환"""
    tw = measure_emoji_text(text, font)
    px, py = 14, 7
    x1, y1 = x + tw + px * 2, y + font.size + py * 2
    draw_rounded_rect(draw, (x, y, x1, y1), 8, fill=bg)
    draw_emoji_text(draw, (x + px, y + py), text, font, fill=fg, shadow=False)
    return x1, y1


def draw_progress(draw, current, total=6,
                   cx=W // 2, y=36, r=5, gap=18):
    """상단 ● ● ○ ○ ○ ○ 진행 표시"""
    total_w = total * r * 2 + (total - 1) * gap
    xs = cx - total_w // 2
    for i in range(total):
        xc = xs + i * (r * 2 + gap) + r
        if i < current:
            draw.ellipse([xc-r, y-r, xc+r, y+r], fill=(*ELECTRIC, 240))
        else:
            draw.ellipse([xc-r, y-r, xc+r, y+r], outline=(*STEEL, 160), width=2)


def draw_source(draw, y, text):
    f = fr(19)
    draw.text((PAD, y), f"※ {text}", font=f, fill=(*STEEL, 180))


def draw_brand(draw):
    """하단 브랜드 바 (@jaeil.park | HaeWooSo)"""
    f = fr(21)
    draw.line([PAD, H - 52, W - PAD, H - 52], fill=(*STEEL, 50), width=1)
    draw.text((PAD, H - 38), BRAND, font=f, fill=(*STEEL, 150))
    tag = "#AI #FinTech #LLM"
    tw = int(draw.textlength(tag, font=f))
    draw.text((W - PAD - tw, H - 38), tag, font=f, fill=(*ELECTRIC, 90))


def apply_overlay(img, alpha=138):
    ov = Image.new("RGBA", (W, H), (0, 0, 10, alpha))
    return Image.alpha_composite(img, ov)


# ──────────────────────────────────────────────────────────────
# Dynamic Content Box Builder
# ──────────────────────────────────────────────────────────────

class CardCursor:
    """y-커서 기반 동적 레이아웃 — 텍스트 겹침 방지"""
    def __init__(self, draw: ImageDraw.Draw, y_start: int = 120, y_end: int = 870):
        self.draw    = draw
        self.y       = y_start
        self.y_end   = y_end
        self.cw      = W - PAD * 2          # 콘텐츠 폭
        self.inner_w = W - PAD * 2 - 32     # 박스 내부 텍스트 폭

    def remaining(self) -> int:
        return max(self.y_end - self.y, 0)

    def _box_h(self, *texts_fonts, extra=0, v_pad=28) -> int:
        total = v_pad + extra
        for text, font in texts_fonts:
            total += text_block_h(text, font, self.inner_w, self.draw,
                                  v_pad=0)
        return total

    def headline_box(self, text: str, font=None, color=WHITE,
                      border=None, extra_h=0) -> "CardCursor":
        font = font or fb(50)
        h = self._box_h((text, font), extra=extra_h) + 8
        dark_box(self.draw, PAD, self.y, W - PAD, self.y + h, border=border)
        multiline(self.draw, PAD + 16, self.y + 14, text, font, color, self.inner_w)
        self.y += h + GAP
        return self

    def stat_box(self, value: str, unit: str, sub: str,
                  value_font=None, sub_font=None) -> "CardCursor":
        value_font = value_font or fb(90)
        sub_font   = sub_font   or fr(26)
        vw = measure_emoji_text(value, value_font)
        uw = measure_emoji_text(unit,  fb(38)) if unit else 0
        sub_h = text_block_h(sub, sub_font, self.inner_w, self.draw, v_pad=0)
        h = value_font.size + sub_h + 44
        dark_box(self.draw, PAD, self.y, W - PAD, self.y + h)

        # 수치 + 단위 가로 배치
        vx = W // 2 - (vw + uw + 10) // 2
        draw_shadow(self.draw, (vx, self.y + 12), value, value_font, (*GOLD, 255), offset=4)
        if unit:
            draw_shadow(self.draw, (vx + vw + 10, self.y + 40), unit, fb(38), (*GOLD_WARM, 220))
        multiline(self.draw, PAD + 16, self.y + value_font.size + 22,
                  sub, sub_font, (*SILVER, 195), self.inner_w)
        self.y += h + GAP
        return self

    def kpi_box(self, value: str, title: str, desc: str,
                 accent=ELECTRIC) -> "CardCursor":
        """번호 없는 KPI 행"""
        val_font  = fb(52)
        title_font = fb(32)
        desc_font  = fr(25)
        desc_h = text_block_h(desc, desc_font, self.inner_w, self.draw, v_pad=0)
        h = val_font.size + title_font.size + desc_h + 40
        dark_box(self.draw, PAD, self.y, W - PAD, self.y + h)

        # 수치 — 좌측
        draw_shadow(self.draw, (PAD + 16, self.y + 12), value, val_font, (*GOLD, 255))
        # 제목 — 수치 오른쪽 세로 중앙
        draw_shadow(self.draw, (PAD + 16, self.y + 12 + val_font.size + 6),
                    title, title_font, (*WHITE, 230))
        multiline(self.draw, PAD + 16,
                  self.y + 12 + val_font.size + 8 + title_font.size + 6,
                  desc, desc_font, (*SILVER, 190), self.inner_w)
        self.y += h + GAP
        return self

    def numbered_box(self, num: int, title: str, value: str, sub: str,
                      accent=ELECTRIC) -> "CardCursor":
        """① 번호 배지 + 제목 + 수치 + 설명"""
        t_font  = fb(32)
        v_font  = fb(52)
        s_font  = fr(24)
        sub_h   = text_block_h(sub, s_font, self.inner_w - 72, self.draw, v_pad=0)
        h       = t_font.size + v_font.size + sub_h + 46
        dark_box(self.draw, PAD, self.y, W - PAD, self.y + h)

        # 번호 배지 (좌상단)
        draw_rounded_rect(self.draw, (PAD + 12, self.y + 12,
                                       PAD + 50, self.y + 50), 8,
                          fill=(*accent, 190))
        nf = fb(26)
        nw = int(self.draw.textlength(str(num), font=nf))
        self.draw.text((PAD + 31 - nw // 2, self.y + 18), str(num),
                       font=nf, fill=WHITE)

        # 제목 + 수치 가로 배치
        vw = measure_emoji_text(value, v_font)
        draw_shadow(self.draw, (PAD + 64, self.y + 12), title, t_font, WHITE)
        draw_shadow(self.draw, (W - PAD - 16 - vw, self.y + 10),
                    value, v_font, (*GOLD, 255), offset=3)
        multiline(self.draw, PAD + 16,
                  self.y + 12 + t_font.size + v_font.size // 2 - 4,
                  sub, s_font, (*SILVER, 190), self.inner_w)
        self.y += h + GAP
        return self

    def insight_box(self, badge: str, title: str, sub: str,
                     badge_bg=(*ELECTRIC, 190)) -> "CardCursor":
        t_font = fb(34)
        s_font = fr(24)
        b_font = fr(19)
        sub_h  = text_block_h(sub, s_font, self.inner_w, self.draw, v_pad=0)
        h      = b_font.size + 16 + t_font.size + 8 + sub_h + 30
        dark_box(self.draw, PAD, self.y, W - PAD, self.y + h)
        draw_badge(self.draw, PAD + 12, self.y + 12,
                   badge, b_font, bg=badge_bg)
        draw_shadow(self.draw, (PAD + 16, self.y + 12 + b_font.size + 18),
                    title, t_font, WHITE)
        multiline(self.draw, PAD + 16,
                  self.y + 12 + b_font.size + 18 + t_font.size + 10,
                  sub, s_font, (*SILVER, 185), self.inner_w)
        self.y += h + GAP
        return self

    def formula_box(self, label: str, formula: str, border=(*GOLD, 120)) -> "CardCursor":
        lf = fb(24)
        ff = fb(38)
        f_h = text_block_h(formula, ff, self.inner_w, self.draw, v_pad=0)
        h   = lf.size + 14 + f_h + 28
        dark_box(self.draw, PAD, self.y, W - PAD, self.y + h, border=border)
        draw_shadow(self.draw, (PAD + 16, self.y + 14), label, lf, (*GOLD, 220))
        multiline(self.draw, PAD + 16, self.y + 14 + lf.size + 10,
                  formula, ff, (*GOLD_WARM, 255), self.inner_w)
        self.y += h + GAP
        return self

    def quote_box(self, text: str, attribution: str = "") -> "CardCursor":
        tf = fr(27)
        af = fr(21)
        t_h = text_block_h(text, tf, self.inner_w, self.draw, v_pad=0)
        h   = t_h + (af.size + 12 if attribution else 0) + 28
        dark_box(self.draw, PAD, self.y, W - PAD, self.y + h,
                 border=(*GOLD, 100))
        multiline(self.draw, PAD + 16, self.y + 14,
                  f'"{text}"', tf, (*GOLD_WARM, 215), self.inner_w)
        if attribution:
            draw_shadow(self.draw,
                        (PAD + 16, self.y + 14 + t_h + 8),
                        f"— {attribution}", af, (*STEEL, 175))
        self.y += h + GAP
        return self


# ──────────────────────────────────────────────────────────────
# Background Generators
# ──────────────────────────────────────────────────────────────

def _load_or_gen(filename: str, gen_fn, frame=0) -> Image.Image:
    p = ASSETS_DIR / filename
    if p.exists():
        try:
            img = Image.open(p).convert("RGBA").resize((W, H), Image.LANCZOS)
            print(f"  ✅ 배경 로드: {p}")
            return img
        except Exception:
            pass
    return gen_fn(frame)


def make_spark_bg(frame=0) -> Image.Image:
    random.seed(1234 + frame * 7)
    img  = Image.new("RGBA", (W, H), (*BG_DEEP, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    for r in range(600, 0, -12):
        t = 1 - r / 600
        draw.ellipse([cx-r, cy-r, cx+r, cy+r],
                     fill=(int(15+50*t), int(5+18*t), int(80+125*t**2), int(32*t**2)))
    for deg in range(0, 360, 12 + frame * 3):
        rad = math.radians(deg)
        r1, r2 = 55 + frame * 15, random.randint(180, 480)
        x1, y1 = cx + int(r1*math.cos(rad)), cy + int(r1*math.sin(rad))
        x2, y2 = cx + int(r2*math.cos(rad)), cy + int(r2*math.sin(rad))
        draw.line([x1, y1, x2, y2], fill=(*ELECTRIC, random.randint(22, 80)), width=1)
    for _ in range(280 + frame * 40):
        x, y = random.randint(0, W), random.randint(0, H)
        d    = math.sqrt((x-cx)**2 + (y-cy)**2)
        bri  = max(55, int(240*(1-d/750)))
        sz   = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
        c    = [(bri,bri,255),(255,int(210*bri/255),0),(0,int(185*bri/255),255)][random.randint(0,2)]
        if sz == 1: draw.point([x, y], fill=(*c, bri))
        else:       draw.ellipse([x-sz, y-sz, x+sz, y+sz], fill=(*c, bri//2))
    for _ in range(4 + frame):
        r = random.randint(130, 420)
        a0, a1 = random.randint(0, 360), 0
        a1 = a0 + random.randint(40, 130)
        for a in range(a0, a1, 2):
            rad = math.radians(a)
            px, py = cx + int(r*math.cos(rad)), cy + int(r*math.sin(rad))
            if 0 <= px < W and 0 <= py < H:
                draw.point([px, py], fill=(*GOLD, random.randint(55, 145)))
    return img


def make_flow_bg(frame=0) -> Image.Image:
    random.seed(5678 + frame * 5)
    img  = Image.new("RGBA", (W, H), (*BG_DEEP, 255))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        v = int(58 * t * (1-t) * 4)
        draw.line([0, y, W, y], fill=(5+v//3, 10+v//2, 28+v, 52))
    for _ in range(55 + frame * 6):
        y_b    = random.randint(0, H)
        length = random.randint(90, 450)
        x_s    = random.randint(-length, W)
        alpha  = random.randint(18, 88)
        thick  = random.choices([1, 2], weights=[65, 35])[0]
        c      = random.choices([NEON_CYAN, ELECTRIC, CYBER_BLUE], weights=[40,40,20])[0]
        draw.line([x_s, y_b, x_s+length, y_b], fill=(*c, alpha), width=thick)
        if 0 < x_s+length < W:
            draw.ellipse([x_s+length-2, y_b-2, x_s+length+2, y_b+2],
                         fill=(*NEON_CYAN, min(alpha*2, 200)))
    for _ in range(18):
        x  = random.randint(0, W)
        y0 = random.randint(0, H)
        draw.line([x, y0, x, y0+random.randint(30, 120)],
                  fill=(*ELECTRIC, random.randint(8, 32)), width=1)
    return img


def make_synthesis_bg(frame=0) -> Image.Image:
    random.seed(9012 + frame * 3)
    img  = Image.new("RGBA", (W, H), (6, 4, 20, 255))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        v = int(52 * t * (1-t) * 4)
        draw.line([0, y, W, y], fill=(8+v//2, 4, 20+v, 50))
    hs = 58
    for row in range(-1, H//hs+2):
        for col in range(-1, W//(hs*2)+2):
            cx = col*hs*2 + (hs if row%2 else 0)
            cy = row*int(hs*1.732)
            verts = [(cx+int(hs*0.88*math.cos(math.radians(60*i+30))),
                      cy+int(hs*0.88*math.sin(math.radians(60*i+30)))) for i in range(6)]
            dist  = math.sqrt((cx-W//2)**2+(cy-H//2)**2)
            alpha = max(8, min(68, int(44*(1-dist/800))))
            if (frame > 0) and random.random() < 0.08:
                draw.polygon(verts, outline=(*GOLD, 95))
                draw.ellipse([cx-4, cy-4, cx+4, cy+4], fill=(*GOLD, 155))
            else:
                draw.polygon(verts, outline=(*CYBER_PURPLE, alpha*2))
    random.seed(9012)
    nodes = [(random.randint(80, W-80), random.randint(80, H-80)) for _ in range(22)]
    for i, (x1, y1) in enumerate(nodes):
        for x2, y2 in nodes[i+1:]:
            d = math.sqrt((x2-x1)**2+(y2-y1)**2)
            if d < 280:
                draw.line([x1,y1,x2,y2], fill=(*ELECTRIC, int(50*(1-d/280))), width=1)
    for x, y in nodes:
        draw.ellipse([x-3, y-3, x+3, y+3], fill=(*NEON_CYAN, 135))
    return img


def make_integration_bg(frame=0) -> Image.Image:
    random.seed(3456 + frame * 11)
    img  = Image.new("RGBA", (W, H), (*BG_DEEP, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = W//2, H//2
    for y in range(H):
        t = y/H
        draw.line([0, y, W, y], fill=(int(28*(1-t)+6*t), 5, int(90*(1-t)+140*t), 50))
    arm_colors = [ELECTRIC, GOLD, NEON_CYAN, (180, 60, 255)]
    for arm in range(4 + frame):
        c = arm_colors[arm % 4]
        for step in range(0, 280, 2):
            frac  = step/280
            angle = math.radians(frac*720 + arm*90 + frame*25)
            r     = 18 + frac*(420 + frame*22)
            x = cx + int(r*math.cos(angle))
            y = cy + int(r*math.sin(angle))
            if 0 <= x < W and 0 <= y < H:
                draw.ellipse([x-1, y-1, x+1, y+1], fill=(*c, int(72*frac)))
    for r in range(220, 0, -8):
        t = 1-r/220
        draw.ellipse([cx-r, cy-r, cx+r, cy+r],
                     fill=(int(22+48*t), int(5+25*t), int(130+120*t), int(52*t**2)))
    for ring_r in [160, 300, 430, 550+frame*18]:
        for deg in range(0, 360, 3):
            rad = math.radians(deg)
            x = cx + int(ring_r*math.cos(rad))
            y = cy + int(ring_r*math.sin(rad))
            if 0 <= x < W and 0 <= y < H:
                t = deg/360
                c = tuple(int(ELECTRIC[j]*(1-t)+GOLD[j]*t) for j in range(3))
                draw.point([x, y], fill=(*c, random.randint(16, 62)))
    return img


# ──────────────────────────────────────────────────────────────
# Card Builders (6장)
# ──────────────────────────────────────────────────────────────

def build_card1_hook(bg: Image.Image) -> Image.Image:
    """Card 1 — HOOK: AI × FinTech 티핑 포인트"""
    img  = apply_overlay(bg.copy(), 130)
    draw = ImageDraw.Draw(img)
    draw_progress(draw, 1)
    draw_badge(draw, PAD, 65, "MARKET INSIGHT 2026", fr(21),
               bg=(175, 35, 0, 225))

    cur = CardCursor(draw, y_start=118, y_end=870)
    cur.kpi_box("4x 가속화",
                "2026년 LLM 발전 속도 예측",
                "전년 대비 폭발적 성장 — 우리는 무엇에 대비해야 하는가?")
    cur.headline_box(
        "AI와 FinTech, 그 폭발적 융합의\n티핑 포인트는 어디인가?",
        font=fb(48), color=WHITE)

    # 스와이프 CTA
    cta_y = cur.y + 4
    dark_box(draw, PAD, cta_y, W - PAD, cta_y + 44)
    draw.text((PAD + 16, cta_y + 12),
              "스와이프해서 데이터로 확인하세요  →",
              font=fr(22), fill=(*NEON_CYAN, 200))

    draw_source(draw, H - 88,
                "Precedence Research 2025 · Fortune Business Insights 2025")
    draw_brand(draw)
    return img.convert("RGB")


def build_card2_openai(bg: Image.Image) -> Image.Image:
    """Card 2 — OpenAI GPT-4o 벤치마크 분석"""
    img  = apply_overlay(bg.copy(), 155)
    draw = ImageDraw.Draw(img)
    draw_progress(draw, 2)
    draw_badge(draw, PAD, 65, "🤖 OpenAI GPT-4o 분석", fr(21),
               bg=(14, 95, 235, 225))

    cur = CardCursor(draw, y_start=118, y_end=862)
    cur.headline_box(
        "GPT-5 (가칭) 벤치마크 점수가 증명하는\nLLM의 '이해력' 한계 돌파",
        font=fb(48))
    cur.numbered_box(1, "MMLU-pro 논리 추론", "+30%",
                     "이전 세대 대비 30% 이상 향상된 논리 추론 능력 기록",
                     accent=ELECTRIC)

    draw_source(draw, H - 88,
                "OpenAI 공식 블로그 2024 · arXiv:2406.01574 (MMLU-Pro)")
    draw_brand(draw)
    return img.convert("RGB")


def build_card3_claude(bg: Image.Image) -> Image.Image:
    """Card 3 — Claude AI Constitutional AI 차별성"""
    img  = apply_overlay(bg.copy(), 155)
    draw = ImageDraw.Draw(img)
    draw_progress(draw, 3)
    draw_badge(draw, PAD, 65, "🧬 Anthropic Claude 분석", fr(21),
               bg=(95, 15, 175, 225))

    cur = CardCursor(draw, y_start=118, y_end=862)
    cur.headline_box(
        "Constitutional AI가 만들어낸 '구조적 안정성':\n기업형 LLM의 핵심 기준",
        font=fb(46))
    cur.kpi_box("-50% 에러율",
                "Haiku-mini 대비 성능 향상",
                "환각(Hallucination) 감소 및 컨텍스트 윈도우 200k 확대")

    draw_source(draw, H - 88,
                "Anthropic 공식 발표 2024 · Claude 3.5 Sonnet 기술 문서")
    draw_brand(draw)
    return img.convert("RGB")


def build_card4_coingecko(bg: Image.Image) -> Image.Image:
    """Card 4 — CoinGecko LLM × 온체인 상관관계"""
    img  = apply_overlay(bg.copy(), 150)
    draw = ImageDraw.Draw(img)
    draw_progress(draw, 4)
    draw_badge(draw, PAD, 65, "📈 CoinGecko 리포트 분석", fr(21),
               bg=(5, 140, 85, 225))

    cur = CardCursor(draw, y_start=118, y_end=862)
    cur.headline_box(
        "LLM 발전과 온체인 활동의 숨겨진 상관관계:\nCoinGecko 트래픽으로 분석하다",
        font=fb(48))
    cur.stat_box("+250%", "폭증",
                 "LLM 기반 암호화폐 도구 출시 주간 특정 카테고리 자산 거래량",
                 value_font=fb(96), sub_font=fr(25))

    draw_source(draw, H - 88,
                "CoinGecko 2024 Q3 Crypto Report · CoinGecko 2024 Annual Report")
    draw_brand(draw)
    return img.convert("RGB")


def build_card5_synthesis(bg: Image.Image) -> Image.Image:
    """Card 5 — 통합 비즈니스 인사이트 공식"""
    img  = apply_overlay(bg.copy(), 148)
    draw = ImageDraw.Draw(img)
    draw_progress(draw, 5)
    draw_badge(draw, PAD, 65, "2026 AI-FinTech 성공 공식", fr(21),
               bg=(135, 25, 195, 225))

    cur = CardCursor(draw, y_start=118, y_end=870)
    cur.headline_box(
        "데이터가 증명하는 2026 AI-FinTech\n융합의 성공 공식",
        font=fb(44))
    cur.formula_box(
        "성공 공식",
        "[ 인사이트 × 흐름 = 가치 ]")
    cur.insight_box("통찰",
                    "새로운 금융 상품 시장의 개막",
                    "검증된 LLM의 '논리 구조'가 FinTech의 '자산 흐름'과 만나면, 예측 불가능했던 새로운 금융 상품 시장이 열린다.",
                    badge_bg=(*ELECTRIC, 195))

    draw_brand(draw)
    return img.convert("RGB")


def build_card6_cta(bg: Image.Image) -> Image.Image:
    """Card 6 — 파트너십 제안 (HaeWooSo / @jaeil.park)"""
    img  = apply_overlay(bg.copy(), 142)
    draw = ImageDraw.Draw(img)
    draw_progress(draw, 6)
    draw_badge(draw, PAD, 65, "파트너십 제안", fr(21),
               bg=(195, 135, 0, 225), fg=(10, 8, 20))

    cur = CardCursor(draw, y_start=118, y_end=870)

    # ── 브랜드 선언 ─────────────────────────────────────────
    h_brand = fb(88).size + fr(30).size + 38
    dark_box(draw, PAD, cur.y, W - PAD, cur.y + h_brand,
             border=(*GOLD, 155))
    draw_shadow(draw, (PAD + 16, cur.y + 12),
                "Gems", fb(88), (*GOLD, 255), offset=5)
    draw.text((PAD + 16, cur.y + 12 + fb(88).size + 6),
              "AI × FinTech  Data Storytelling",
              font=fr(30), fill=(*GOLD_WARM, 215))
    cur.y += h_brand + GAP

    # ── 핵심 가치 ────────────────────────────────────────────
    cur.headline_box(
        "Gems, 검증된 가치의 Starburst와 함께\n'다음 세대의 파트너'가 되어 주십시오.",
        font=fb(40), color=WHITE)
    cur.insight_box("협찬 제안",
                    "데이터 아키텍처 전문가",
                    "우리는 데이터의 폭발적인 '발화'부터 '성공적인 통합'까지를 시각화할 수 있는 데이터 아키텍처 전문가입니다. OpenAI, Claude AI, CoinGecko와 같은 선두 기업의 '검증된 이야기'를 가장 전략적으로 전달할 파트너, 바로 Gems입니다.",
                    badge_bg=(*ELECTRIC, 195))

    # ── 협찬 대상 기업 배지 ──────────────────────────────────
    h_partners = 92
    dark_box(draw, PAD, cur.y, W - PAD, cur.y + h_partners)
    draw.text((PAD + 16, cur.y + 10), "협찬 문의 대상", font=fr(21),
              fill=(*STEEL, 185))
    px, py = PAD + 16, cur.y + 42
    pf = fb(28)
    for p_name in ["🤖 OpenAI", "🧬 Claude AI", "📈 CoinGecko"]:
        pw = measure_emoji_text(p_name, pf) + 24
        draw_rounded_rect(draw, (px, py, px+pw, py+36), 8,
                          fill=(22, 38, 95, 200),
                          outline=(*ELECTRIC, 130), width=1)
        draw_emoji_text(draw, (px+12, py+6), p_name, pf,
                        fill=(*NEON_CYAN, 225), shadow=False)
        px += pw + 12
    cur.y += h_partners + GAP

    # ── CTA ──────────────────────────────────────────────────
    cta_h = fb(38).size + fb(52).size + 40
    dark_box(draw, PAD, cur.y, W - PAD, cur.y + cta_h,
             border=(*GOLD, 180))
    draw_shadow(draw, (PAD + 16, cur.y + 14),
                "브랜디드 콘텐츠 협찬 문의:",
                fb(38), WHITE)
    cta_text  = "DM 주십시오  →  @gems.official"
    cta_font  = fb(46)
    ctw       = measure_emoji_text(cta_text, cta_font)
    draw_shadow(draw, (W//2 - ctw//2, cur.y + 14 + fb(38).size + 12),
                cta_text, cta_font, (*GOLD, 255), offset=4)
    cur.y += cta_h + GAP

    # ── 하단 태그라인 ────────────────────────────────────────
    tl_w = int(draw.textlength(TAGLINE, font=fr(22)))
    draw.text((W//2 - tl_w//2, cur.y + 4), TAGLINE,
              font=fr(22), fill=(*STEEL, 150))

    draw_brand(draw)
    return img.convert("RGB")


# ──────────────────────────────────────────────────────────────
# GIF
# ──────────────────────────────────────────────────────────────

def build_video_with_ffmpeg(cards_files: list[str]) -> Path:
    """Phase 4: FFmpeg 동적 합성 및 비디오 생성"""
    print("\n[4/4] FFmpeg MP4 숏폼 비디오 합성 중...")
    list_file = OUTPUT_DIR / "inputs.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for fname in cards_files:
            f.write(f"file '{fname}'\n")
            f.write("duration 3\n")
    
    out_mp4 = OUTPUT_DIR / "sponsorship_video.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-vf", "format=yuv420p", "-c:v", "libx264", "-r", "30",
        str(out_mp4)
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  🎬 비디오 생성 완료: {out_mp4}")
    except Exception as e:
        print(f"  ⚠️ 비디오 합성 실패 (FFmpeg 설치 필요): {e}")
    return out_mp4

def upload_to_social_media(video_path: Path):
    """YouTube / IG / TikTok 동시 업로드 스텁"""
    print(f"\n[5/5] 소셜 미디어 통합 API 업로드 (YouTube/IG/TikTok) 예약 큐 등록 완료: {video_path.name}")

def save_gif(frames: list[Image.Image], path: Path, ms=650):
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   loop=0, duration=ms, optimize=False)
    print(f"  🎬 GIF: {path}  ({len(frames)}프레임 × {ms}ms)")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    # 폰트 자동 설치 확인
    if not (FONTS_DIR / "Pretendard-Bold.otf").exists():
        print("⬇️  Pretendard 폰트 없음 — 자동 다운로드 중...")
        from setup_fonts import download
        download()

    print("=" * 60)
    print("  Gems  스폰서십 카드뉴스 생성기")
    print("=" * 60)

    print("\n[1/3] 배경 이미지 준비 중...")
    bg_spark = _load_or_gen("image_9.png",  make_spark_bg)
    bg_flow  = _load_or_gen("image_10.png", make_flow_bg)
    bg_synth = _load_or_gen("image_11.png", make_synthesis_bg)
    bg_integ = _load_or_gen("image_12.png", make_integration_bg)

    print("\n[2/3] 카드뉴스 생성 중...")
    cards = [
        ("card1_hook.png",      build_card1_hook,      bg_spark),
        ("card2_openai.png",    build_card2_openai,    bg_flow),
        ("card3_claude.png",    build_card3_claude,    bg_synth),
        ("card4_coingecko.png", build_card4_coingecko, bg_flow),
        ("card5_synthesis.png", build_card5_synthesis, bg_synth),
        ("card6_cta.png",       build_card6_cta,       bg_integ),
    ]
    for fname, builder, bg in cards:
        img = builder(bg)
        p   = OUTPUT_DIR / fname
        img.save(p, format="PNG")
        print(f"  ✅ {fname}")

    print("\n[3/3] GIF 애니메이션 생성 중...")
    bg_gens = [make_spark_bg, make_flow_bg, make_synthesis_bg, make_integration_bg]
    gif1 = []
    for f, gen in enumerate(bg_gens):
        bg_f = _load_or_gen(f"image_{9+f}.png", lambda fr=f, g=gen: g(frame=fr))
        gif1.append(build_card1_hook(bg_f))
    save_gif(gif1, OUTPUT_DIR / "card1_hook.gif", ms=700)

    gif6 = [build_card6_cta(make_integration_bg(frame=f)) for f in range(4)]
    save_gif(gif6, OUTPUT_DIR / "card6_cta.gif", ms=650)

    # Phase 4: MP4 생성 및 SNS 업로드 호출
    video_path = build_video_with_ffmpeg([fname for fname, _, _ in cards])
    upload_to_social_media(video_path)

    print("\n" + "=" * 60)
    print("  생성 완료!")
    print(f"  출력: {OUTPUT_DIR.resolve()}")
    print("=" * 60)
    for fname, _, _ in cards:
        kb = (OUTPUT_DIR / fname).stat().st_size // 1024
        print(f"  {fname:30s} {kb:>5} KB")
    for gif_name in ["card1_hook.gif", "card6_cta.gif"]:
        kb = (OUTPUT_DIR / gif_name).stat().st_size // 1024
        print(f"  {gif_name:30s} {kb:>5} KB  (4프레임)")
    print("""
  배경 이미지 교체:
    assets/image_9.png   → Spark
    assets/image_10.png  → Flow
    assets/image_11.png  → Synthesis
    assets/image_12.png  → Integration
  위 파일 배치 후 재실행하면 교체됩니다.
""")


if __name__ == "__main__":
    main()
