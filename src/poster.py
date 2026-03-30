import os
import time
import requests

AI_FOOTER = "\n\n✨ AI가 큐레이션한 콘텐츠입니다 | 매일 AI·코인·증시 트렌드 👉 팔로우"
THREADS_MAX_LEN = 500


def _truncate_for_threads(caption: str) -> str:
    """Threads API 500자 제한 대응: AI_FOOTER 포함해서 500자 이내로 자름"""
    max_body = THREADS_MAX_LEN - len(AI_FOOTER) - 1  # -1 for ellipsis
    if len(caption) > max_body:
        return caption[:max_body] + "…"
    return caption


def _add_comment(platform: str, media_id: str, text: str, user_id: str, token: str):
    """게시물에 첫 댓글 추가 (해시태그 분리 → 도달률 향상)"""
    if platform == "instagram":
        url = f"https://graph.instagram.com/v24.0/{media_id}/comments"
        params = {"message": text, "access_token": token}
    else:
        url = f"https://graph.threads.net/v1.0/{media_id}/replies"
        params = {"text": text, "access_token": token}
    try:
        res = requests.post(url, params=params, timeout=15)
        if res.ok:
            print(f"💬 첫 댓글(해시태그) 등록 완료")
        else:
            print(f"⚠️ 첫 댓글 등록 실패: {res.status_code}")
    except Exception as e:
        print(f"⚠️ 첫 댓글 등록 오류: {e}")


def post_instagram_carousel(image_urls: list[str], caption: str, hashtags: str) -> dict:
    """Instagram Graph API v24.0 게시 (1장: 단일 이미지 / 2장+: 캐러셀)"""
    user_id = os.environ.get("INSTAGRAM_USER_ID", "")
    token   = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")

    if not user_id or not token:
        print("⏭️  Instagram 미설정 - 스킵")
        return {}

    full_caption = caption + AI_FOOTER

    # 단일 이미지 포스팅
    if len(image_urls) == 1:
        print("📸 Instagram 단일 이미지 게시 중...")
        res = requests.post(
            f"https://graph.instagram.com/v24.0/{user_id}/media",
            params={"image_url": image_urls[0], "caption": full_caption, "access_token": token},
            timeout=30
        )
        if not res.ok:
            print(f"❌ Instagram media container 오류: {res.status_code} - {res.text}")
        res.raise_for_status()
        container_id = res.json()["id"]
        time.sleep(5)
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

    # 캐러셀 포스팅 (2장 이상)
    print(f"📸 Instagram 슬라이드 컨테이너 생성 중... ({len(image_urls)}장)")
    child_ids = []
    for i, url in enumerate(image_urls):
        res = requests.post(
            f"https://graph.instagram.com/v24.0/{user_id}/media",
            params={"image_url": url, "is_carousel_item": "true", "access_token": token},
            timeout=30
        )
        if not res.ok:
            print(f"❌ 슬라이드 {i+1} 컨테이너 오류: {res.status_code} - {res.text}")
        res.raise_for_status()
        child_ids.append(res.json()["id"])
        print(f"  슬라이드 {i+1}/{len(image_urls)}: {res.json()['id']}")
        time.sleep(2)

    res = requests.post(
        f"https://graph.instagram.com/v24.0/{user_id}/media",
        params={"media_type": "CAROUSEL", "children": ",".join(child_ids),
                "caption": full_caption, "access_token": token},
        timeout=30
    )
    if not res.ok:
        print(f"❌ Instagram carousel container 오류: {res.status_code} - {res.text}")
    res.raise_for_status()
    container_id = res.json()["id"]
    print(f"📸 Instagram carousel container: {container_id}")

    time.sleep(15)
    result = requests.post(
        f"https://graph.instagram.com/v24.0/{user_id}/media_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30
    ).json()
    media_id = result.get("id", "")
    print(f"✅ Instagram carousel posted: {media_id}")
    if media_id and hashtags:
        time.sleep(3)
        _add_comment("instagram", media_id, hashtags, user_id, token)
    return result


def post_threads_carousel(image_urls: list[str], caption: str, hashtags: str, topic_tag: str = "") -> dict:
    """Threads Graph API v1.0 게시 (1장: 단일 이미지 / 2장+: 캐러셀)"""
    user_id = os.environ.get("THREADS_USER_ID", "")
    token   = os.environ.get("THREADS_ACCESS_TOKEN", "")

    if not user_id or not token:
        print("⏭️  Threads 미설정 - 스킵")
        return {}

    full_caption = _truncate_for_threads(caption) + AI_FOOTER

    # 단일 이미지 포스팅
    if len(image_urls) == 1:
        print("🧵 Threads 단일 이미지 게시 중...")
        params = {"media_type": "IMAGE", "image_url": image_urls[0],
                  "text": full_caption, "access_token": token}
        if topic_tag:
            params["topic_tag"] = topic_tag
        res = requests.post(
            f"https://graph.threads.net/v1.0/{user_id}/threads",
            params=params, timeout=30
        )
        if not res.ok:
            print(f"❌ Threads media container 오류: {res.status_code} - {res.text}")
        res.raise_for_status()
        container_id = res.json()["id"]
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

    # 캐러셀 포스팅 (2장 이상)
    print(f"🧵 Threads 슬라이드 컨테이너 생성 중... ({len(image_urls)}장)")
    child_ids = []
    for i, url in enumerate(image_urls):
        res = requests.post(
            f"https://graph.threads.net/v1.0/{user_id}/threads",
            params={"media_type": "IMAGE", "image_url": url,
                    "is_carousel_item": "true", "access_token": token},
            timeout=30
        )
        if not res.ok:
            print(f"❌ 슬라이드 {i+1} 컨테이너 오류: {res.status_code} - {res.text}")
        res.raise_for_status()
        child_ids.append(res.json()["id"])
        print(f"  슬라이드 {i+1}/{len(image_urls)}: {res.json()['id']}")
        time.sleep(2)

    carousel_params = {"media_type": "CAROUSEL", "children": ",".join(child_ids),
                       "text": full_caption, "access_token": token}
    if topic_tag:
        carousel_params["topic_tag"] = topic_tag
        print(f"🏷️  Threads topic_tag: {topic_tag}")
    res = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        params=carousel_params, timeout=30
    )
    if not res.ok:
        print(f"❌ Threads carousel container 오류: {res.status_code} - {res.text}")
    res.raise_for_status()
    container_id = res.json()["id"]
    print(f"🧵 Threads carousel container: {container_id}")

    time.sleep(35)
    result = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30
    ).json()
    media_id = result.get("id", "")
    print(f"✅ Threads carousel posted: {media_id}")
    if media_id and hashtags:
        time.sleep(3)
        _add_comment("threads", media_id, hashtags, user_id, token)
    return result
