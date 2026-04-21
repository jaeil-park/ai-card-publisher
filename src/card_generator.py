import json
import shutil
import socket
import subprocess
import threading
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlencode, quote

from playwright.sync_api import sync_playwright

DIST_DIR    = Path(__file__).parent.parent / "card-ui-dist"
CARD_UI_DIR = Path(__file__).parent.parent / "card-ui"


def _ensure_build():
    if not (DIST_DIR / "index.html").exists():
        print("🔨 card-ui 빌드 중...")
        subprocess.run(["npm", "run", "build"], cwd=str(CARD_UI_DIR),
                       check=True, shell=True)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _start_server(directory: Path, port: int) -> HTTPServer:
    class _H(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)
        def log_message(self, *_):
            pass

    srv = HTTPServer(("127.0.0.1", port), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def render_card_png(content: dict, bg_image_path: Path = None,
                    slide_index: int = None, total_slides: int = None) -> bytes:
    """React 카드를 Playwright로 1080×1350 PNG 렌더링.

    content 필수 키: title, points (list of {subtitle, source})
    bg_image_path: 로컬 배경 이미지 경로 (없으면 검정 배경)
    """
    _ensure_build()

    kst_date = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y.%m.%d")

    # 배경 이미지를 dist 디렉터리에 임시 복사
    tmp_bg = None
    bg_url = ""
    if bg_image_path and Path(bg_image_path).exists():
        tmp_bg = DIST_DIR / "_bg_temp.png"
        shutil.copy2(bg_image_path, tmp_bg)
        bg_url = "./_bg_temp.png"

    qs = {
        "title":  content.get("title", ""),
        "points": json.dumps(content.get("points", []), ensure_ascii=False),
        "bg_url": bg_url,
        "date":   kst_date,
        "render": "1",
    }
    if slide_index is not None:
        qs["slide_index"] = str(slide_index)
    if total_slides is not None:
        qs["total_slides"] = str(total_slides)
    params = urlencode(qs, quote_via=quote)

    port   = _free_port()
    server = _start_server(DIST_DIR, port)
    url    = f"http://127.0.0.1:{port}/index.html?{params}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1350})
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_selector(".card", timeout=15000)
            page.wait_for_timeout(500)
            png = page.locator(".card").screenshot()
            browser.close()
    finally:
        server.shutdown()
        if tmp_bg and tmp_bg.exists():
            tmp_bg.unlink()

    return png
