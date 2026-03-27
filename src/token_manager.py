import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

TOKEN_FILE = Path(".token_status.json")
REFRESH_THRESHOLD_DAYS = 30  # 30일 이하 남으면 자동 갱신


# ── 공통 유틸 ──────────────────────────────

def load_token_status() -> dict:
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return {}


def save_token_status(status: dict):
    with open(TOKEN_FILE, "w") as f:
        json.dump(status, f, indent=2)


def days_until_expiry(expires_at_timestamp: int) -> int:
    now = datetime.now(timezone.utc).timestamp()
    remaining_seconds = expires_at_timestamp - now
    return max(0, int(remaining_seconds / 86400))


# ── Instagram 토큰 갱신 ────────────────────

def refresh_instagram_token(current_token: str) -> dict:
    """Instagram Long-lived Token 갱신 (만료 전 언제든 갱신 가능)"""
    res = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={
            "grant_type": "ig_refresh_token",
            "access_token": current_token,
        },
        timeout=15
    )
    res.raise_for_status()
    data = res.json()

    if "error" in data:
        raise Exception(f"Instagram 토큰 갱신 실패: {data['error']['message']}")

    expires_in = data.get("expires_in", 5184000)  # 기본 60일
    print(f"✅ Instagram 토큰 갱신 완료 | 만료까지: {expires_in // 86400}일")
    return {
        "access_token": data["access_token"],
        "expires_in": expires_in,
        "expires_at": int(datetime.now(timezone.utc).timestamp()) + expires_in
    }


# ── Threads 토큰 갱신 ─────────────────────

def refresh_threads_token(current_token: str) -> dict:
    """Threads Long-lived Token 갱신 (만료 전 언제든 갱신 가능)"""
    res = requests.get(
        "https://graph.threads.net/refresh_access_token",
        params={
            "grant_type": "th_refresh_token",
            "access_token": current_token,
        },
        timeout=15
    )
    res.raise_for_status()
    data = res.json()

    if "error" in data:
        raise Exception(f"Threads 토큰 갱신 실패: {data['error']['message']}")

    expires_in = data.get("expires_in", 5184000)
    print(f"✅ Threads 토큰 갱신 완료 | 만료까지: {expires_in // 86400}일")
    return {
        "access_token": data["access_token"],
        "expires_in": expires_in,
        "expires_at": int(datetime.now(timezone.utc).timestamp()) + expires_in
    }


# ── GitHub Secrets 자동 업데이트 ───────────

def update_github_secret(secret_name: str, secret_value: str):
    """갱신된 토큰을 GitHub Secrets에 자동 업데이트"""
    import base64
    from nacl import encoding, public

    github_token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "jaeil-park/ai-card-publisher")

    if not github_token:
        print(f"⚠️ GITHUB_TOKEN 없음 - Secret [{secret_name}] 수동 업데이트 필요")
        return

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # 공개 키 가져오기
    key_res = requests.get(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        headers=headers, timeout=10
    )
    key_res.raise_for_status()
    key_data = key_res.json()

    # 토큰 값 암호화
    pub_key = public.PublicKey(
        key_data["key"].encode("utf-8"),
        encoding.Base64Encoder()
    )
    sealed_box = public.SealedBox(pub_key)
    encrypted = base64.b64encode(
        sealed_box.encrypt(secret_value.encode("utf-8"))
    ).decode("utf-8")

    # Secret 업데이트
    requests.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}",
        headers=headers,
        json={"encrypted_value": encrypted, "key_id": key_data["key_id"]},
        timeout=10
    ).raise_for_status()

    print(f"✅ GitHub Secret [{secret_name}] 업데이트 완료")


# ── Discord 알림 ───────────────────────────

def notify_discord(message: str):
    """Discord Webhook으로 토큰 갱신 결과 알림"""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        return
    try:
        requests.post(
            webhook_url,
            json={"content": message},
            timeout=10
        )
    except Exception as e:
        print(f"⚠️ Discord 알림 실패: {e}")


# ── 메인 갱신 로직 ─────────────────────────

def check_and_refresh_tokens():
    """
    Instagram + Threads 토큰 상태 확인
    → 30일 이하 남으면 자동 갱신
    → GitHub Secrets 자동 업데이트
    → Discord 알림 전송
    """
    status  = load_token_status()
    updated = False
    messages = []

    # ── Instagram 토큰 체크 ──
    ig_token     = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    ig_expires   = status.get("instagram_expires_at", 0)
    ig_days_left = days_until_expiry(ig_expires) if ig_expires else 0

    print(f"📸 Instagram 토큰 만료까지: {ig_days_left}일")

    if ig_days_left <= REFRESH_THRESHOLD_DAYS and ig_token:
        print("🔄 Instagram 토큰 갱신 시작...")
        try:
            ig_result = refresh_instagram_token(ig_token)
            status["instagram_expires_at"]      = ig_result["expires_at"]
            status["instagram_last_refreshed"]  = datetime.now(timezone.utc).isoformat()
            messages.append(f"✅ Instagram 토큰 갱신 완료 ({ig_result['expires_in'] // 86400}일 연장)")
            updated = True
            try:
                update_github_secret("INSTAGRAM_ACCESS_TOKEN", ig_result["access_token"])
            except Exception as e:
                print(f"⚠️ GitHub Secret 업데이트 실패 (수동 갱신 필요): {e}")
        except Exception as e:
            messages.append(f"❌ Instagram 토큰 갱신 실패: {e}")
            print(f"❌ Instagram 갱신 실패: {e}")

    # ── Threads 토큰 체크 ──
    th_token     = os.environ.get("THREADS_ACCESS_TOKEN", "")
    th_expires   = status.get("threads_expires_at", 0)
    th_days_left = days_until_expiry(th_expires) if th_expires else 0

    print(f"🧵 Threads 토큰 만료까지: {th_days_left}일")

    if not th_token:
        print("⏭️  Threads 토큰 미설정 - 갱신 스킵")
    elif th_days_left <= REFRESH_THRESHOLD_DAYS:
        print("🔄 Threads 토큰 갱신 시작...")
        try:
            th_result = refresh_threads_token(th_token)
            status["threads_expires_at"]     = th_result["expires_at"]
            status["threads_last_refreshed"] = datetime.now(timezone.utc).isoformat()
            messages.append(f"✅ Threads 토큰 갱신 완료 ({th_result['expires_in'] // 86400}일 연장)")
            updated = True
            try:
                update_github_secret("THREADS_ACCESS_TOKEN", th_result["access_token"])
            except Exception as e:
                print(f"⚠️ GitHub Secret 업데이트 실패 (수동 갱신 필요): {e}")
        except Exception as e:
            messages.append(f"❌ Threads 토큰 갱신 실패: {e}")
            print(f"❌ Threads 갱신 실패: {e}")

    if updated:
        save_token_status(status)
        print("💾 토큰 상태 저장 완료")
        notify_discord("🔑 [ai-card-publisher]\n" + "\n".join(messages))
    else:
        print("✅ 모든 토큰 정상 (갱신 불필요)")


if __name__ == "__main__":
    check_and_refresh_tokens()
