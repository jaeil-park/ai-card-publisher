import asyncio
import base64
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

# Jinja2 템플릿과 Tailwind CSS를 사용한 HTML 구조
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Noto Sans KR', sans-serif; }
        .glass-panel {
            background-color: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }
    </style>
</head>
<body class="w-[1080px] h-[1350px] overflow-hidden bg-black text-white">
    <div class="absolute inset-0 bg-cover bg-center" style="background-image: url('{{ bg_image_data_uri }}');"></div>
    <!-- 텍스트 가독성을 위한 은은한 그라데이션 오버레이 -->
    <div class="absolute inset-0 bg-gradient-to-b from-black/10 via-black/30 to-black/80"></div>
    
    <div class="relative z-10 flex flex-col h-full p-12">
        <h1 class="text-5xl font-extrabold leading-snug text-center mb-10 mt-8 tracking-tight drop-shadow-2xl">
            {{ title }}
        </h1>

        <!-- 중앙 정렬을 위한 Flex Container -->
        <div class="flex-1 flex flex-col justify-center space-y-6">
            {% for point in points %}
            <!-- iOS 스타일 Glassmorphism -->
            <div class="glass-panel p-8 rounded-[2rem]">
                <h2 class="text-3xl font-bold text-cyan-200 mb-4 leading-snug drop-shadow-md">{{ point.subtitle }}</h2>
                <p class="text-right text-xl text-white/70 font-medium">출처: {{ point.source }}</p>
            </div>
            {% endfor %}
        </div>

        <div class="mt-8 text-center text-2xl font-bold text-white/40 tracking-widest uppercase">
            GEMS <span class="mx-2 font-light">|</span> @GEMS.OFFICIAL
        </div>
    </div>
</body>
</html>
"""

async def render_html_as_image(facts: dict, bg_image_path: Path, output_path: Path) -> Path:
    """Jinja2 템플릿과 Playwright를 사용하여 HTML을 렌더링하고 스크린샷을 찍습니다."""
    # Playwright에서 로컬 파일 보안 정책 이슈를 우회하기 위해 Base64 삽입
    with open(bg_image_path, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode('utf-8')
    bg_image_data_uri = f"data:image/png;base64,{b64_string}"

    env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['html']))
    template = env.from_string(HTML_TEMPLATE)
    html_content = template.render(
        title=facts.get("title", ""),
        points=facts.get("points", []),
        bg_image_data_uri=bg_image_data_uri
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # 인스타그램 세로 피드 최적화 해상도 (4:5)
        page = await browser.new_page(viewport={'width': 1080, 'height': 1350})
        await page.set_content(html_content, wait_until="networkidle")
        await page.wait_for_timeout(500)  # CSS 필터 및 폰트 렌더링 보장 대기
        await page.screenshot(path=output_path, type='png')
        await browser.close()

    print(f"✅ Playwright 스크린샷 저장 완료: {output_path}")
    return output_path

def render_html_sync(facts: dict, bg_image_path: Path, output_path: Path) -> Path:
    """render_html_as_image의 동기 실행 래퍼"""
    return asyncio.run(render_html_as_image(facts, bg_image_path, output_path))