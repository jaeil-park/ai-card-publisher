import os
import json
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

ANALYTICS_FILE  = Path("analytics/posts.json")
WEBHOOK_URL     = os.environ.get("DISCORD_WEBHOOK_URL", "")

# 콘텐츠 타입별 월 운영비 (USD)
MONTHLY_COST_USD = 10.0
KRW_PER_USD      = 1380

# 콘텐츠 타입 한글 레이블
TYPE_LABEL = {
    "morning_briefing": "☀️ 아침 브리핑",
    "tech_trend":       "💻 개발 트렌드",
    "market_update":    "📊 시장 시황",
    "ai_tools":         "🛠️ AI 개발툴",
    "product_hunt":     "🚀 AI 신제품",
    "ai_tips":          "🧠 AI 비서 팁",
}


# ── 데이터 저장/로드 ───────────────────────────────────────

def _load() -> dict:
    if ANALYTICS_FILE.exists():
        with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"posts": []}


def _save(data: dict):
    ANALYTICS_FILE.parent.mkdir(exist_ok=True)
    with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 포스팅 기록 ────────────────────────────────────────────

def record_post(content_type: str, title: str, results: dict):
    """포스팅 완료 후 기록 저장 (main.py에서 호출)"""
    data = _load()
    now  = datetime.now(timezone.utc).isoformat()

    for platform, result in results.items():
        media_id = result.get("id", "")
        if not media_id:
            continue
        data["posts"].append({
            "media_id":     media_id,
            "platform":     platform,
            "content_type": content_type,
            "title":        title,
            "posted_at":    now,
            "insights":     {},
            "insights_at":  None,
        })

    _save(data)
    print(f"📊 Analytics 기록 완료 ({len(results)}개 플랫폼)")


# ── Instagram Insights 수집 ───────────────────────────────

def _fetch_instagram_insights(media_id: str, token: str) -> dict:
    """Instagram Graph API로 미디어 인사이트 수집 (24h 이후 가능)"""
    try:
        # 기본 지표 (like_count, comments_count)
        r1 = requests.get(
            f"https://graph.instagram.com/v24.0/{media_id}",
            params={"fields": "like_count,comments_count,timestamp", "access_token": token},
            timeout=10
        )
        basic = r1.json() if r1.ok else {}

        # 인사이트 지표 (impressions, reach, saved)
        r2 = requests.get(
            f"https://graph.instagram.com/v24.0/{media_id}/insights",
            params={"metric": "impressions,reach,saved", "access_token": token},
            timeout=10
        )
        insights_raw = {}
        if r2.ok:
            for item in r2.json().get("data", []):
                insights_raw[item["name"]] = item["values"][0]["value"] if item.get("values") else item.get("value", 0)

        return {
            "likes":       basic.get("like_count", 0),
            "comments":    basic.get("comments_count", 0),
            "impressions": insights_raw.get("impressions", 0),
            "reach":       insights_raw.get("reach", 0),
            "saved":       insights_raw.get("saved", 0),
        }
    except Exception as e:
        print(f"⚠️ Insights 수집 실패 ({media_id}): {e}")
        return {}


def refresh_insights():
    """24h 이상 지난 포스트 인사이트 업데이트"""
    data  = _load()
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    now   = datetime.now(timezone.utc)
    updated = 0

    for post in data["posts"]:
        if post["platform"] != "instagram":
            continue
        if post["insights_at"]:  # 이미 수집됨
            continue
        posted_at = datetime.fromisoformat(post["posted_at"])
        if (now - posted_at).total_seconds() < 86400:  # 24h 미만
            continue

        insights = _fetch_instagram_insights(post["media_id"], token)
        if insights:
            post["insights"]    = insights
            post["insights_at"] = now.isoformat()
            updated += 1

    if updated:
        _save(data)
        print(f"✅ Insights 업데이트: {updated}개 포스트")


# ── Discord 전송 ───────────────────────────────────────────

def _send_discord(embeds: list):
    if not WEBHOOK_URL:
        print("⚠️ DISCORD_WEBHOOK_URL 미설정")
        return
    try:
        res = requests.post(WEBHOOK_URL, json={"embeds": embeds}, timeout=10)
        if res.ok:
            print("📨 Discord 리포트 전송 완료")
        else:
            print(f"⚠️ Discord 전송 실패: {res.status_code}")
    except Exception as e:
        print(f"⚠️ Discord 전송 오류: {e}")


# ── 즉시 포스팅 알림 ──────────────────────────────────────

def notify_posted(content_type: str, title: str, platforms: list[str]):
    """포스팅 완료 즉시 Discord 알림"""
    label    = TYPE_LABEL.get(content_type, content_type)
    platform_str = " · ".join(p.capitalize() for p in platforms if p)
    kst_now  = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y.%m.%d %H:%M")

    embed = {
        "title":       f"✅ 포스팅 완료 | {label}",
        "description": f"**{title}**",
        "color":       0x00C851,
        "fields": [
            {"name": "📱 플랫폼",  "value": platform_str, "inline": True},
            {"name": "🕐 시간 (KST)", "value": kst_now,  "inline": True},
        ],
        "footer": {"text": "ai-card-publisher • AI Generated Content"},
    }
    _send_discord([embed])


# ── 일간 성과 리포트 ──────────────────────────────────────

def send_daily_report():
    """어제 포스팅된 콘텐츠의 Insights 기반 일간 리포트"""
    refresh_insights()
    data = _load()
    now  = datetime.now(timezone.utc)
    yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end   = yesterday_start + timedelta(days=1)

    # 어제 포스팅 + Insights 수집된 것만
    posts = [
        p for p in data["posts"]
        if p["platform"] == "instagram"
        and p["insights"]
        and yesterday_start <= datetime.fromisoformat(p["posted_at"]) < yesterday_end
    ]

    if not posts:
        _send_discord([{
            "title":       "📊 일간 리포트",
            "description": "어제 수집된 Insights 데이터가 없습니다.",
            "color":       0xAAAAAA,
        }])
        return

    # 집계
    total_impressions = sum(p["insights"].get("impressions", 0) for p in posts)
    total_reach       = sum(p["insights"].get("reach", 0)       for p in posts)
    total_likes       = sum(p["insights"].get("likes", 0)       for p in posts)
    total_saved       = sum(p["insights"].get("saved", 0)       for p in posts)
    total_comments    = sum(p["insights"].get("comments", 0)    for p in posts)

    # 베스트 포스트
    best = max(posts, key=lambda p: p["insights"].get("impressions", 0))

    # 참여율 = (좋아요 + 댓글 + 저장) / 노출 × 100
    eng_rate = ((total_likes + total_comments + total_saved) / max(total_impressions, 1)) * 100

    # 하루 비용 (KRW)
    daily_cost_krw = int((MONTHLY_COST_USD / 30) * KRW_PER_USD)

    # 포스트별 성과 라인
    post_lines = []
    for p in sorted(posts, key=lambda x: x["insights"].get("impressions", 0), reverse=True):
        label = TYPE_LABEL.get(p["content_type"], p["content_type"])
        imp   = p["insights"].get("impressions", 0)
        saved = p["insights"].get("saved", 0)
        post_lines.append(f"{label} | 노출 **{imp:,}** · 저장 **{saved}**")

    kst_date = (now + timedelta(hours=9) - timedelta(days=1)).strftime("%Y.%m.%d")

    embed = {
        "title":       f"📊 일간 성과 리포트 | {kst_date}",
        "color":       0x5865F2,
        "fields": [
            {
                "name":   "📈 전체 집계",
                "value":  (
                    f"노출 **{total_impressions:,}** · 도달 **{total_reach:,}**\n"
                    f"좋아요 **{total_likes}** · 저장 **{total_saved}** · 댓글 **{total_comments}**\n"
                    f"참여율 **{eng_rate:.2f}%**"
                ),
                "inline": False,
            },
            {
                "name":   "🏆 베스트 콘텐츠",
                "value":  f"{TYPE_LABEL.get(best['content_type'], '')} | **{best['title']}**\n노출 {best['insights'].get('impressions',0):,}",
                "inline": False,
            },
            {
                "name":   "📋 타입별 성과",
                "value":  "\n".join(post_lines) or "없음",
                "inline": False,
            },
            {
                "name":   "💰 오늘 운영비",
                "value":  f"약 **{daily_cost_krw:,}원**",
                "inline": True,
            },
        ],
        "footer": {"text": "ai-card-publisher • Insights는 게시 24h 후 반영"},
    }
    _send_discord([embed])


# ── 주간 ROI 리포트 ────────────────────────────────────────

def send_weekly_report():
    """주간 콘텐츠 타입별 성과 + ROI 분석"""
    refresh_insights()
    data = _load()
    now  = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    posts = [
        p for p in data["posts"]
        if p["platform"] == "instagram"
        and p["insights"]
        and datetime.fromisoformat(p["posted_at"]) >= week_ago
    ]

    if not posts:
        _send_discord([{"title": "📊 주간 ROI 리포트", "description": "이번 주 데이터 없음", "color": 0xAAAAAA}])
        return

    # 콘텐츠 타입별 집계
    type_stats: dict[str, dict] = {}
    for p in posts:
        ct = p["content_type"]
        if ct not in type_stats:
            type_stats[ct] = {"impressions": 0, "reach": 0, "saved": 0, "likes": 0, "count": 0}
        for k in ["impressions", "reach", "saved", "likes"]:
            type_stats[ct][k] += p["insights"].get(k, 0)
        type_stats[ct]["count"] += 1

    # 순위 정렬 (노출 기준)
    ranked = sorted(type_stats.items(), key=lambda x: x[1]["impressions"], reverse=True)

    ranking_lines = []
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"]
    for i, (ct, s) in enumerate(ranked):
        label   = TYPE_LABEL.get(ct, ct)
        eng     = ((s["likes"] + s["saved"]) / max(s["impressions"], 1)) * 100
        ranking_lines.append(
            f"{medals[i]} {label}\n"
            f"   노출 {s['impressions']:,} · 저장 {s['saved']} · 참여율 {eng:.1f}% ({s['count']}회)"
        )

    # 주간 비용/ROI
    weekly_cost_krw = int((MONTHLY_COST_USD / 4) * KRW_PER_USD)
    total_reach     = sum(s["reach"] for _, s in type_stats.items())

    kst_start = (week_ago + timedelta(hours=9)).strftime("%m.%d")
    kst_end   = (now      + timedelta(hours=9)).strftime("%m.%d")

    embed = {
        "title":       f"📊 주간 ROI 리포트 | {kst_start} – {kst_end}",
        "color":       0xFFAA00,
        "fields": [
            {
                "name":   "🏆 콘텐츠 타입 성과 순위",
                "value":  "\n".join(ranking_lines),
                "inline": False,
            },
            {
                "name":   "💰 주간 운영비",
                "value":  f"약 **{weekly_cost_krw:,}원** (월 {int(MONTHLY_COST_USD * KRW_PER_USD):,}원)",
                "inline": True,
            },
            {
                "name":   "👥 총 도달",
                "value":  f"**{total_reach:,}명**",
                "inline": True,
            },
            {
                "name":   "💡 ROI 팁",
                "value":  f"가장 성과 좋은 타입: **{TYPE_LABEL.get(ranked[0][0], '')}**\n해당 타입 비중을 늘리면 도달률 향상 기대",
                "inline": False,
            },
        ],
        "footer": {"text": "ai-card-publisher • 매주 월요일 자동 발송"},
    }
    _send_discord([embed])


if __name__ == "__main__":
    # 수동 실행 시 주간 리포트 즉시 전송
    send_weekly_report()
