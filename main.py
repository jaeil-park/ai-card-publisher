import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

from src.token_manager import check_and_refresh_tokens
from src.trend_fetcher import get_content_type, collect_data, CONTENT_META
from src.content_generator import generate_facts, generate_caption, generate_weekly_sections
from src.background_maker import generate_background
from src.html_renderer import render_html_sync
from src.image_compositor import upload_image # Re-using the uploader
from src.analytics import record_post, notify_posted
from src.poster import post_instagram_carousel, post_threads_carousel
from src.highlight_manager import get_highlight, create_story_cover, print_highlight_guide
from PIL import Image

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

def main():
    # 1. 토큰 만료 체크
    print("🔍 토큰 상태 확인 중...")
    check_and_refresh_tokens()

    # 2. 콘텐츠 타입 결정 및 데이터 수집
    content_type = get_content_type()
    meta         = CONTENT_META[content_type]
    print(f"\n{meta['emoji']} 콘텐츠 타입: {meta['label']} ({content_type})")
    data = collect_data(content_type)
    news_items = data.get("news", data.get("products", []))

    # 3~5. 팩트 추출 → 배경 → 렌더링 (주간 리포트: 3장 / 일반: 1장)
    if content_type == "weekly_review":
        print("\n[1/5] 🤖 GPT-4o로 주간 써머리 3섹션 추출 중...")
        all_sections = generate_weekly_sections(data)
        title = all_sections[0].get("title", "주간 핵심 정리")
        print(f"  ✅ {len(all_sections)}개 섹션 생성 완료")

        print(f"\n[2-3/5] 🎨 배경 생성 + Playwright 렌더링 중... ({len(all_sections)}장)")
        image_urls = []
        final_image_pil = None
        for i, section_facts in enumerate(all_sections):
            bg = generate_background(size=(1080, 1350))
            bg_path = OUTPUT_DIR / f"bg_weekly_{i}.png"
            bg.save(bg_path)
            card_path = OUTPUT_DIR / f"weekly_card_{i}.png"
            render_html_sync(section_facts, bg_path, card_path)
            card_pil = Image.open(card_path)
            if final_image_pil is None:
                final_image_pil = card_pil
            image_urls.append(upload_image(card_pil))
            print(f"  ✅ 슬라이드 {i+1}/{len(all_sections)} 업로드 완료")

        facts = all_sections[0]
    else:
        print("\n[1/5] 🤖 GPT-4o로 이미지용 팩트 추출 중...")
        facts = generate_facts(theme=meta["label"], news=news_items)
        title = facts.get("title")
        print(f"  ✅ 제목: {title}")

        print("\n[2/5] 🎨 배경 이미지 준비 중...")
        bg_path = OUTPUT_DIR / "background.png"
        generate_background(size=(1080, 1350)).save(bg_path)

        print("\n[3/5] 🖼️  Playwright로 HTML 렌더링 및 스크린샷 중...")
        final_image_path = OUTPUT_DIR / "final_card.png"
        render_html_sync(facts, bg_path, final_image_path)
        final_image_pil = Image.open(final_image_path)
        image_urls = [upload_image(final_image_pil)]

    # 캡션 생성
    print("\n[4/5] ✍️  GPT-4o로 SNS 본문 생성 중...")
    caption_full = generate_caption(facts, news_items)
    caption_parts = caption_full.rsplit("#", 1)
    caption = caption_parts[0].strip()
    hashtags = f"#{caption_parts[1].strip()}" if len(caption_parts) > 1 else "#AI #FinTech #Gems"

    # 포스팅
    print("\n[5/5] ☁️  SNS 포스팅 중...")
    source_links = [n["link"] for n in news_items if n.get("link")][:2]
    threads_caption = caption
    if source_links:
        threads_caption += "\n\n[관련 링크]\n" + "\n".join(source_links)

    # Instagram & Threads 포스팅
    results = {}
    ig_result = post_instagram_carousel(image_urls, caption, hashtags)
    th_result = post_threads_carousel(image_urls, threads_caption, hashtags, "TECHNOLOGY")
    if ig_result.get("id"):
        results["instagram"] = ig_result
    if th_result.get("id"):
        results["threads"]   = th_result

    # 8. 결과 기록 및 알림
    if results:
        record_post(content_type, title, results)
        notify_posted(content_type, title, list(results.keys()))

    # 9. 하이라이트용 Story 커버 생성
    print(f"\n📱 Story 커버 생성 중... (하이라이트: [{get_highlight(content_type)}])")
    try:
        from pathlib import Path as _Path
        _cover_path = _Path("output/story_covers") / f"story_{content_type}.jpg"
        create_story_cover(final_image_pil, content_type, title, save_path=_cover_path)
        print_highlight_guide(content_type, title)
    except Exception as e:
        print(f"  ⚠️ Story 커버 생성 실패 (계속 진행): {e}")

    print("🎉 All platforms posted successfully!")


if __name__ == "__main__":
    main()
