"""
Meta(Threads/Instagram) 도배 방지 가드 — analytics/posts.json 히스토리 기반.

2026-07 계정정지 사고: card_news.yml cron이 하루 6회 실행되고, 매 실행마다
Instagram + Threads에 동시 게시하여 하루 최대 12건의 자동 게시가 매일
반복됨. Meta Community Standards(스팸 정책)는 "posting...at very high
frequencies"(수동/자동 불문 매우 높은 빈도의 게시)를 명시적으로 금지하며,
동일한 AI_FOOTER 템플릿이 매 게시물에 반복 삽입된 점도 "반복적 콘텐츠"
신호를 가중시킴. 이 두 신호가 겹쳐 Threads 계정이 정지된 것으로 판단.

analytics/posts.json은 이미 매 실행 후 git commit되어 워크플로 간 상태가
보존되므로(.token_status.json과 동일한 패턴), 별도 상태 파일 없이 이
기존 기록을 근거로 쿨다운·일일한도를 계산한다.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ANALYTICS_FILE = Path("analytics/posts.json")

# 플랫폼별 최소 게시 간격(시간) / 일일 게시 한도
# 2026-07 2차 개편: 크론을 1회/일(06:00 KST)로 축소. workflow_dispatch 수동
# 재실행이나 스케줄 중복 트리거로 "1일 1회" 원칙이 깨지는 것을 막는 최후 방어선.
MIN_INTERVAL_HOURS = {"instagram": 20.0, "threads": 20.0}
DAILY_CAP          = {"instagram": 1, "threads": 1}

# Meta 스팸 정책의 "참여 유도(engagement bait)" 조항 대응 — 이런 문구가
# 캡션에 들어가면 게시 자체를 차단한다. (giveaway-for-engagement, 잠금 콘텐츠 등)
_ENGAGEMENT_BAIT_PATTERNS = [
    re.compile(p) for p in [
        r"댓글\s*남기(면|시)",
        r"좋아요\s*누르(면|시)",
        r"공유하(면|시).{0,10}(무료|증정|혜택)",
        r"팔로우하(면|시).{0,10}(이벤트|경품|추첨)",
        r"태그하(면|시).{0,10}(당첨|증정)",
    ]
]


def _load_posts() -> list[dict]:
    if not ANALYTICS_FILE.exists():
        return []
    try:
        return json.loads(ANALYTICS_FILE.read_text(encoding="utf-8")).get("posts", [])
    except Exception:
        return []


def check_rate_limit(platform: str) -> tuple[bool, str]:
    """(게시 허용 여부, 차단 사유) 반환. analytics/posts.json 기록 기준."""
    posts = [p for p in _load_posts() if p.get("platform") == platform]
    if not posts:
        return True, ""

    now = datetime.now(timezone.utc)
    try:
        last_ts = max(datetime.fromisoformat(p["posted_at"]) for p in posts)
    except Exception:
        return True, ""  # 기록 파싱 실패 시 안전하게 통과 (기존 tistory 패턴과 동일 철학)

    elapsed_h = (now - last_ts).total_seconds() / 3600
    min_interval = MIN_INTERVAL_HOURS.get(platform, 3.0)
    if elapsed_h < min_interval:
        remain = min_interval - elapsed_h
        return False, (
            f"{platform} 도배 방지: 마지막 게시 후 {elapsed_h:.1f}h 경과 "
            f"(최소 {min_interval}h 필요, {remain:.1f}h 대기)"
        )

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = sum(
        1 for p in posts
        if datetime.fromisoformat(p["posted_at"]) >= today_start
    )
    cap = DAILY_CAP.get(platform, 3)
    if today_count >= cap:
        return False, f"{platform} 일일 게시 한도 도달 ({today_count}/{cap}) — Meta 스팸 정책 대응"

    return True, ""


def check_content_policy(caption: str) -> tuple[bool, str]:
    """Meta 스팸 정책의 참여 유도(engagement bait) 문구 검사."""
    for pattern in _ENGAGEMENT_BAIT_PATTERNS:
        if pattern.search(caption):
            return False, f"참여 유도(engagement bait) 문구 감지: '{pattern.pattern}'"
    return True, ""
