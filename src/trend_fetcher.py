import os
import json
import requests
import time
from google import genai
from google.genai import types
from datetime import datetime, timedelta, date


CONTENT_META = {
    "morning_briefing": {"emoji": "☀️", "label": "아침 AI 브리핑",  "bg_style": "bright sunrise digital newsroom, blue gold gradient"},
    "tech_trend":       {"emoji": "💻", "label": "개발 트렌드",     "bg_style": "dark coding terminal, green matrix neon, github vibes"},
    "market_update":    {"emoji": "📊", "label": "시장 시황",       "bg_style": "financial trading floor, dark blue red candlestick chart"},
    "ai_tools":         {"emoji": "🛠️", "label": "AI 개발툴",      "bg_style": "futuristic IDE interface, purple cyan glow, tool icons"},
    "product_hunt":     {"emoji": "🚀", "label": "AI 신제품",       "bg_style": "product launch stage, orange white spotlight, startup energy"},
    "ai_tips":          {"emoji": "🧠", "label": "AI 비서 팁",      "bg_style": "mind map neural network, teal purple gradient, productivity"},
    "weekly_picks":     {"emoji": "🛍️", "label": "주간 추천템",     "bg_style": "cozy home shopping flatlay, warm pastel gradient, product photography"},
}


# ── 콘텐츠 타입 자동 결정 ──────────────────────────────────

# 2026-07 개편: 크론이 3회/일 → 1회/일로 축소되면서 시간대 기반 분기를
# 요일 기반 로테이션으로 전환. 매일 같은 시각에 게시되므로 콘텐츠 타입까지
# 고정되면 "반복적 콘텐츠" 스팸 신호가 재발하기 때문
# (Threads 계정정지 사고 원인 중 하나 — rate_limiter.py 주석 참조).
_WEEKDAY_ROTATION = [
    "morning_briefing",  # 월 (0) ☀️ 아침 AI 브리핑
    "tech_trend",        # 화 (1) 💻 개발 트렌드
    "market_update",     # 수 (2) 📊 시장 시황
    "ai_tools",          # 목 (3) 🛠️ AI 개발툴
    "product_hunt",      # 금 (4) 🚀 AI 신제품
    "ai_tips",           # 토 (5) 🧠 AI 비서 팁
    "weekly_picks",      # 일 (6) 🛍️ 주간 추천템 (데이터랩 급상승 카테고리 + 쿠팡 실제 상품)
]


def get_content_type() -> str:
    """현재 요일 기준으로 콘텐츠 타입 자동 결정 (1일 1회 게시 체제)."""
    weekday = (datetime.utcnow() + timedelta(hours=9)).weekday()  # 0=월 … 6=일
    return _WEEKDAY_ROTATION[weekday]


# ── 데이터 수집 함수들 ─────────────────────────────────────

def fetch_ai_news() -> list[dict]:
    """Naver Search API: AI 최신 뉴스 (무료: 일 25,000회)"""
    try:
        client_id = os.environ.get("NAVER_CLIENT_ID", "")
        client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
        res = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret
            },
            params={"query": "AI 인공지능", "display": 5, "sort": "sim"},
            timeout=10
        )
        res.raise_for_status()
        return [{"title": i["title"].replace("<b>", "").replace("</b>", ""), "snippet": i.get("description", "").replace("<b>", "").replace("</b>", "")}
                for i in res.json().get("items", [])]
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
    """Naver Search API: AI 개발툴 최신 동향 (무료)"""
    try:
        client_id = os.environ.get("NAVER_CLIENT_ID", "")
        client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
        res = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret
            },
            params={"query": "AI 개발툴 코딩", "display": 5, "sort": "sim"},
            timeout=10
        )
        res.raise_for_status()
        return [{"title": i["title"].replace("<b>", "").replace("</b>", ""), "snippet": i.get("description", "").replace("<b>", "").replace("</b>", "")}
                for i in res.json().get("items", [])]
    except Exception as e:
        print(f"⚠️ AI 개발툴 뉴스 수집 실패: {e}")
        return []


def fetch_product_hunt() -> list[dict]:
    """Naver Search API: AI 신제품/서비스 동향 (무료)"""
    try:
        client_id = os.environ.get("NAVER_CLIENT_ID", "")
        client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
        res = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret
            },
            params={"query": "AI 신제품 출시", "display": 5, "sort": "sim"},
            timeout=10
        )
        res.raise_for_status()
        return [{"title": i["title"].replace("<b>", "").replace("</b>", ""), "snippet": i.get("description", "").replace("<b>", "").replace("</b>", "")}
                for i in res.json().get("items", [])]
    except Exception as e:
        print(f"⚠️ Product Hunt 수집 실패: {e}")
        return []


# ── 주간 추천템 (네이버 데이터랩 쇼핑인사이트 + 쿠팡 파트너스) ──
#
# 데이터랩 쇼핑인사이트 공식 API(client_id/secret)는 "순위 발견" API가 아니라
# 미리 지정한 카테고리들의 상대적 검색 추이 비교만 제공한다. 따라서:
#   1) 데이터랩으로 지난주 대비 이번 주 검색 비율이 가장 많이 오른 카테고리를 탐지
#   2) 그 카테고리명을 키워드로 쿠팡 파트너스 공식 검색 API를 호출해 실제 판매 중인
#      상품(로켓배송 우선)을 후보로 선정
# 이렇게 "어떤 카테고리가 뜨는지"는 데이터랩이, "그 안의 구체적 상품"은 쿠팡 실제
# 검색 결과가 담당하도록 역할을 분리한다.
_SHOPPING_CATEGORIES = [
    ("패션의류", "50000000"),
    ("화장품/미용", "50000002"),
    ("디지털/가전", "50000003"),
    ("가구/인테리어", "50000004"),
    ("식품", "50000006"),
    ("스포츠/레저", "50000007"),
    ("생활/건강", "50000008"),
    ("여가/생활편의", "50000009"),
]


def fetch_trending_shopping_category() -> dict | None:
    """데이터랩 쇼핑인사이트: 최근 7일 평균 검색비율이 이전 7일 대비 가장 많이 오른 카테고리.

    API 제약: category 배열은 요청당 최대 3개까지만 허용되므로(초과 시 400
    TypeError) 3개씩 나눠 여러 번 호출한 뒤 결과를 합산한다.
    """
    client_id = os.environ.get("NAVER_CLIENT_ID", "")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        print("⚠️ NAVER_CLIENT_ID/SECRET 미설정 — 쇼핑 트렌드 탐지 스킵")
        return None

    today = date.today()
    start = today - timedelta(days=14)
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    all_results = []
    for i in range(0, len(_SHOPPING_CATEGORIES), 3):
        chunk = _SHOPPING_CATEGORIES[i:i + 3]
        try:
            res = requests.post(
                "https://openapi.naver.com/v1/datalab/shopping/categories",
                headers=headers,
                json={
                    "startDate": start.isoformat(),
                    "endDate": today.isoformat(),
                    "timeUnit": "date",
                    "category": [{"name": name, "param": [code]} for name, code in chunk],
                },
                timeout=10,
            )
            res.raise_for_status()
            all_results.extend(res.json().get("results", []))
        except Exception as e:
            print(f"⚠️ 데이터랩 쇼핑인사이트 수집 실패({[n for n, _ in chunk]}): {e}")

    best = None
    for r in all_results:
        data_points = r.get("data", [])
        if len(data_points) < 8:
            continue
        recent = [d["ratio"] for d in data_points[-7:]]
        prior = [d["ratio"] for d in data_points[-14:-7]]
        if not prior or sum(prior) == 0:
            continue
        growth = (sum(recent) / len(recent)) / (sum(prior) / len(prior)) - 1
        if best is None or growth > best["growth"]:
            best = {"name": r.get("title", ""), "growth": growth}

    if best:
        print(f"📈 급상승 카테고리: {best['name']} ({best['growth']*100:+.1f}%)")
    return best


def fetch_weekly_shopping_picks() -> list[dict]:
    """급상승 카테고리 탐지 → 쿠팡 공식 검색 API로 실제 상품 후보 선정."""
    from src.coupang_client import search_products

    category = fetch_trending_shopping_category()
    category_name = category["name"] if category else _SHOPPING_CATEGORIES[0][0]
    growth_note = f"전주 대비 검색량 {category['growth']*100:+.0f}%" if category else "이번 주 관심 카테고리"

    products = search_products(category_name, limit=6)
    rocket_first = sorted(products, key=lambda p: not p.get("is_rocket", False))[:5]

    if not rocket_first:
        return [{"title": f"{category_name} 카테고리 인기 급상승", "snippet": growth_note}]

    return [
        {
            "title": p["name"][:40],
            "snippet": f"{p['price']:,}원 · {'로켓배송' if p['is_rocket'] else '일반배송'} · {category_name} {growth_note}",
        }
        for p in rocket_first
    ]


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

    elif content_type == "weekly_picks":
        return {"news": fetch_weekly_shopping_picks()}

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
          "dalle_prompt": "Unsplash 배경 검색용 영문 키워드 (예: technology, office, neon, ai)"
}}"""

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=system_msg,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(resp.text)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Gemini API 요청 지연 (재시도 중... {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)  # 1초, 2초 점진적으로 대기 시간 증가
            else:
                raise e
