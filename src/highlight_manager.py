"""
Instagram 하이라이트 카테고리 관리
────────────────────────────────────────────────────────────
Instagram Graph API는 하이라이트 직접 생성을 지원하지 않으므로
(Stories 업로드 → 앱에서 하이라이트 추가 필요),
이 모듈은:
  1. 콘텐츠 타입 → 하이라이트 카테고리 매핑
  2. 9:16 Story 커버 이미지 자동 생성 (output/story_covers/)
  3. 하이라이트별 포스팅 현황 조회

추천 인스타그램 하이라이트 구성:
  ┌───────────────────────────────────────────────────────┐
  │  🤖 OpenAI   │  🧬 Claude AI  │  📈 CoinGecko        │
  │  🧠 AI툴     │  ☕ 바이브코딩  │  📊 마켓             │
  └───────────────────────────────────────────────────────┘
"""

import os
import platform
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

STORY_W, STORY_H = 1080, 1920
STORY_DIR = Path("output/story_covers")
STORY_DIR.mkdir(parents=True, exist_ok=True)

FONTS_DIR = Path("fonts")
_EMOJI_FONT_PATH = r"C:\Windows\Fonts\seguiemj.ttf"
BRAND = "HaeWooSo  |  @jaeil.park"

# ──────────────────────────────────────────────────────────
# 콘텐츠 타입 → 하이라이트 카테고리 매핑
# ──────────────────────────────────────────────────────────
HIGHLIGHT_MAP: dict[str, str] = {
    # 기존 콘텐츠 타입
    "morning_briefing": "AI툴",
    "bigtech_news":     "AI툴",
    "startup_trend":    "AI툴",
    "product_hunt":     "AI툴",
    "ai_tips":          "AI툴",
    "vibe_coding":      "바이브코딩",
    "weekly_review":    "AI툴",
    "market_update":    "마켓",
    # 새 브랜드 스포트라이트
    "openai_spotlight": "OpenAI",
    "claude_spotlight": "Claude AI",
    "coingecko_report": "CoinGecko",
}

# 하이라이트별 테마 색상 (RGB)
HIGHLIGHT_THEME: dict[str, dict] = {
    "OpenAI":    {"bg": (16,  16,  16), "accent": (16, 163, 127), "emoji": "🤖"},
    "Claude AI": {"bg": (12,   8,  28), "accent": (198, 120, 221), "emoji": "🧬"},
    "CoinGecko": {"bg": ( 5,  20,  10), "accent": (55,  200,  80), "emoji": "📈"},
    "AI툴":      {"bg": ( 8,  14,  32), "accent": (40,  120, 255), "emoji": "🧠"},
    "바이브코딩": {"bg": (20,  12,   8), "accent": (255, 160,  40), "emoji": "☕"},
    "마켓":      {"bg": ( 8,  20,  16), "accent": (30,  210, 160), "emoji": "📊"},
}

_DEFAULT_THEME = {"bg": (8, 12, 28), "accent": (80, 80, 80), "emoji": "📌"}


def get_highlight(content_type: str) -> str:
    """콘텐츠 타입의 하이라이트 카테고리 반환"""
    return HIGHLIGHT_MAP.get(content_type, "AI툴")


def _load_font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    """Pretendard 우선, 없으면 OS 내장 한글 폰트 사용"""
    pretendard = (FONTS_DIR / ("Pretendard-Bold.otf" if bold else "Pretendard-Regular.otf"))
    candidates = [str(pretendard)] if pretendard.exists() else []

    s = platform.system()
    if s == "Windows":
        b = "malgunbd.ttf" if bold else "malgun.ttf"
        candidates += [f"C:\\Windows\\Fonts\\{b}", "C:\\Windows\\Fonts\\arial.ttf"]
    elif s == "Linux":
        b = "NanumGothicBold.ttf" if bold else "NanumGothic.ttf"
        candidates += [f"/usr/share/fonts/truetype/nanum/{b}"]
    else:
        candidates += ["/System/Library/Fonts/AppleSDGothicNeo.ttc"]

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


_emoji_cache: dict[int, ImageFont.FreeTypeFont | None] = {}


def _emoji_font(size: int) -> ImageFont.FreeTypeFont | None:
    """Segoe UI Emoji (Windows built-in) — 컬러 이모지 렌더링"""
    if size in _emoji_cache:
        return _emoji_cache[size]
    p = Path(_EMOJI_FONT_PATH)
    if not p.exists():
        _emoji_cache[size] = None
        return None
    try:
        f = ImageFont.truetype(str(p), int(size * 0.82))
        _emoji_cache[size] = f
        return f
    except Exception:
        _emoji_cache[size] = None
        return None


def _draw_text_emoji(draw: ImageDraw.Draw, xy: tuple, text: str,
                     font: ImageFont.FreeTypeFont, fill=(255, 255, 255)) -> int:
    """이모지 혼합 텍스트 렌더링 → 렌더링된 총 폭 반환"""
    x, y = xy
    ef = _emoji_font(font.size)
    sx = x
    for ch in text:
        cp = ord(ch)
        if cp == 0xFE0F:       # 변환 선택자 건너뜀
            continue
        is_em = (0x1F000 <= cp <= 0x1FFFF or 0x2600 <= cp <= 0x27BF
                 or 0x2B00 <= cp <= 0x2BFF)
        if is_em and ef:
            ey = y + (font.size - ef.size) // 2
            try:
                draw.text((x, ey), ch, font=ef, embedded_color=True)
            except Exception:
                pass
            x += int(ef.getlength(ch)) + 2
        else:
            draw.text((x, y), ch, font=font, fill=fill)
            x += int(font.getlength(ch))
    return x - sx


def create_story_cover(
    feed_card: Image.Image,
    content_type: str,
    title: str = "",
    save_path: Path | None = None,
) -> Image.Image:
    """
    피드 카드(1080×1080)를 Story 커버(1080×1920)로 변환.

    레이아웃:
      ┌─────────────────────┐  ← 1080×1920
      │  상단 여백 + 배지    │  y=0~160
      │  피드 카드 (정방형)  │  y=200~1280  (1080px)
      │  제목 요약           │  y=1310~1500
      │  "피드에서 더 보기 →"│  y=1550~1620
      │  하단 브랜드         │  y=1860~1900
      └─────────────────────┘
    """
    theme = HIGHLIGHT_THEME.get(get_highlight(content_type), _DEFAULT_THEME)

    # 배경
    img = Image.new("RGBA", (STORY_W, STORY_H), (*theme["bg"], 255))
    draw = ImageDraw.Draw(img)

    # 상단 그라데이션 밴드
    for y in range(200):
        t = 1 - y / 200
        a = int(80 * t)
        draw.line([0, y, STORY_W, y], fill=(*theme["accent"], a))

    # 하이라이트 카테고리 배지 (상단 중앙) — 이모지 렌더링 적용
    hl = get_highlight(content_type)
    badge_text = f"{theme['emoji']}  {hl}"
    bf = _load_font(True, 36)
    # 이모지 포함 폭 측정 (이모지 폰트 기준)
    ef = _emoji_font(36)
    bw = sum(
        int((ef or bf).getlength(c)) + (2 if ef else 0)
        if (0x1F000 <= ord(c) <= 0x1FFFF or 0x2600 <= ord(c) <= 0x27BF) and ef
        else int(bf.getlength(c))
        for c in badge_text if ord(c) != 0xFE0F
    ) + 40
    bx = (STORY_W - bw) // 2
    draw.rounded_rectangle([bx, 60, bx + bw, 120], radius=30,
                            fill=(*theme["accent"], 200))
    _draw_text_emoji(draw, (bx + 20, 72), badge_text, bf, fill=(255, 255, 255))

    # 피드 카드 붙여넣기 (상단 y=180)
    card_rgb = feed_card.convert("RGBA").resize((STORY_W, STORY_W), Image.LANCZOS)
    img.paste(card_rgb, (0, 180), card_rgb)

    # 제목 요약
    if title:
        tf = _load_font(True, 44)
        max_w = STORY_W - 80
        # 줄바꿈
        words = title
        lines = []
        cur = ""
        for ch in words:
            test = cur + ch
            if draw.textlength(test, font=tf) <= max_w:
                cur = test
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)

        y_t = 1310
        for line in lines[:2]:
            lw = int(draw.textlength(line, font=tf))
            draw.text(((STORY_W - lw) // 2, y_t), line, font=tf,
                      fill=(255, 255, 255, 230))
            y_t += 60

    # "피드에서 더 보기 →" CTA
    cta_f = _load_font(False, 34)
    cta_text = "피드에서 자세히 보기  →"
    cta_w = int(draw.textlength(cta_text, font=cta_f))
    draw.text(((STORY_W - cta_w) // 2, 1570),
              cta_text, font=cta_f, fill=(*theme["accent"], 230))

    # 하단 구분선 + 브랜드 (HaeWooSo | @jaeil.park)
    draw.line([40, 1860, STORY_W - 40, 1860], fill=(80, 80, 100, 80), width=1)
    brand_f = _load_font(False, 28)
    bw2 = int(draw.textlength(BRAND, font=brand_f))
    draw.text(((STORY_W - bw2) // 2, 1875), BRAND, font=brand_f,
              fill=(130, 140, 160, 160))

    result = img.convert("RGB")

    if save_path is None:
        safe = content_type.replace("/", "_")
        save_path = STORY_DIR / f"story_{safe}.jpg"
    result.save(save_path, format="JPEG", quality=92)
    print(f"  📱 Story 커버 저장: {save_path}")

    return result


def print_highlight_guide(content_type: str, post_title: str = ""):
    """포스팅 후 하이라이트 안내 출력"""
    hl = get_highlight(content_type)
    theme = HIGHLIGHT_THEME.get(hl, _DEFAULT_THEME)
    print(
        f"\n  {'─'*50}\n"
        f"  {theme['emoji']} Instagram 하이라이트 추가 안내\n"
        f"  {'─'*50}\n"
        f"  카테고리:  [{hl}]\n"
        f"  포스트:    {post_title or content_type}\n"
        f"  Story 커버: output/story_covers/story_{content_type}.jpg\n"
        f"\n  [추가 방법]\n"
        f"  1. 위 Story 커버 파일을 Instagram Story로 업로드\n"
        f"  2. 스토리 → 하이라이트 [{hl}]에 추가\n"
        f"     (해당 하이라이트가 없으면 '새 하이라이트'로 생성)\n"
        f"  {'─'*50}\n"
    )


def list_highlights_from_analytics(posts: list[dict]) -> dict[str, list[dict]]:
    """analytics posts 리스트를 하이라이트 카테고리별로 그루핑"""
    grouped: dict[str, list[dict]] = {}
    for post in posts:
        hl = HIGHLIGHT_MAP.get(post.get("content_type", ""), "AI툴")
        grouped.setdefault(hl, []).append(post)
    return grouped


def print_highlights_summary(posts: list[dict]):
    """하이라이트별 포스팅 현황 콘솔 출력"""
    grouped = list_highlights_from_analytics(posts)
    print("\n  ══ Instagram 하이라이트별 콘텐츠 현황 ══")
    for hl, items in sorted(grouped.items()):
        theme = HIGHLIGHT_THEME.get(hl, _DEFAULT_THEME)
        print(f"\n  {theme['emoji']} [{hl}]  ({len(items)}개)")
        for p in sorted(items, key=lambda x: x.get("posted_at", ""), reverse=True)[:5]:
            ts = p.get("posted_at", "")[:10]
            title = p.get("title", "")[:30]
            plat  = p.get("platform", "")
            print(f"     {ts}  {plat:>10s}  {title}")
    print()
