import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw
from openai import OpenAI
from pathlib import Path
import random

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
ASSETS_DIR = Path("assets")

def generate_background(size: tuple = (1080, 1920)) -> Image.Image:
    """
    로컬 assets/image_*.png가 있으면 재활용하고, 없으면 DALL-E 3로 생성합니다.
    """
    local_images = list(ASSETS_DIR.glob("image_*.png"))
    if local_images:
        random_image_path = random.choice(local_images)
        try:
            img = Image.open(random_image_path).convert("RGBA").resize(size, Image.LANCZOS)
            print(f"✅ 로컬 배경 이미지 재활용: {random_image_path.name}")
            return img
        except Exception as e:
            print(f"⚠️ 로컬 배경 이미지 로드 실패: {e}")

    print("🎨 로컬 배경 이미지가 없어 DALL-E 3로 새로 생성합니다.")
    width, height = size
    prompt = f"""
A photorealistic, clean background image for a tech news card.
Theme: Dark data center, cyberpunk aesthetics, glowing data streams, abstract plexus network.
Color Palette: Deep blues, purples, with accents of cyan and gold.
Composition: Minimalist, with plenty of dark, empty space for text overlays.
Crucially, there should be NO text, NO letters, NO numbers, NO user interface elements, and NO logos in the image.
The image should be abstract and atmospheric.
Aspect Ratio: {width}:{height}
"""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1792", # DALL-E 3 supported sizes for 9:16
            quality="hd",
            style="natural",
            n=1,
        )
        img_data = requests.get(response.data[0].url, timeout=30).content
        img = Image.open(BytesIO(img_data)).convert("RGBA").resize(size, Image.LANCZOS)
        print(f"✅ DALL-E 3 배경 생성 완료: {response.data[0].url}")
        return img
    except Exception as e:
        print(f"⚠️ DALL-E 3 배경 생성 실패: {e}")
        img = Image.new("RGBA", size, (4, 5, 18))
        draw = ImageDraw.Draw(img)
        for y in range(height):
            t = y / height
            v = int(58 * t * (1-t) * 4)
            draw.line([(0, y), (width, y)], fill=(5+v//3, 10+v//2, 28+v, 255))
        return img