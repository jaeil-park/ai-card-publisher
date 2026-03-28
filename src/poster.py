import os
import time
import requests

AI_FOOTER = "\n\n✨ AI가 큐레이션한 콘텐츠입니다 | 매일 AI·코인·증시 트렌드 👉 팔로우"


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
    """Instagram Graph API v24.0 캐러셀(슬라이드) 게시

    Instagram 가이드라인 반영:
    - 슬라이드는 단일 이미지보다 도달 성과 우수
    - 해시태그는 첫 댓글로 분리 → 도달률 향상
    - 낚시성/오해 소지 없는 캡션 사용
    """
    user_id = os.environ.get("INSTAGRAM_USER_ID", "")
    token   = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")

    if not user_id or not token:
        print("⏭️  Instagram 미설정 - 스킵")
        return {}

    # 1. 각 슬라이드 아이템 컨테이너 생성
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
        cid = res.json()["id"]
        child_ids.append(cid)
        print(f"  슬라이드 {i+1}/{len(image_urls)}: {cid}")
        time.sleep(2)

    # 2. 캐러셀 컨테이너 생성
    full_caption = caption + AI_FOOTER
    res = requests.post(
        f"https://graph.instagram.com/v24.0/{user_id}/media",
        params={
            "media_type": "CAROUSEL",
            "children":   ",".join(child_ids),
            "caption":    full_caption,
            "access_token": token,
        },
        timeout=30
    )
    if not res.ok:
        print(f"❌ Instagram carousel container 오류: {res.status_code} - {res.text}")
    res.raise_for_status()
    container_id = res.json()["id"]
    print(f"📸 Instagram carousel container: {container_id}")

    # 3. 게시 (15초 대기 후)
    time.sleep(15)
    result = requests.post(
        f"https://graph.instagram.com/v24.0/{user_id}/media_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30
    ).json()
    media_id = result.get("id", "")
    print(f"✅ Instagram carousel posted: {media_id}")

    # 4. 해시태그 첫 댓글 등록
    if media_id and hashtags:
        time.sleep(3)
        _add_comment("instagram", media_id, hashtags, user_id, token)

    return result


def post_threads_carousel(image_urls: list[str], caption: str, hashtags: str, topic_tag: str = "") -> dict:
    """Threads Graph API v1.0 캐러셀(슬라이드) 게시

    Instagram 가이드라인 반영:
    - 슬라이드 형식으로 더 많은 도달 확보
    - 해시태그 첫 댓글 분리
    - topic_tag: ARTIFICIAL_INTELLIGENCE / TECHNOLOGY / FINANCE
    """
    user_id = os.environ.get("THREADS_USER_ID", "")
    token   = os.environ.get("THREADS_ACCESS_TOKEN", "")

    if not user_id or not token:
        print("⏭️  Threads 미설정 - 스킵")
        return {}

    full_caption = caption + AI_FOOTER

    # 1. 각 슬라이드 아이템 컨테이너 생성
    print(f"🧵 Threads 슬라이드 컨테이너 생성 중... ({len(image_urls)}장)")
    child_ids = []
    for i, url in enumerate(image_urls):
        res = requests.post(
            f"https://graph.threads.net/v1.0/{user_id}/threads",
            params={
                "media_type":       "IMAGE",
                "image_url":        url,
                "is_carousel_item": "true",
                "access_token":     token,
            },
            timeout=30
        )
        if not res.ok:
            print(f"❌ 슬라이드 {i+1} 컨테이너 오류: {res.status_code} - {res.text}")
        res.raise_for_status()
        cid = res.json()["id"]
        child_ids.append(cid)
        print(f"  슬라이드 {i+1}/{len(image_urls)}: {cid}")
        time.sleep(2)

    # 2. 캐러셀 컨테이너 생성
    carousel_params = {
        "media_type":   "CAROUSEL",
        "children":     ",".join(child_ids),
        "text":         full_caption,
        "access_token": token,
    }
    if topic_tag:
        carousel_params["topic_tag"] = topic_tag
        print(f"🏷️  Threads topic_tag: {topic_tag}")
    res = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        params=carousel_params,
        timeout=30
    )
    if not res.ok:
        print(f"❌ Threads carousel container 오류: {res.status_code} - {res.text}")
    res.raise_for_status()
    container_id = res.json()["id"]
    print(f"🧵 Threads carousel container: {container_id}")

    # 3. 게시 (35초 대기 후)
    time.sleep(35)
    result = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30
    ).json()
    media_id = result.get("id", "")
    print(f"✅ Threads carousel posted: {media_id}")

    # 4. 해시태그 첫 댓글 등록
    if media_id and hashtags:
        time.sleep(3)
        _add_comment("threads", media_id, hashtags, user_id, token)

    return result
