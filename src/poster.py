import os
import time
import requests

INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]
INSTAGRAM_TOKEN   = os.environ["INSTAGRAM_ACCESS_TOKEN"]
THREADS_USER_ID   = os.environ["THREADS_USER_ID"]
THREADS_TOKEN     = os.environ["THREADS_ACCESS_TOKEN"]


def post_instagram(image_url: str, caption: str) -> dict:
    """Instagram Graph API v24.0 이미지 게시"""
    # Step 1: 미디어 컨테이너 생성
    res = requests.post(
        f"https://graph.instagram.com/v24.0/{INSTAGRAM_USER_ID}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": INSTAGRAM_TOKEN,
        },
        timeout=30
    )
    res.raise_for_status()
    container_id = res.json()["id"]
    print(f"📸 Instagram container: {container_id}")

    # Step 2: 처리 대기
    time.sleep(15)

    # Step 3: 게시 확정
    result = requests.post(
        f"https://graph.instagram.com/v24.0/{INSTAGRAM_USER_ID}/media_publish",
        params={
            "creation_id": container_id,
            "access_token": INSTAGRAM_TOKEN,
        },
        timeout=30
    ).json()
    print(f"✅ Instagram posted: {result.get('id')}")
    return result


def post_threads(image_url: str, caption: str) -> dict:
    """Threads Graph API v1.0 이미지 게시"""
    # Step 1: 미디어 컨테이너 생성
    res = requests.post(
        f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads",
        params={
            "media_type": "IMAGE",
            "image_url": image_url,
            "text": caption,
            "access_token": THREADS_TOKEN,
        },
        timeout=30
    )
    res.raise_for_status()
    container_id = res.json()["id"]
    print(f"🧵 Threads container: {container_id}")

    # Step 2: 처리 대기
    time.sleep(35)

    # Step 3: 게시 확정
    result = requests.post(
        f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish",
        params={
            "creation_id": container_id,
            "access_token": THREADS_TOKEN,
        },
        timeout=30
    ).json()
    print(f"✅ Threads posted: {result.get('id')}")
    return result


def run_posting(image_url: str, caption: str, hashtags: str) -> None:
    """Instagram + Threads 동시 게시"""
    full_caption = f"{caption}\n\n{hashtags}"
    post_instagram(image_url, full_caption)
    post_threads(image_url, full_caption)
