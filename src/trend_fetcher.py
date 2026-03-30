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
    "morning_briefing":  {"emoji": "☀️", "label": "아침 종합 브리핑"},
    "bigtech_news":      {"emoji": "🏢", "label": "빅테크 IT 뉴스"},
    "market_update":     {"emoji": "📊", "label": "시장 시황"},
    "startup_trend":     {"emoji": "🦄", "label": "스타트업 트렌드"},
    "product_hunt":      {"emoji": "🚀", "label": "테크 신제품"},
    "ai_tips":           {"emoji": "🧠", "label": "AI 비서 팁"},
    "vibe_coding":       {"emoji": "☕", "label": "바이브코딩 티타임"},
    "weekly_review":     {"emoji": "📅", "label": "주간 핵심 정리"},
    # ── 브랜드 스포트라이트 ─────────────────────────────────
    "openai_spotlight":  {"emoji": "🤖", "label": "OpenAI 스포트라이트"},
    "claude_spotlight":  {"emoji": "🧬", "label": "Claude AI 스포트라이트"},
    "coingecko_report":  {"emoji": "📈", "label": "CoinGecko AI 마켓"},
    # ── 신규 추가 ───────────────────────────────────────────
    "gemini_spotlight":  {"emoji": "✨", "label": "Google Gemini 스포트라이트"},
    "kr_tech_news":      {"emoji": "🇰🇷", "label": "국내 테크 뉴스"},
    "defi_web3":         {"emoji": "🌐", "label": "DeFi/Web3 트렌드"},
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

    # 21:00 슬롯 7일 순환 (월~일)
    _21H_ROTATION = [
        "ai_tips",           # 월 (0)
        "vibe_coding",       # 화 (1)
        "openai_spotlight",  # 수 (2)
        "claude_spotlight",  # 목 (3)
        "gemini_spotlight",  # 금 (4) – Google AI 스포트라이트
        "defi_web3",         # 토 (5) – DeFi/Web3 트렌드
        "weekly_review",     # 일 (6) – 20:00과 동일, 아래 조건에서 먼저 처리됨
    ]
    if hour >= 21:
        return _21H_ROTATION[weekday]

    # 9시 슬롯: 짝수 요일(월수금일) → bigtech_news, 홀수(화목토) → kr_tech_news
    if hour == 9:
        return "bigtech_news" if weekday % 2 == 0 else "kr_tech_news"

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
        year = datetime.now().year
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": f"Claude Code Cursor Copilot Windsurf AI coding tool {year}", "gl": "kr", "hl": "ko", "num": 5},
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
        year = datetime.now().year
        res = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": f"site:producthunt.com AI tool {year}", "num": 5},
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
            json={"q": f"스타트업 투자 시리즈 Series 유니콘 VC AI 신기술 {datetime.now().year}", "gl": "kr", "hl": "ko", "num": 6},
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
            json={"q": f"vibe coding Claude Code Cursor Windsurf AI coding 바이브코딩 {datetime.now().year}", "gl": "kr", "hl": "ko", "num": 6},
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


def fetch_openai_spotlight() -> list[dict]:
    """Serper: OpenAI / GPT 최신 공식 발표 및 동향"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": f"OpenAI GPT ChatGPT 최신 발표 업데이트 {datetime.now().year}", "gl": "kr", "hl": "ko", "num": 6},
            timeout=10
        )
        res.raise_for_status()
        return [
            {"title": i["title"], "snippet": i.get("snippet", ""),
             "source": i.get("source", ""), "link": i.get("link", "")}
            for i in res.json().get("news", [])
        ]
    except Exception as e:
        print(f"⚠️ OpenAI 뉴스 수집 실패: {e}")
        return [{"title": "OpenAI 최신 소식", "snippet": "GPT 관련 최신 동향을 확인하세요", "link": ""}]


def fetch_claude_spotlight() -> list[dict]:
    """Serper: Anthropic / Claude AI 최신 공식 발표 및 동향"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": f"Anthropic Claude AI 최신 업데이트 Constitutional AI {datetime.now().year}", "gl": "kr", "hl": "ko", "num": 6},
            timeout=10
        )
        res.raise_for_status()
        return [
            {"title": i["title"], "snippet": i.get("snippet", ""),
             "source": i.get("source", ""), "link": i.get("link", "")}
            for i in res.json().get("news", [])
        ]
    except Exception as e:
        print(f"⚠️ Claude 뉴스 수집 실패: {e}")
        return [{"title": "Claude AI 최신 소식", "snippet": "Anthropic Claude 관련 최신 동향을 확인하세요", "link": ""}]


def fetch_coingecko_ai_tokens() -> list[dict]:
    """CoinGecko API: AI 관련 토큰 카테고리 시황"""
    try:
        # AI & Big Data 카테고리 코인
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "category": "artificial-intelligence",
                "order": "market_cap_desc",
                "per_page": 8,
                "page": 1,
                "price_change_percentage": "24h,7d",
            },
            timeout=10
        )
        res.raise_for_status()
        return [
            {
                "name":        c["name"],
                "symbol":      c["symbol"].upper(),
                "price_usd":   f"${c['current_price']:,.4f}",
                "change_24h":  f"{c.get('price_change_percentage_24h', 0):.2f}%",
                "change_7d":   f"{c.get('price_change_percentage_7d_in_currency', 0):.2f}%",
                "market_cap":  f"${c.get('market_cap', 0) / 1e6:.1f}M",
            }
            for c in res.json()
        ]
    except Exception as e:
        print(f"⚠️ CoinGecko AI 토큰 수집 실패: {e}")
        return fetch_crypto()  # 폴백: 일반 코인 시황


def fetch_gemini_spotlight() -> list[dict]:
    """Serper: Google Gemini / DeepMind 최신 공식 발표 및 동향"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": f"Google Gemini DeepMind AI 최신 업데이트 발표 {datetime.now().year}", "gl": "kr", "hl": "ko", "num": 6},
            timeout=10
        )
        res.raise_for_status()
        return [
            {"title": i["title"], "snippet": i.get("snippet", ""),
             "source": i.get("source", ""), "link": i.get("link", "")}
            for i in res.json().get("news", [])
        ]
    except Exception as e:
        print(f"⚠️ Gemini 뉴스 수집 실패: {e}")
        return [{"title": "Google Gemini 최신 소식", "snippet": "Google AI 관련 최신 동향을 확인하세요", "link": ""}]


def fetch_kr_tech_news() -> list[dict]:
    """Serper: 국내 테크 뉴스 (네이버·카카오·삼성·LG AI 동향)"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": f"네이버 카카오 삼성 LG SK AI 인공지능 기술 뉴스 {datetime.now().year}", "gl": "kr", "hl": "ko", "num": 6},
            timeout=10
        )
        res.raise_for_status()
        return [
            {"title": i["title"], "snippet": i.get("snippet", ""),
             "source": i.get("source", ""), "link": i.get("link", "")}
            for i in res.json().get("news", [])
        ]
    except Exception as e:
        print(f"⚠️ 국내 테크 뉴스 수집 실패: {e}")
        return []


def fetch_defi_web3() -> list[dict]:
    """CoinGecko API: DeFi 프로토콜 시황 + Serper: Web3 최신 트렌드"""
    results = []
    # DeFi TVL 상위 코인
    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "category": "decentralized-finance-defi",
                "order": "market_cap_desc",
                "per_page": 5,
                "price_change_percentage": "24h,7d",
            },
            timeout=10
        )
        res.raise_for_status()
        results = [
            {
                "name":       c["name"],
                "symbol":     c["symbol"].upper(),
                "price_usd":  f"${c['current_price']:,.4f}",
                "change_24h": f"{c.get('price_change_percentage_24h', 0):.2f}%",
                "market_cap": f"${c.get('market_cap', 0) / 1e6:.1f}M",
            }
            for c in res.json()
        ]
    except Exception as e:
        print(f"⚠️ DeFi 시황 수집 실패: {e}")

    # Web3 최신 뉴스 보완
    try:
        news_res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": f"DeFi Web3 블록체인 탈중앙화 최신 트렌드 {datetime.now().year}", "gl": "kr", "hl": "ko", "num": 4},
            timeout=10
        )
        news_res.raise_for_status()
        results += [
            {"title": i["title"], "snippet": i.get("snippet", ""), "link": i.get("link", "")}
            for i in news_res.json().get("news", [])
        ]
    except Exception as e:
        print(f"⚠️ Web3 뉴스 수집 실패: {e}")

    return results


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
    # ── 브랜드 스포트라이트 ─────────────────────────────────
    elif content_type == "openai_spotlight":
        return {
            "news":   fetch_openai_spotlight(),
            "github": fetch_github_trending()[:2],
        }
    elif content_type == "claude_spotlight":
        return {
            "news":   fetch_claude_spotlight(),
            "github": fetch_github_trending()[:2],
        }
    elif content_type == "coingecko_report":
        return {
            "crypto": fetch_coingecko_ai_tokens(),
            "news":   fetch_ai_news()[:3],
        }
    elif content_type == "gemini_spotlight":
        return {
            "news":   fetch_gemini_spotlight(),
            "github": fetch_github_trending()[:2],
        }
    elif content_type == "kr_tech_news":
        return {
            "news":   fetch_kr_tech_news(),
            "github": fetch_github_trending()[:2],
        }
    elif content_type == "defi_web3":
        return {
            "news":   fetch_defi_web3(),
            "crypto": fetch_crypto()[:2],
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

        points = content.get("slide2", {}).get("points", [])
        points_text = ""
        if isinstance(points, list):
            points_text = " ".join([
                f"{p.get('tag', '')} {p.get('text', '')} {p.get('context', '')}" if isinstance(p, dict) else str(p)
                for p in points
            ])

        all_text = " ".join([
            content.get("caption", ""),
            content.get("slide1", {}).get("headline", ""),
            content.get("slide1", {}).get("sub", ""),
            content.get("slide2", {}).get("headline", ""),
            points_text,
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

[슬라이드 2 - 상세: 왜/어떻게 - 스크롤 유도 (인포그래픽)]
- headline: "왜?" "어떻게?" 형태 질문. 15자 이내.
- points: 팩트 3가지. 원인→영향→전망 구조 권장.
  각 항목:
  - tag: 2~3자 카테고리 레이블 (예: "원인" "영향" "전망" "배경" "수치" "전략" "현황")
  - text: 핵심 팩트 + 수치. 25자 이내.
  - context: 배경 설명 또는 추가 데이터. 이유/근거 포함. 35자 이내.

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
    "points": [
      {{"tag": "원인", "text": "핵심팩트+수치", "context": "배경설명/근거"}},
      {{"tag": "영향", "text": "핵심팩트+수치", "context": "배경설명/근거"}},
      {{"tag": "전망", "text": "핵심팩트+수치", "context": "배경설명/근거"}}
    ]
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
