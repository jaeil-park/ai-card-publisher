import os
from dotenv import load_dotenv

load_dotenv()  # 로컬 테스트용 .env 로드

from src.token_manager import check_and_refresh_tokens
from src.trend_fetcher import get_theme, fetch_ai_news, fetch_crypto, generate_card_content
from src.card_generator import create_card
from src.poster import run_posting


def main():
    # 1. 토큰 만료 체크 (30일 이하 시 자동 갱신)
    print("🔍 토큰 상태 확인 중...")
    check_and_refresh_tokens()

    # 2. 테마 결정
    theme, keywords = get_theme()
    print(f"🚀 Theme: {theme} | Keywords: {keywords}")

    # 3. 트렌드 수집 + 콘텐츠 생성
    news    = fetch_ai_news()
    crypto  = fetch_crypto()
    content = generate_card_content(theme, news, crypto)
    print(f"📝 Title: {content['title']}")

    # 4. 카드 이미지 생성 + 업로드
    image_url = create_card(content)

    # 5. SNS 게시
    run_posting(image_url, content["caption"], content["hashtags"])
    print("🎉 All platforms posted successfully!")


if __name__ == "__main__":
    main()
