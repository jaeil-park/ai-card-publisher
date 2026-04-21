import os
import random
import requests
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw

ASSETS_DIR = Path("assets")


def _gradient_fallback(size: tuple) -> Image.Image:
    width, height = size
    img = Image.new("RGBA", size, (4, 5, 18))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        v = int(58 * t * (1 - t) * 4)
        draw.line([(0, y), (width, y)], fill=(5 + v // 3, 10 + v // 2, 28 + v, 255))
    return img


def _load_local(size: tuple) -> Image.Image | None:
    local_images = list(ASSETS_DIR.glob("image_*.png"))
    if not local_images:
        return None
    path = random.choice(local_images)
    try:
        img = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
        print(f"✅ 로컬 배경 이미지 재활용: {path.name}")
        return img
    except Exception as e:
        print(f"⚠️ 로컬 배경 이미지 로드 실패: {e}")
        return None


def _fetch_unsplash(query: str, size: tuple) -> Image.Image | None:
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not access_key:
        print("⚠️ UNSPLASH_ACCESS_KEY 미설정 — Unsplash 스킵")
        return None
    try:
        res = requests.get(
            "https://api.unsplash.com/photos/random",
            params={"query": query, "orientation": "portrait", "content_filter": "high"},
            headers={"Authorization": f"Client-ID {access_key}"},
            timeout=15,
        )
        res.raise_for_status()
        url = res.json()["urls"]["regular"]
        img_data = requests.get(url, timeout=30).content
        img = Image.open(BytesIO(img_data)).convert("RGBA").resize(size, Image.LANCZOS)
        print(f"✅ Unsplash 배경 이미지 다운로드 완료")
        return img
    except Exception as e:
        print(f"⚠️ Unsplash 이미지 다운로드 실패: {e}")
        return None


def generate_background(size: tuple = (1080, 1350), dalle_prompt: str = "") -> Image.Image:
    """
    우선순위: 로컬 assets/ → Unsplash API → 그라데이션 폴백
    dalle_prompt 값을 Unsplash 검색어로 재활용합니다.
    """
    img = _load_local(size)
    if img:
        return img

    query = dalle_prompt or "technology dark abstract"
    img = _fetch_unsplash(query, size)
    if img:
        return img

    print("🎨 배경 이미지 없음 — 그라데이션 폴백 사용")
    return _gradient_fallback(size)
