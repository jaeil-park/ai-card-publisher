import os
from dotenv import load_dotenv

load_dotenv()

from src.token_manager import check_and_refresh_tokens
from src.trend_fetcher import get_content_type, collect_data, generate_card_content, CONTENT_META
from src.card_generator import generate_carousel
from src.analytics import record_post, notify_posted
from src.poster import post_instagram_carousel, post_threads_carousel
from src.highlight_manager import (
    get_highlight, create_story_cover, print_highlight_guide,
)


def main():
    # 1. 토큰 만료 체크
    print("🔍 토큰 상태 확인 중...")
    check_and_refresh_tokens()

    # 2. 현재 시각 기준 콘텐츠 타입 자동 결정
    content_type = get_content_type()
    meta         = CONTENT_META[content_type]
    print(f"{meta['emoji']} 콘텐츠 타입: {meta['label']} ({content_type})")

    # 3. 타입에 맞는 데이터 수집
    data = collect_data(content_type)

    # 4. GPT로 3슬라이드 캐러셀 콘텐츠 생성
    news   = data.get("news", data.get("products", data.get("tools_news", data.get("github", []))))
    crypto = data.get("crypto", [])
    content = generate_card_content(theme=meta["label"], news=news, crypto=crypto)

    title = content["slide1"]["headline"]
    print(f"📝 슬라이드 1 훅: {content['slide1']['stat']} / {title}")
    print(f"📝 슬라이드 2: {content['slide2']['headline']}")
    print(f"📝 슬라이드 3 CTA: {content['slide3']['cta_question']}")

    # 4-1. 콘텐츠 타입별 커뮤니티 해시태그 추가
    _COMMUNITY_TAGS = {
        "morning_briefing":  ["#AIThreads"],
        "bigtech_news":      ["#AIThreads"],
        "market_update":     ["#AIThreads", "#CoinGecko"],
        "startup_trend":     ["#AIThreads", "#유튜브자동화"],
        "product_hunt":      ["#AIThreads", "#유튜브자동화"],
        "ai_tips":           ["#AIThreads", "#CLAUDE"],
        "vibe_coding":       ["#AIThreads", "#바이브코딩", "#CLAUDE", "#유튜브자동화"],
        "weekly_review":     ["#AIThreads"],
        # 브랜드 스포트라이트
        "openai_spotlight":  ["#AIThreads", "#OpenAI", "#ChatGPT", "#GPT"],
        "claude_spotlight":  ["#AIThreads", "#CLAUDE", "#Anthropic", "#ConstitutionalAI"],
        "coingecko_report":  ["#AIThreads", "#CoinGecko", "#Web3AI", "#AIAgents"],
    }
    community_tags = " ".join(_COMMUNITY_TAGS.get(content_type, ["#AIThreads"]))
    content["hashtags"] = content["hashtags"].rstrip() + " " + community_tags
    print(f"🏷️  커뮤니티 태그: {community_tags}")

    # 5. 3장 캐러셀 이미지 생성 + Cloudinary 업로드
    image_urls = generate_carousel(content)
    print(f"🖼️  캐러셀 {len(image_urls)}장 생성 완료")

    # 6. 뉴스 링크 추출 (Threads 전용 - 클릭 가능한 링크 지원)
    # Instagram은 피드에서 링크가 클릭 불가 → 캡션 그대로 사용
    LINK_SHARE_TYPES = {"bigtech_news", "startup_trend", "product_hunt", "morning_briefing", "vibe_coding"}
    source_links = [n["link"] for n in news if n.get("link")][:2]
    threads_caption = content["caption"]
    if content_type in LINK_SHARE_TYPES and source_links:
        threads_caption += "\n\n[ 관련 기사 ]\n" + "\n".join(source_links)
        print(f"🔗 Threads 링크 추가: {len(source_links)}개")

    # 7. Instagram + Threads 캐러셀 게시
    _TOPIC_MAP = {
        "market_overview":   "FINANCE",
        "market_update":     "FINANCE",
        "bigtech_news":      "TECHNOLOGY",
        "startup_trend":     "TECHNOLOGY",
        "ai_tips":           "ARTIFICIAL_INTELLIGENCE",
        "vibe_coding":       "ARTIFICIAL_INTELLIGENCE",
        "morning_briefing":  "ARTIFICIAL_INTELLIGENCE",
        "product_hunt":      "ARTIFICIAL_INTELLIGENCE",
        "weekly_review":     "ARTIFICIAL_INTELLIGENCE",
        # 브랜드 스포트라이트
        "openai_spotlight":  "ARTIFICIAL_INTELLIGENCE",
        "claude_spotlight":  "ARTIFICIAL_INTELLIGENCE",
        "coingecko_report":  "FINANCE",
    }
    topic_tag = _TOPIC_MAP.get(content_type, "ARTIFICIAL_INTELLIGENCE")

    results = {}
    ig_result = post_instagram_carousel(image_urls, content["caption"], content["hashtags"])
    th_result = post_threads_carousel(image_urls, threads_caption, content["hashtags"], topic_tag)
    if ig_result.get("id"):
        results["instagram"] = ig_result
    if th_result.get("id"):
        results["threads"]   = th_result

    # 7. Analytics 기록 + Discord 즉시 알림
    if results:
        record_post(content_type, title, results)
        notify_posted(content_type, title, list(results.keys()))

    # 8. Instagram 하이라이트용 Story 커버 자동 생성
    print(f"\n📱 Story 커버 생성 중... (하이라이트: [{get_highlight(content_type)}])")
    try:
        from PIL import Image as _PIL_Image
        from pathlib import Path as _Path
        # 첫 번째 이미지로 Story 커버 생성 (로컬 파일 또는 URL에서)
        _cover_path = _Path("output/story_covers") / f"story_{content_type}.jpg"
        # Cloudinary URL에서 이미지 다운로드 후 Story 커버 생성
        import requests as _req
        import io as _io
        _img_data = _req.get(image_urls[0], timeout=20).content
        _feed_card = _PIL_Image.open(_io.BytesIO(_img_data)).convert("RGB")
        create_story_cover(_feed_card, content_type, title, save_path=_cover_path)
        print_highlight_guide(content_type, title)
    except Exception as e:
        print(f"  ⚠️ Story 커버 생성 실패 (계속 진행): {e}")

    print("🎉 All platforms posted successfully!")


if __name__ == "__main__":
    main()
