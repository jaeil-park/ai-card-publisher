import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw
from openai import OpenAI
from pathlib import Path
import random

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
ASSETS_DIR = Path("assets")

def generate_background(size: tuple = (1080, 1350), dalle_prompt: str = "") -> Image.Image:
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
    if not dalle_prompt:
        dalle_prompt = "A photorealistic, clean background image for a tech news card."
        
    enhanced_prompt = f"""
{dalle_prompt}

Style requirements:
- Photorealistic, high resolution news photograph quality
- Professional journalism photo style
- Dark moody cinematic lighting with subtle blue/orange tones
- No text overlays, no letters, no numbers, no graphics, no UI elements
- No abstract art, no illustrations
- Real-world scene that directly represents the news topic
- Shot as if taken by a professional news photographer
- Sharp focus on main subject, plenty of dark space for text overlays
Aspect Ratio: {width}:{height}
"""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
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