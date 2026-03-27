import os
from dotenv import load_dotenv

load_dotenv()

from src.token_manager import check_and_refresh_tokens
from src.trend_fetcher import get_content_type, collect_data, generate_card_content, CONTENT_META
from src.card_generator import create_card
from src.analytics import record_post, notify_posted


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

    # 4. GPT로 카드 콘텐츠 생성
    content = generate_card_content(content_type, data)
    print(f"📝 Title: {content['title']}")

    # 5. 카드 이미지 생성 + Cloudinary 업로드
    image_url = create_card(content)

    # 6. Instagram + Threads 게시
    results = {}
    from src.poster import post_instagram, post_threads
    ig_result = post_instagram(image_url, content["caption"], content["hashtags"])
    th_result = post_threads(image_url, content["caption"], content["hashtags"])
    if ig_result.get("id"):
        results["instagram"] = ig_result
    if th_result.get("id"):
        results["threads"]   = th_result

    # 7. Analytics 기록 + Discord 즉시 알림
    if results:
        record_post(content_type, content["title"], results)
        notify_posted(content_type, content["title"], list(results.keys()))

    print("🎉 All platforms posted successfully!")


if __name__ == "__main__":
    main()
