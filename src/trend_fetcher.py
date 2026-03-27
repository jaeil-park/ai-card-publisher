import os
import json
import requests
from openai import OpenAI
from datetime import datetime, timedelta

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# 콘텐츠 포맷 풀 — 매 실행마다 GPT가 하나 선택
CONTENT_FORMATS = ["질문형", "통계/수치형", "팁/노하우형", "예측/전망형", "비교분석형"]


def get_theme() -> tuple[str, list[str]]:
    """KST 기준 시간대 + 요일별 특집 테마"""
    kst_now   = datetime.utcnow() + timedelta(hours=9)
    hour      = kst_now.hour
    weekday   = kst_now.weekday()  # 0=월 … 6=일

    if weekday == 0:
        return "weekly_ai_summary", ["주간 AI 요약", "이번 주 테크 뉴스"]
    if weekday == 4:
        return "weekly_crypto", ["주간 코인 총정리", "투자 전략"]

    if 6 <= hour < 12:
        return "morning", ["AI 최신뉴스", "테크 트렌드"]
    elif 12 <= hour < 18:
        return "afternoon", ["코인 시황", "글로벌 증시"]
    else:
        return "evening", ["AI 투자", "퀀트 전략"]


def fetch_ai_news() -> list[dict]:
    """Serper API로 AI 최신 뉴스 수집"""
    try:
        res = requests.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": os.environ["SERPER_API_KEY"]},
            json={"q": "AI 인공지능 최신 뉴스", "gl": "kr", "hl": "ko", "num": 5},
            timeout=10
        )
        res.raise_for_status()
        items = res.json().get("news", [])
        return [{"title": i["title"], "snippet": i.get("snippet", "")} for i in items]
    except Exception as e:
        print(f"⚠️ AI 뉴스 수집 실패: {e}")
        return [{"title": "AI 트렌드", "snippet": "최신 AI 동향을 확인하세요"}]


def fetch_crypto() -> list[dict]:
    """CoinGecko 무료 API로 코인 시황"""
    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "krw",
                "ids": "bitcoin,ethereum,solana",
                "order": "market_cap_desc"
            },
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
        return [{"name": "Bitcoin", "price_krw": "N/A", "change_24h": "N/A"}]


def fetch_stock_market() -> list[dict]:
    """Yahoo Finance 무료 API로 글로벌 증시 수집"""
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
            data  = res.json()["chart"]["result"][0]
            close = data["indicators"]["quote"][0]["close"]
            prev, curr = close[-2], close[-1]
            change = ((curr - prev) / prev) * 100
            results.append({
                "name": name,
                "value": f"{curr:,.2f}",
                "change_1d": f"{change:+.2f}%"
            })
        except Exception as e:
            print(f"⚠️ {name} 수집 실패: {e}")
    return results


def generate_card_content(theme: str, news: list, crypto: list) -> dict:
    """GPT-4o로 카드뉴스 콘텐츠 생성 (다양한 포맷 + 유입 최적화 + AI 명시)"""
    stock = fetch_stock_market()
    kst_date = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y.%m.%d")

    prompt = f"""
당신은 SNS 바이럴 카드뉴스 전문 에디터입니다.
아래 데이터를 기반으로 팔로우·저장·댓글을 유도하는 카드뉴스 콘텐츠를 생성하세요.

날짜: {kst_date} KST
테마: {theme}
콘텐츠 포맷: {CONTENT_FORMATS} 중 테마에 가장 어울리는 1개 선택
AI 뉴스: {json.dumps(news, ensure_ascii=False)}
코인 시황: {json.dumps(crypto, ensure_ascii=False)}
글로벌 증시: {json.dumps(stock, ensure_ascii=False)}

반드시 아래 JSON 형식으로만 응답하세요 (마크다운·설명 없이 JSON만):
{{
  "title": "카드 제목 (15자 이내, 임팩트 있게)",
  "summary": "핵심 내용 3줄 (줄바꿈은 \\n, 각 줄 30자 이내, 수치 포함)",
  "caption": "인스타그램 캡션 (이모지 포함, 250자 이내)\\n\\n마지막 줄은 반드시 질문이나 CTA: 예) '여러분은 어떻게 생각하세요? 💬 댓글로 알려주세요!' 또는 '📌 저장해두고 나중에 확인하세요!'",
  "hashtags": "관련 해시태그 20개 (공백 구분, #AI #인공지능 등 포함)",
  "dalle_prompt": "카드뉴스 배경 이미지 프롬프트 (영문, 추상적 미래적 디자인, 100자 이내)"
}}
"""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)
