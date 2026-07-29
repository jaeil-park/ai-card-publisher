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


def _post_threads_container(user_id: str, token: str, params: dict, max_retries: int = 3) -> str:
    """Threads 미디어 컨테이너 생성 (단일 이미지/캐러셀 슬라이드 공용).

    'Media download has failed'(OAuthException code=1, subcode=2207052)는 URL이
    멀쩡해도 Meta 크롤러가 간헐적으로 못 가져오는 걸로 알려진 문제(Meta 개발자 커뮤니티에
    다수 보고됨) — 같은 실행에서 다른 슬라이드는 성공하고 특정 슬라이드만 실패하는
    패턴이 그 증거. 재시도로 대부분 해결된다.
    """
    last_res = None
    for attempt in range(1, max_retries + 1):
        res = requests.post(
            "https://graph.threads.net/v1.0/{}/threads".format(user_id),
            params=params, timeout=30
        )
        if res.ok:
            return res.json()["id"]

        last_res = res
        is_transient_fetch_error = res.status_code == 400 and "2207052" in res.text
        if is_transient_fetch_error and attempt < max_retries:
            wait = 8 * attempt
            print(f"  ⚠️ 미디어 페치 실패(일시적, subcode 2207052) — {wait}초 후 재시도 ({attempt}/{max_retries})")
            time.sleep(wait)
            continue
        break

    print(f"❌ Threads 컨테이너 오류: {last_res.status_code} - {last_res.text}")
    last_res.raise_for_status()


def _add_comment(platform: str, media_id: str, text: str, user_id: str, token: str):
    """게시물에 첫 댓글 추가 (해시태그 분리 → 도달률 향상)"""
    try:
        if platform == "instagram":
            url = f"https://graph.instagram.com/v24.0/{media_id}/comments"
            params = {"message": text, "access_token": token}
            res = requests.post(url, params=params, timeout=15)
            if res.ok:
                print(f"💬 첫 댓글(해시태그) 등록 완료")
            else:
                print(f"⚠️ 첫 댓글 등록 실패: {res.status_code} - {res.text}")
        else:
            # Threads 댓글(Reply)은 일반 포스트처럼 2단계(생성->발행)로 진행해야 함
            container_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
            container_params = {"media_type": "TEXT", "text": text, "reply_to_id": media_id, "access_token": token}
            res = requests.post(container_url, params=container_params, timeout=15)
            
            if not res.ok:
                print(f"⚠️ Threads 댓글 컨테이너 생성 실패: {res.status_code} - {res.text}")
                return
                
            container_id = res.json()["id"]
            time.sleep(5)  # 컨테이너 준비 대기
            
            pub_res = requests.post(f"https://graph.threads.net/v1.0/{user_id}/threads_publish", params={"creation_id": container_id, "access_token": token}, timeout=15)
            if pub_res.ok:
                print(f"💬 첫 댓글(해시태그) 등록 완료")
            else:
                print(f"⚠️ Threads 댓글 발행 실패: {pub_res.status_code} - {pub_res.text}")
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
        container_id = _post_threads_container(user_id, token, params)
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
        cid = _post_threads_container(user_id, token, {
            "media_type": "IMAGE", "image_url": url,
            "is_carousel_item": "true", "access_token": token,
        })
        child_ids.append(cid)
        print(f"  슬라이드 {i+1}/{len(image_urls)}: {cid}")
        time.sleep(2)

    carousel_params = {"media_type": "CAROUSEL", "children": ",".join(child_ids),
                       "text": full_caption, "access_token": token}
    if topic_tag:
        carousel_params["topic_tag"] = topic_tag
        print(f"🏷️  Threads topic_tag: {topic_tag}")
    container_id = _post_threads_container(user_id, token, carousel_params)
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
