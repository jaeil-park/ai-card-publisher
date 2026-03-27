import os
import json
import requests
from openai import OpenAI
from datetime import datetime

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))


def get_theme() -> tuple[str, list[str]]:
    """KST 기준 시간대별 테마 반환"""
    hour = (datetime.utcnow().hour + 9) % 24
    if 6 <= hour < 12:
        return "morning", ["AI 최신뉴스", "테크 트렌드"]
    elif 12 <= hour < 18:
        return "afternoon", ["코인 시황", "BTC ETH 가격"]
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


def generate_card_content(theme: str, news: list, crypto: list) -> dict:
    """GPT-4o로 카드뉴스 콘텐츠 생성"""
    prompt = f"""
당신은 SNS 카드뉴스 전문 에디터입니다.
아래 데이터를 기반으로 인스타그램/스레드용 카드뉴스 콘텐츠를 생성하세요.

테마: {theme}
AI 뉴스: {json.dumps(news, ensure_ascii=False)}
코인 시황: {json.dumps(crypto, ensure_ascii=False)}

반드시 아래 JSON 형식으로만 응답하세요 (마크다운, 설명 없이 JSON만):
{{
  "title": "카드 제목 (15자 이내, 임팩트 있게)",
  "summary": "핵심 내용 3줄 (줄바꿈은 \\n 사용, 각 줄 30자 이내)",
  "caption": "인스타그램 캡션 (이모지 포함, 300자 이내)",
  "hashtags": "#AI #인공지능 #코인 #비트코인 #트렌드",
  "dalle_prompt": "카드뉴스 배경 이미지 프롬프트 (영문, 추상적 미래적 디자인, 100자 이내)"
}}
"""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)
