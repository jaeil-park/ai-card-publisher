import os
import json
import requests
from openai import OpenAI
from datetime import datetime, timedelta, date

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# ── 콘텐츠 타입 스케줄 (KST 기준) ──────────────────────────
CONTENT_SCHEDULE = {
    6:  "morning_briefing",  # ☀️ 아침 AI 뉴스 브리핑
    9:  "tech_trend",        # 💻 GitHub + HN 개발 트렌드
    12: "market_update",     # 📊 코인 + 글로벌 증시
    15: "ai_tools",          # 🛠️ AI 개발툴 비교/팁
    18: "product_hunt",      # 🚀 AI 신제품 발견
    21: "ai_tips",           # 🧠 AI 비서 실전 팁
}

CONTENT_META = {
    "morning_briefing": {"emoji": "☀️", "label": "아침 AI 브리핑",  "bg_style": "bright sunrise digital newsroom, blue gold gradient"},
    "tech_trend":       {"emoji": "💻", "label": "개발 트렌드",     "bg_style": "dark coding terminal, green matrix neon, github vibes"},
    "market_update":    {"emoji": "📊", "label": "시장 시황",       "bg_style": "financial trading floor, dark blue red candlestick chart"},
    "ai_tools":         {"emoji": "🛠️", "label": "AI 개발툴",      "bg_style": "futuristic IDE interface, purple cyan glow, tool icons"},
    "product_hunt":     {"emoji": "🚀", "label": "AI 신제품",       "bg_style": "product launch stage, orange white spotlight, startup energy"},
    "ai_tips":          {"emoji": "🧠", "label": "AI 비서 팁",      "bg_style": "mind map neural network, teal purple gradient, productivity"},
}


# ── 콘텐츠 타입 자동 결정 ──────────────────────────────────

def get_content_type() -> str:
    """현재 KST 시각 기준으로 콘텐츠 타입 자동 결정"""
    hour = (datetime.utcnow() + timedelta(hours=9)).hour
    # 정각 매핑, 사이 시간은 가장 가까운 이전 슬롯
    for h in sorted(CONTENT_SCHEDULE.keys(), reverse=True):
        if hour >= h:
            return CONTENT_SCHEDULE[h]
    return "morning_briefing"


# ── 데이터 수집 함수들 ─────────────────────────────────────

def fetch_ai_news() -> list[dict]:
    """Serper API: AI 최신 뉴스"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": "AI 인공지능 최신 뉴스", "gl": "kr", "hl": "ko", "num": 5},
            timeout=10
        )
        res.raise_for_status()
        return [{"title": i["title"], "snippet": i.get("snippet", "")}
                for i in res.json().get("news", [])]
    except Exception as e:
        print(f"⚠️ AI 뉴스 수집 실패: {e}")
        return [{"title": "AI 트렌드", "snippet": "최신 AI 동향을 확인하세요"}]


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
    """Serper: AI 개발툴 최신 동향 (Claude Code, Cursor, Copilot 등)"""
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
    """Serper: Product Hunt AI 신제품"""
    try:
        res = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": os.environ.get("SERPER_API_KEY", "")},
            json={"q": "site:producthunt.com AI tool 2025", "num": 5},
            timeout=10
        )
        res.raise_for_status()
        return [{"title": i["title"], "snippet": i.get("snippet", "")}
                for i in res.json().get("organic", [])]
    except Exception as e:
        print(f"⚠️ Product Hunt 수집 실패: {e}")
        return []


# ── 콘텐츠 타입별 데이터 수집 ─────────────────────────────

def collect_data(content_type: str) -> dict:
    """콘텐츠 타입에 맞는 데이터 수집"""
    print(f"📡 데이터 수집 중: {content_type}")
    if content_type == "morning_briefing":
        return {"news": fetch_ai_news()}

    elif content_type == "tech_trend":
        return {"github": fetch_github_trending(), "hn": fetch_hacker_news()}

    elif content_type == "market_update":
        return {"crypto": fetch_crypto(), "stock": fetch_stock_market()}

    elif content_type == "ai_tools":
        return {"tools_news": fetch_ai_tools_news(), "hn": fetch_hacker_news()}

    elif content_type == "product_hunt":
        return {"products": fetch_product_hunt(), "news": fetch_ai_news()[:2]}

    elif content_type == "ai_tips":
        return {"news": fetch_ai_news()[:3]}

    return {}


# ── GPT 콘텐츠 생성 ────────────────────────────────────────

PROMPTS = {
    "morning_briefing": """
오늘 아침 독자가 출근길에 빠르게 훑어볼 AI 뉴스 브리핑 카드를 만드세요.
핵심만 3가지, 읽는 데 30초 이내로 소화 가능해야 합니다.
CTA: "오늘도 AI와 함께 시작해요! 💪 저장해두고 틈틈이 확인하세요"
""",
    "tech_trend": """
개발자 커뮤니티에서 화제인 GitHub 레포와 HN 기사를 기반으로
'이번 주 놓치면 안 될 AI 개발 트렌드' 카드를 만드세요.
스타 수, 언어, 핵심 기능을 수치와 함께 언급하세요.
CTA: "팔로우하면 매일 핫한 개발 트렌드를 받아볼 수 있어요 🔔"
""",
    "market_update": """
코인과 글로벌 증시 데이터를 분석해 오늘의 시장 흐름을 한눈에 보여주는 카드를 만드세요.
수치는 반드시 포함하고, 짧은 시장 해석 1문장을 추가하세요.
CTA: "여러분의 투자 전략은? 댓글로 알려주세요 💬"
""",
    "ai_tools": """
Claude Code, Cursor, GitHub Copilot, Windsurf 등 AI 개발툴 최신 소식을 기반으로
개발자가 바로 써먹을 수 있는 팁이나 비교 카드를 만드세요.
실제 사용 예시나 단축키, 프롬프트 예시를 포함하면 좋습니다.
CTA: "어떤 AI 코딩툴 쓰세요? 댓글로 공유해주세요! 🛠️"
""",
    "product_hunt": """
오늘 Product Hunt에서 주목받는 AI 신제품/서비스를 소개하는 카드를 만드세요.
제품명, 핵심 기능, 무료/유료 여부, 사용 대상을 간결하게 담으세요.
CTA: "써보고 싶은 제품 있나요? 댓글로 알려주세요 🚀"
""",
    "ai_tips": """
일반인과 직장인이 오늘 당장 써먹을 수 있는 AI 비서 활용 팁 카드를 만드세요.
ChatGPT, Claude, Gemini 등에서 바로 사용 가능한 프롬프트 예시를 포함하세요.
CTA: "이 팁 써보셨나요? 결과를 댓글로 공유해주세요 🧠"
""",
}


def generate_card_content(content_type: str, data: dict) -> dict:
    """GPT-4o로 콘텐츠 타입에 맞는 카드뉴스 생성"""
    meta     = CONTENT_META[content_type]
    kst_date = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y.%m.%d %H:%M")
    prompt   = PROMPTS[content_type]

    system_msg = f"""당신은 SNS 바이럴 카드뉴스 전문 에디터입니다.
콘텐츠 타입: {meta['label']} {meta['emoji']}
날짜: {kst_date} KST

{prompt}

수집 데이터:
{json.dumps(data, ensure_ascii=False, indent=2)}

반드시 아래 JSON 형식으로만 응답 (마크다운·설명 없이 JSON만):
{{
  "title": "카드 제목 (15자 이내, 임팩트 있게, {meta['emoji']} 포함)",
  "summary": "핵심 내용 3줄 (줄바꿈 \\n, 각 줄 30자 이내, 수치/구체성 포함)",
  "caption": "인스타그램 캡션 (이모지 포함, 250자 이내, 마지막 줄은 반드시 CTA)",
  "hashtags": "관련 해시태그 20개 (공백 구분, #AI #인공지능 포함)",
  "dalle_prompt": "배경 이미지 프롬프트 (영문, '{meta['bg_style']}' 스타일 참고, 100자 이내)"
}}"""

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": system_msg}],
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)
