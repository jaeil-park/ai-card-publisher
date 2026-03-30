import asyncio
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
    </style>
</head>
<body class="w-[1080px] h-[1920px] overflow-hidden">
    <div class="relative w-full h-full bg-cover bg-center" style="background-image: url('{{ bg_image_url }}');">
        <div class="absolute inset-0 bg-black/30"></div>
        <div class="relative z-10 flex flex-col h-full p-14 text-white">
            
            <h1 class="text-6xl font-bold leading-tight text-center mb-16 drop-shadow-lg">
                {{ title }}
            </h1>

            <div class="space-y-8">
                {% for point in points %}
                <div class="p-6 rounded-2xl border border-white/20 bg-black/40 backdrop-blur-md shadow-2xl">
                    <h2 class="text-3xl font-bold text-cyan-300 mb-3 leading-snug drop-shadow-md">{{ point.subtitle }}</h2>
                    <p class="text-right text-xl text-white/60">출처: {{ point.source }}</p>
                </div>
                {% endfor %}
            </div>

            <div class="mt-auto text-center text-2xl text-white/50 drop-shadow-md">
                Gems | @gems.official
            </div>
        </div>
    </div>
</body>
</html>
"""

async def render_html_as_image(facts: dict, bg_image_path: Path, output_path: Path) -> Path:
    """Jinja2 템플릿과 Playwright를 사용하여 HTML을 렌더링하고 스크린샷을 찍습니다."""
    env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['html']))
    template = env.from_string(HTML_TEMPLATE)
    html_content = template.render(
        title=facts.get("title", ""),
        points=facts.get("points", []),
        bg_image_url=bg_image_path.resolve().as_uri()
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1080, 'height': 1920})
        await page.set_content(html_content, wait_until="networkidle")
        await page.screenshot(path=output_path, type='png')
        await browser.close()

    print(f"✅ Playwright 스크린샷 저장 완료: {output_path}")
    return output_path

def render_html_sync(facts: dict, bg_image_path: Path, output_path: Path) -> Path:
    """render_html_as_image의 동기 실행 래퍼"""
    return asyncio.run(render_html_as_image(facts, bg_image_path, output_path))