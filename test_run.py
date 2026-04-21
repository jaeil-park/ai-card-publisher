import json
from dotenv import load_dotenv

load_dotenv()
from src.trend_fetcher import get_content_type, collect_data, generate_card_content
from src.card_generator import render_card_png

def test_pipeline():
    print("1️⃣ 콘텐츠 타입 결정 중...")
    content_type = get_content_type()
    print(f"   -> 선택된 타입: {content_type}")

    print("\n2️⃣ 데이터 수집 중 (Naver, Github 등)...")
    data = collect_data(content_type)
    print(f"   -> 수집 완료: {list(data.keys())}")

    print("\n3️⃣ Gemini API로 카드뉴스 내용 생성 중...")
    card_content = generate_card_content(content_type, data)
    print("   -> 생성 결과:")
    print(json.dumps(card_content, ensure_ascii=False, indent=2))

    print("\n4️⃣ React + Playwright로 카드 렌더링 중...")
    png_bytes = render_card_png(card_content)

    output_path = "test_card.png"
    with open(output_path, "wb") as f:
        f.write(png_bytes)
    print(f"\n✅ 테스트 완료! 결과물이 '{output_path}'에 저장되었습니다. 사진을 확인해보세요!")

if __name__ == "__main__":
    test_pipeline()