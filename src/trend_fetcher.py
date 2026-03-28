import os
import json
import requests
from openai import OpenAI
from datetime import datetime, timedelta, date, timezone

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# ── 콘텐츠 타입 스케줄 (KST 기준) ──────────────────────────
CONTENT_SCHEDULE = {
    6:  "morning_briefing",  # ☀️ 아침 종합 뉴스 브리핑 (AI + 테크 + 경제)
    9:  "bigtech_news",      # 🏢 빅테크 IT 뉴스 + 원문 링크 공유
    12: "market_update",     # 📊 코인 + 글로벌 증시 + 환율
    15: "startup_trend",     # 🦄 스타트업/VC 투자 + 신기술 트렌드
    18: "product_hunt",      # 🚀 테크/AI 신제품 발견
    21: "ai_tips",           # 🧠 AI 비서 실전 팁
}

CONTENT_META = {
    "morning_briefing": {"emoji": "☀️", "label": "아침 종합 브리핑"},
    "bigtech_news":     {"emoji": "🏢", "label": "빅테크 IT 뉴스"},
    "market_update":    {"emoji": "📊", "label": "시장 시황"},
    "startup_trend":    {"emoji": "🦄", "label": "스타트업 트렌드"},
    "product_hunt":     {"emoji": "🚀", "label": "테크 신제품"},
    "ai_tips":          {"emoji": "🧠", "label": "AI 비서 팁"},
    "vibe_coding":      {"emoji": "☕", "label": "바이브코딩 티타임"},
    "weekly_review":    {"emoji": "📅", "label": "주간 핵심 정리"},
}


# ── 콘텐츠 타입 자동 결정 ──────────────────────────────────

def get_content_type() -> str:
    """현재 KST 시각 기준으로 콘텐츠 타입 자동 결정

    21:00 슬롯 로테이션:
      - 월/수/금 → ai_tips (AI 비서 실전 팁)
      - 화/목/토 → vibe_coding (바이브코딩 티타임)
      - 일 20:00  → weekly_review (한 주 핵심 정리)
    """
    now     = datetime.now(timezone.utc) + timedelta(hours=9)
    hour    = now.hour
    weekday = now.weekday()  # 0=월 … 6=일

    # 일요일 20:00: 주간 정리
    if weekday == 6 and hour == 20:
        return "weekly_review"

    # 21:00 슬롯: 화(1)/목(3)/토(5) → 바이브코딩, 나머지 → AI 팁
    if hour >= 21:
        return "vibe_coding" if weekday in (1, 3, 5) else "ai_tips"

    for h in sorted(CONTENT_SCHEDULE.keys(), reverse=True):
        if hour >= h:
            return CONTENT_SCHEDULE[h]
    return "morning_briefing"


# ── 데이터 수집 함수들 ─────────────────────────────────────

def fetch_ai_news() -> list[dict]:
    """Serper API: AI 최신 뉴스 (링크 포함)"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": "AI 인공지능 최신 뉴스", "gl": "kr", "hl": "ko", "num": 5},
            timeout=10
        )
        res.raise_for_status()
        return [
            {"title": i["title"], "snippet": i.get("snippet", ""),
             "source": i.get("source", ""), "link": i.get("link", "")}
            for i in res.json().get("news", [])
        ]
    except Exception as e:
        print(f"⚠️ AI 뉴스 수집 실패: {e}")
        return [{"title": "AI 트렌드", "snippet": "최신 AI 동향을 확인하세요", "link": ""}]


def fetch_github_trending() -> list[dict]:
    """GitHub API: 이번 주 스타 급증 AI 레포지토리"""
    try:
        since = (date.today() - timedelta(days=7)).isoformat()
        res = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": f"topic:ai created:>{since}", "sort": "stars", "order": "desc", "per_page": 5},
            headers={"Accept": "application/vnd.github+json"},
            timeout=10
        )
        res.raise_for_status()
        return [
            {
                "name": r["full_name"],
                "description": (r.get("description") or "")[:80],
                "stars": f"{r['stargazers_count']:,}⭐",
                "language": r.get("language", ""),
            }
            for r in res.json().get("items", [])
        ]
    except Exception as e:
        print(f"⚠️ GitHub Trending 수집 실패: {e}")
        return []


def fetch_hacker_news() -> list[dict]:
    """Hacker News Algolia API: AI/LLM 화제글"""
    try:
        res = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"tags": "story", "query": "AI LLM Claude GPT agent", "hitsPerPage": 5},
            timeout=10
        )
        res.raise_for_status()
        return [
            {"title": h["title"], "points": h.get("points", 0)}
            for h in res.json().get("hits", [])
        ]
    except Exception as e:
        print(f"⚠️ Hacker News 수집 실패: {e}")
        return []


def fetch_crypto() -> list[dict]:
    """CoinGecko 무료 API: 코인 시황"""
    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={"vs_currency": "krw", "ids": "bitcoin,ethereum,solana", "order": "market_cap_desc"},
            timeout=10
        )
        res.raise_for_status()
        return [
            {
                "name": c["name"],
                "price_krw": f"{c['current_price']:,.0f}원",
                "change_24h": f"{c['price_change_percentage_24h']:.2f}%"
            }
            for c in res.json()
        ]
    except Exception as e:
        print(f"⚠️ 코인 시황 수집 실패: {e}")
        return []


def fetch_stock_market() -> list[dict]:
    """Yahoo Finance 무료 API: 글로벌 증시"""
    symbols = {"KOSPI": "^KS11", "NASDAQ": "^IXIC", "S&P500": "^GSPC"}
    results = []
    for name, symbol in symbols.items():
        try:
            res = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"interval": "1d", "range": "2d"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )
            data   = res.json()["chart"]["result"][0]
            close  = data["indicators"]["quote"][0]["close"]
            prev, curr = close[-2], close[-1]
            change = ((curr - prev) / prev) * 100
            results.append({"name": name, "value": f"{curr:,.2f}", "change_1d": f"{change:+.2f}%"})
        except Exception as e:
            print(f"⚠️ {name} 수집 실패: {e}")
    return results


def fetch_ai_tools_news() -> list[dict]:
    """Serper: AI 개발툴 최신 동향"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": "Claude Code Cursor Copilot Windsurf AI coding tool 2025", "gl": "kr", "hl": "ko", "num": 5},
            timeout=10
        )
        res.raise_for_status()
        return [{"title": i["title"], "snippet": i.get("snippet", "")}
                for i in res.json().get("news", [])]
    except Exception as e:
        print(f"⚠️ AI 개발툴 뉴스 수집 실패: {e}")
        return []


def fetch_product_hunt() -> list[dict]:
    """Serper: 테크/AI 신제품 (링크 포함)"""
    try:
        res = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": "site:producthunt.com AI tool 2025", "num": 5},
            timeout=10
        )
        res.raise_for_status()
        return [
            {"title": i["title"], "snippet": i.get("snippet", ""), "link": i.get("link", "")}
            for i in res.json().get("organic", [])
        ]
    except Exception as e:
        print(f"⚠️ Product Hunt 수집 실패: {e}")
        return []


def fetch_bigtech_news() -> list[dict]:
    """Serper: 빅테크(Apple/Google/Meta/MS/Amazon/Nvidia/TSMC) IT 뉴스 + 링크"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": "Apple Google Meta Microsoft Amazon Nvidia TSMC 빅테크 IT 뉴스", "gl": "kr", "hl": "ko", "num": 6},
            timeout=10
        )
        res.raise_for_status()
        return [
            {"title": i["title"], "snippet": i.get("snippet", ""),
             "source": i.get("source", ""), "link": i.get("link", "")}
            for i in res.json().get("news", [])
        ]
    except Exception as e:
        print(f"⚠️ 빅테크 뉴스 수집 실패: {e}")
        return []


def fetch_startup_trend() -> list[dict]:
    """Serper: 스타트업 투자/VC + 신기술 트렌드 + 링크"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": "스타트업 투자 시리즈 Series 유니콘 VC AI 신기술 2025", "gl": "kr", "hl": "ko", "num": 6},
            timeout=10
        )
        res.raise_for_status()
        return [
            {"title": i["title"], "snippet": i.get("snippet", ""),
             "source": i.get("source", ""), "link": i.get("link", "")}
            for i in res.json().get("news", [])
        ]
    except Exception as e:
        print(f"⚠️ 스타트업 트렌드 수집 실패: {e}")
        return []


# ── 콘텐츠 타입별 데이터 수집 ─────────────────────────────

def fetch_vibe_coding_news() -> list[dict]:
    """Serper: 바이브코딩 + AI 코딩 도구 최신 화제 + 링크"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": "vibe coding Claude Code Cursor Windsurf AI coding 바이브코딩 2025", "gl": "kr", "hl": "ko", "num": 6},
            timeout=10
        )
        res.raise_for_status()
        return [
            {"title": i["title"], "snippet": i.get("snippet", ""),
             "source": i.get("source", ""), "link": i.get("link", "")}
            for i in res.json().get("news", [])
        ]
    except Exception as e:
        print(f"⚠️ 바이브코딩 뉴스 수집 실패: {e}")
        return []


def fetch_weekly_summary() -> list[dict]:
    """이번 주 AI 핵심 뉴스 (Serper 주간 검색)"""
    try:
        week_ago = (datetime.now(timezone.utc) + timedelta(hours=9) - timedelta(days=7)).strftime("%Y-%m-%d")
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": f"AI 인공지능 주요 뉴스 after:{week_ago}", "gl": "kr", "hl": "ko", "num": 8},
            timeout=10
        )
        res.raise_for_status()
        return [{"title": i["title"], "snippet": i.get("snippet", "")}
                for i in res.json().get("news", [])]
    except Exception as e:
        print(f"⚠️ 주간 요약 수집 실패: {e}")
        return fetch_ai_news()


def collect_data(content_type: str) -> dict:
    """콘텐츠 타입에 맞는 데이터 수집"""
    print(f"📡 데이터 수집 중: {content_type}")
    if content_type == "morning_briefing":
        # 종합 브리핑: AI 뉴스 + 코인 시황 + 빅테크 헤드라인
        return {
            "news":   fetch_ai_news(),
            "crypto": fetch_crypto()[:2],
            "bigtech": fetch_bigtech_news()[:2],
        }
    elif content_type == "bigtech_news":
        # 빅테크 IT 뉴스 (링크 포함 → Threads에서 공유)
        return {"news": fetch_bigtech_news()}
    elif content_type == "market_update":
        return {"crypto": fetch_crypto(), "stock": fetch_stock_market()}
    elif content_type == "startup_trend":
        # 스타트업/VC 트렌드 + GitHub 급성장 레포
        return {"news": fetch_startup_trend(), "github": fetch_github_trending()[:3]}
    elif content_type == "product_hunt":
        return {"products": fetch_product_hunt(), "news": fetch_ai_news()[:2]}
    elif content_type == "ai_tips":
        return {"news": fetch_ai_news()[:3]}
    elif content_type == "vibe_coding":
        # 바이브코딩 뉴스 + HN 커뮤니티 반응 + GitHub 핫 레포
        return {
            "news":   fetch_vibe_coding_news(),
            "hn":     fetch_hacker_news(),
            "github": fetch_github_trending()[:2],
        }
    elif content_type == "weekly_review":
        return {
            "news":   fetch_weekly_summary(),
            "crypto": fetch_crypto(),
            "github": fetch_github_trending()[:3],
        }
    return {}


# ── GPT 콘텐츠 생성 ────────────────────────────────────────

def generate_card_content(theme: str, news: list, crypto: list) -> dict:
    """GPT-4o로 Instagram 캐러셀 3슬라이드 팩트 기반 콘텐츠 생성

    Instagram 가이드라인 반영:
    - 슬라이드 형식 > 단일 이미지 (도달 성과 우수)
    - 슬라이드 1: 첫 3초 안에 관심 유도 (큰 수치/팩트 훅)
    - 슬라이드 2: 상세 내용으로 스크롤 유도
    - 슬라이드 3: 핵심 요약 + 댓글 CTA (깊은 참여 유도)
    - 낚시성 콘텐츠 금지: 팩트/수치 기반
    """

    def remove_duplicate_words(content: dict) -> dict:
        import re
        from collections import Counter

        all_text = " ".join([
            content.get("caption", ""),
            content.get("slide1", {}).get("headline", ""),
            content.get("slide1", {}).get("sub", ""),
            content.get("slide2", {}).get("headline", ""),
            " ".join(content.get("slide2", {}).get("points", [])),
            content.get("slide3", {}).get("takeaway", ""),
        ])
        words = re.findall(r'[가-힣a-zA-Z]{2,}', all_text)
        duplicates = [w for w, c in Counter(words).items() if c >= 3]
        if duplicates:
            print(f"⚠️ 중복 단어 감지: {duplicates}")
        return content

    # 테마별 특별 톤/형식 지침
    THEME_GUIDES: dict[str, str] = {
        "바이브코딩 티타임": """
[바이브코딩 티타임 특별 규칙]
- 전체 톤: 개발자 친구와 커피 마시며 나누는 가벼운 대화체
- stat: 시간 절약/생산성 수치 우선 (예: "10배 속도", "3분 완성", "100줄 절약")
- slide2 포인트: 반드시 실제 써먹을 수 있는 프롬프트 예시 1개 이상 포함
  형식: '프롬프트: "..."' 또는 '팁: ...'
- slide3 cta_question: 참여 유도 질문 (예: "바이브코딩 써본 분? 경험 공유해주세요!")
- dalle_prompt: cozy coding setup, coffee cup next to laptop, warm ambient light,
  casual developer workspace, photorealistic
- caption: 친근하고 공감 가는 톤, "저도 써봤는데..." 같은 1인칭 경험 느낌
""",
    }

    theme_extra = THEME_GUIDES.get(theme, "")

    prompt = f"""
당신은 Instagram 성장 전문 카드뉴스 에디터입니다.
슬라이드(캐러셀) 3장 구성으로 팩트 기반 카드뉴스를 만드세요.

Instagram 공식 가이드라인:
- 슬라이드는 단일 사진보다 도달 성과가 더 좋음
- 첫 슬라이드에서 3초 안에 관심 유도 필수
- 공감/충분히 공유될 수 있는 콘텐츠 제작
- 낚시성/오해 소지 있는 표현 절대 금지
- 댓글 참여 유도로 깊은 참여(engagement) 집중
{theme_extra}
[입력 데이터]
테마: {theme}
AI 뉴스: {json.dumps(news, ensure_ascii=False)}
코인 시황: {json.dumps(crypto, ensure_ascii=False)}

[슬라이드 1 - 훅: 첫 3초 안에 관심 유도]
- stat: 가장 임팩트 있는 수치 하나. 6자 이내. (예: "+9.2%", "GPT-5", "1조원", "$1T")
- headline: 수치를 설명하는 임팩트 제목. 12자 이내.
- sub: stat이 나타내는 맥락/기간. 20자 이내.
  예: "이번 주 GitHub 스타 획득", "BTC 24시간 변동률"
  절대 금지: "X개 소개", "총 X건", "핵심 N가지" 등 슬라이드 2 항목 수 언급
- dalle_prompt: 주제와 직접 연관된 photorealistic 뉴스 사진 장면 (영문, 100자 이내)
  예시: "Bitcoin gold coin on dark financial chart, photorealistic, cinematic lighting"

[슬라이드 2 - 상세: 왜/어떻게 - 스크롤 유도]
- headline: "왜?" "어떻게?" 형태 질문. 15자 이내.
- points: 팩트 3가지. 각 항목 수치 포함, 30자 이내. 서로 다른 관점.

[슬라이드 3 - 요약 + CTA: 댓글 참여 유도]
- takeaway: 핵심 결론 한 문장. 25자 이내.
- cta_question: 댓글을 유도하는 열린 질문. 30자 이내. (예: "BTC 올해 전망 어떻게 보시나요?")
- follow_cta: 팔로우 유도 문구. 20자 이내.

[캡션 규칙 - Instagram 가이드라인 준수]
- 첫 줄: 강한 훅 (질문 또는 놀라운 사실. 본인 목소리로)
- 중간: 핵심 내용 2문장
- 마지막 줄: 댓글 유도 질문 (슬라이드3 cta_question과 다른 표현)
- 250자 이내, 이모지 포함
- 오해 소지/낚시성 표현 금지

[중복 단어 금지]
- AI/인공지능 → AI만 사용
- 코인/암호화폐/가상화폐 → 코인만 사용
- 전체 슬라이드에서 동일 단어 3회 이상 사용 금지

반드시 아래 JSON 형식으로만 응답 (마크다운, 설명 없이 JSON만):
{{
  "slide1": {{
    "stat": "핵심수치",
    "headline": "임팩트 제목",
    "sub": "부제목",
    "dalle_prompt": "photorealistic news photo, ..."
  }},
  "slide2": {{
    "headline": "왜 이런 일이?",
    "points": ["팩트1+수치", "팩트2+수치", "팩트3+수치"]
  }},
  "slide3": {{
    "takeaway": "핵심 결론",
    "cta_question": "댓글 유도 질문?",
    "follow_cta": "팔로우하면 매일 소식!"
  }},
  "caption": "훅문장\\n\\n핵심내용 2문장\\n\\n댓글유도질문",
  "hashtags": "#팩트 #수치 포함 해시태그 10개"
}}
"""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    content = json.loads(resp.choices[0].message.content)
    return remove_duplicate_words(content)
