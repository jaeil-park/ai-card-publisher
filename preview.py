"""
로컬 카드뉴스 미리보기 스크립트
- SNS 게시 없음 / Cloudinary 업로드 없음
- output/preview/ 폴더에 PNG + GIF 저장 후 자동으로 탐색기 오픈

실행:
    python preview.py                 # DALL-E 배경 + GPT 콘텐츠 실제 생성
    python preview.py --mock          # API 호출 없이 더미 데이터로 빠른 확인
"""

import argparse
import os
import pathlib
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

OUTPUT_DIR = pathlib.Path("output/preview")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 더미 콘텐츠 (--mock 모드) ───────────────────────────────
MOCK_FACTS = {
  "title": "AI와 금융의 미래를 바꿀 3가지 팩트 (Mock)",
  "points": [
    {
      "subtitle": "GPT-5, 인간 전문가 수준 초월 예측",
      "source": "arXiv"
    },
    {
      "subtitle": "Claude 3.5, 환각 현상 구조적 제어",
      "source": "Anthropic"
    },
    {
      "subtitle": "온체인 데이터 분석으로 상관관계 발견",
      "source": "CoinGecko"
    }
  ]
}


def run_mock():
    """API 호출 없이 더미 데이터로 HTML 렌더링"""
    from src.html_renderer import render_html_sync
    from PIL import Image, ImageDraw

    print("🧪 Mock 모드: API 호출 없이 더미 데이터로 HTML 렌더링")

    # 임시 단색 배경 생성
    bg_pil = Image.new("RGBA", (1080, 1350), (4, 5, 18))
    draw = ImageDraw.Draw(bg_pil)
    for y in range(1350):
        t = y / 1350
        v = int(58 * t * (1-t) * 4)
        draw.line([(0, y), (1080, y)], fill=(5+v//3, 10+v//2, 28+v, 255))
    
    bg_path = OUTPUT_DIR / "preview_mock_bg.png"
    bg_pil.save(bg_path)

    save_path = OUTPUT_DIR / "preview_html_mock.png"
    render_html_sync(MOCK_FACTS, bg_path, save_path)
    print(f"🖼️  미리보기 이미지 저장: {save_path}")


def run_real():
    """실제 API를 호출하여 HTML 렌더링 (SNS 게시 없음)"""
    from src.trend_fetcher import get_content_type, collect_data, CONTENT_META
    from src.content_generator import generate_facts
    from src.background_maker import generate_background
    from src.html_renderer import render_html_sync

    print("🚀 Real 모드: 실제 API를 호출하여 HTML 렌더링 (SNS 게시 없음)")
    content_type = get_content_type()
    meta         = CONTENT_META[content_type]
    print(f"{meta['emoji']} 콘텐츠 타입: {meta['label']}")

    data = collect_data(content_type)
    news_items = data.get("news", data.get("products", []))

    print("\n[1/3] 🤖 GPT-4o로 핵심 팩트 추출 중...")
    facts = generate_facts(theme=meta["label"], news=news_items)
    print(f"  ✅ 제목: {facts.get('title')}")

    print("\n[2/3] 🎨 배경 이미지 준비 중...")
    background_image_pil = generate_background(size=(1080, 1350))
    bg_path = OUTPUT_DIR / "preview_real_bg.png"
    background_image_pil.save(bg_path)

    print("\n[3/3] 🖼️  Playwright로 HTML 렌더링 및 스크린샷 중...")
    save_path = OUTPUT_DIR / "preview_html_real.png"
    render_html_sync(facts, bg_path, save_path)
    print(f"🖼️  미리보기 이미지 저장: {save_path}")


def open_output():
    """output/preview 폴더를 탐색기/파인더로 오픈"""
    import subprocess, platform
    p = str(OUTPUT_DIR.resolve())
    if platform.system() == "Windows":
        os.startfile(p)
    elif platform.system() == "Darwin":
        subprocess.run(["open", p])
    else:
        subprocess.run(["xdg-open", p])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="카드뉴스 로컬 미리보기")
    parser.add_argument("--mock", action="store_true",
                        help="API 없이 더미 데이터로 빠른 렌더링 확인")
    args = parser.parse_args()

    if args.mock:
        run_mock()
    else:
        run_real()

    print(f"\n✅ 저장 완료: {OUTPUT_DIR.resolve()}")
    open_output()
