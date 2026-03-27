import os
import time
import requests

AI_FOOTER = "\n\n✨ AI가 큐레이션한 콘텐츠입니다 | 매일 AI·코인·증시 트렌드 👉 팔로우"


def _add_comment(platform: str, media_id: str, text: str, user_id: str, token: str):
    """게시물에 첫 댓글 추가 (해시태그 분리 → 도달률 향상)"""
    if platform == "instagram":
        url = f"https://graph.instagram.com/v24.0/{media_id}/comments"
    else:
        url = f"https://graph.threads.net/v1.0/{media_id}/replies"
    try:
        res = requests.post(
            url,
            params={"message" if platform == "instagram" else "text": text,
                    "access_token": token},
            timeout=15
        )
        if res.ok:
            print(f"💬 첫 댓글(해시태그) 등록 완료")
    except Exception as e:
        print(f"⚠️ 첫 댓글 등록 실패: {e}")


def post_instagram(image_url: str, caption: str, hashtags: str) -> dict:
    """Instagram Graph API v24.0 이미지 게시 + 첫 댓글에 해시태그"""
    user_id = os.environ.get("INSTAGRAM_USER_ID", "")
    token   = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")

    if not user_id or not token:
        print("⏭️  Instagram 미설정 - 스킵")
        return {}

    full_caption = caption + AI_FOOTER

    res = requests.post(
        f"https://graph.instagram.com/v24.0/{user_id}/media",
        params={"image_url": image_url, "caption": full_caption, "access_token": token},
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
    media_id = result.get("id", "")
    print(f"✅ Instagram posted: {media_id}")

    if media_id and hashtags:
        time.sleep(3)
        _add_comment("instagram", media_id, hashtags, user_id, token)

    return result


def post_threads(image_url: str, caption: str, hashtags: str) -> dict:
    """Threads Graph API v1.0 이미지 게시 + 첫 댓글에 해시태그"""
    user_id = os.environ.get("THREADS_USER_ID", "")
    token   = os.environ.get("THREADS_ACCESS_TOKEN", "")

    if not user_id or not token:
        print("⏭️  Threads 미설정 - 스킵")
        return {}

    full_caption = caption + AI_FOOTER

    res = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        params={"media_type": "IMAGE", "image_url": image_url,
                "text": full_caption, "access_token": token},
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
    media_id = result.get("id", "")
    print(f"✅ Threads posted: {media_id}")

    if media_id and hashtags:
        time.sleep(3)
        _add_comment("threads", media_id, hashtags, user_id, token)

    return result


def run_posting(image_url: str, caption: str, hashtags: str) -> None:
    """Instagram + Threads 게시 (미설정 플랫폼 자동 스킵)"""
    post_instagram(image_url, caption, hashtags)
    post_threads(image_url, caption, hashtags)
