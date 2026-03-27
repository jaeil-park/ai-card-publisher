import os
import time
import requests


def post_instagram(image_url: str, caption: str) -> dict:
    """Instagram Graph API v24.0 이미지 게시"""
    user_id = os.environ.get("INSTAGRAM_USER_ID", "")
    token   = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")

    if not user_id or not token:
        print("⏭️  Instagram 미설정 - 스킵")
        return {}

    res = requests.post(
        f"https://graph.instagram.com/v24.0/{user_id}/media",
        params={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=30
    )
    if not res.ok:
        print(f"❌ Instagram API 오류: {res.status_code} - {res.text}")
    res.raise_for_status()
    container_id = res.json()["id"]
    print(f"📸 Instagram container: {container_id}")

    time.sleep(15)

    result = requests.post(
        f"https://graph.instagram.com/v24.0/{user_id}/media_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30
    ).json()
    print(f"✅ Instagram posted: {result.get('id')}")
    return result


def post_threads(image_url: str, caption: str) -> dict:
    """Threads Graph API v1.0 이미지 게시"""
    user_id = os.environ.get("THREADS_USER_ID", "")
    token   = os.environ.get("THREADS_ACCESS_TOKEN", "")

    if not user_id or not token:
        print("⏭️  Threads 미설정 - 스킵")
        return {}

    res = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        params={"media_type": "IMAGE", "image_url": image_url, "text": caption, "access_token": token},
        timeout=30
    )
    res.raise_for_status()
    container_id = res.json()["id"]
    print(f"🧵 Threads container: {container_id}")

    time.sleep(35)

    result = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30
    ).json()
    print(f"✅ Threads posted: {result.get('id')}")
    return result


def run_posting(image_url: str, caption: str, hashtags: str) -> None:
    """Instagram + Threads 게시 (미설정 플랫폼 자동 스킵)"""
    full_caption = f"{caption}\n\n{hashtags}"
    post_instagram(image_url, full_caption)
    post_threads(image_url, full_caption)
