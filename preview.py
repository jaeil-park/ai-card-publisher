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

from dotenv import load_dotenv
load_dotenv()

OUTPUT_DIR = pathlib.Path("output/preview")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 더미 콘텐츠 (--mock 모드) ───────────────────────────────
MOCK_CONTENT = {
    "slide1": {
        "stat":         "+39%",
        "headline":     "엔비디아 매출 집중",
        "sub":          "익명 고객 2곳에서 발생",
        "dalle_prompt": "Nvidia GPU data center server room, dark cinematic lighting, "
                        "photorealistic, blue neon glow",
    },
    "slide2": {
        "headline": "왜 이런 일이?",
        "points": [
            "AI 시장 경쟁 가열 — 빅테크 GPU 주문 급증",
            "TSMC 등 수혜 확산 — AI 반도체 공급망 전반",
            "익명 고객 2곳 집중 — 전체 매출의 39% 차지",
        ],
    },
    "slide3": {
        "takeaway":     "빅테크, AI 투자 집중도 높아진다.",
        "cta_question": "AI 시장의 향후 전망은?",
        "follow_cta":   "팔로우하면 매일 소식!",
    },
    "caption":  "AI 시장의 뜨거운 경쟁, 알고 계셨나요?",
    "hashtags": "#빅테크 #AI #엔비디아 #TSMC #AIThreads",
}


def run_mock():
    """API 호출 없이 더미 배경 + 더미 콘텐츠로 카드 생성"""
    from PIL import Image
    from src.card_generator import (
        create_slide1, create_slide1_gif,
        create_slide2, create_slide3,
    )

    print("🧪 Mock 모드: API 호출 없이 더미 데이터로 렌더링")

    # 단색 배경 (DALL-E 대체)
    bg = Image.new("RGBA", (1024, 1024), (12, 18, 40, 255))

    s1 = MOCK_CONTENT["slide1"]
    s2 = MOCK_CONTENT["slide2"]
    s3 = MOCK_CONTENT["slide3"]

    print("🖼️  슬라이드 1 생성 중...")
    slide1 = create_slide1(s1["stat"], s1["headline"], s1["sub"], bg)
    slide1.save(OUTPUT_DIR / "slide1.png")

    print("🎞️  슬라이드 1 GIF 생성 중...")
    frames = create_slide1_gif(s1["stat"], s1["headline"], s1["sub"], bg)
    frames[0].save(
        OUTPUT_DIR / "slide1_hook.gif",
        save_all=True, append_images=frames[1:],
        loop=0, duration=500, optimize=False,
    )

    print("🖼️  슬라이드 2 생성 중...")
    slide2 = create_slide2(s2["headline"], s2["points"], bg)
    slide2.save(OUTPUT_DIR / "slide2.png")

    print("🖼️  슬라이드 3 생성 중...")
    slide3 = create_slide3(s3["takeaway"], s3["cta_question"], s3["follow_cta"])
    slide3.save(OUTPUT_DIR / "slide3.png")


def run_real():
    """실제 API 호출 (DALL-E + GPT) — SNS 게시는 하지 않음"""
    from src.trend_fetcher import get_content_type, collect_data, generate_card_content, CONTENT_META
    from src.card_generator import (
        generate_background,
        create_slide1, create_slide1_gif,
        create_slide2, create_slide3,
    )

    content_type = get_content_type()
    meta         = CONTENT_META[content_type]
    print(f"{meta['emoji']} 콘텐츠 타입: {meta['label']}")

    data   = collect_data(content_type)
    news   = data.get("news", data.get("products", data.get("tools_news", data.get("github", []))))
    crypto = data.get("crypto", [])
    content = generate_card_content(theme=meta["label"], news=news, crypto=crypto)

    s1 = content["slide1"]
    s2 = content["slide2"]
    s3 = content["slide3"]
    print(f"📝 stat={s1['stat']}  headline={s1['headline']}")

    print("🎨 DALL-E 배경 생성 중...")
    bg = generate_background(s1["dalle_prompt"])

    print("🖼️  슬라이드 1 생성 중...")
    slide1 = create_slide1(s1["stat"], s1["headline"], s1["sub"], bg)
    slide1.save(OUTPUT_DIR / "slide1.png")

    print("🎞️  슬라이드 1 GIF 생성 중...")
    frames = create_slide1_gif(s1["stat"], s1["headline"], s1["sub"], bg)
    frames[0].save(
        OUTPUT_DIR / "slide1_hook.gif",
        save_all=True, append_images=frames[1:],
        loop=0, duration=500, optimize=False,
    )

    print("🖼️  슬라이드 2 생성 중...")
    slide2 = create_slide2(s2["headline"], s2["points"], bg)
    slide2.save(OUTPUT_DIR / "slide2.png")

    print("🖼️  슬라이드 3 생성 중...")
    slide3 = create_slide3(s3["takeaway"], s3["cta_question"],
                            s3.get("follow_cta", "팔로우하면 매일 AI 소식!"))
    slide3.save(OUTPUT_DIR / "slide3.png")


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
    print("   slide1.png / slide1_hook.gif / slide2.png / slide3.png")
    open_output()
