import os
from dotenv import load_dotenv

load_dotenv()

from src.token_manager import check_and_refresh_tokens
from src.trend_fetcher import get_content_type, collect_data, generate_card_content, CONTENT_META
from src.card_generator import generate_carousel
from src.analytics import record_post, notify_posted
from src.poster import post_instagram_carousel, post_threads_carousel


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

    # 5. 3장 캐러셀 이미지 생성 + Cloudinary 업로드
    image_urls = generate_carousel(content)
    print(f"🖼️  캐러셀 {len(image_urls)}장 생성 완료")

    # 6. Instagram + Threads 캐러셀 게시
    results = {}
    ig_result = post_instagram_carousel(image_urls, content["caption"], content["hashtags"])
    th_result = post_threads_carousel(image_urls, content["caption"], content["hashtags"])
    if ig_result.get("id"):
        results["instagram"] = ig_result
    if th_result.get("id"):
        results["threads"]   = th_result

    # 7. Analytics 기록 + Discord 즉시 알림
    if results:
        record_post(content_type, title, results)
        notify_posted(content_type, title, list(results.keys()))

    print("🎉 All platforms posted successfully!")


if __name__ == "__main__":
    main()
