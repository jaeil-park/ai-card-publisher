import os
import json
import time
from google import genai
from google.genai import types

def _client():
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

def _generate_json(prompt: str, retries: int = 3) -> dict:
    client = _client()
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return json.loads(resp.text)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise e


def generate_facts(theme: str, news: list) -> dict:
    prompt = f"""
당신은 데이터 저널리스트입니다. 주어진 최신 뉴스 데이터에서 가장 중요한 핵심 팩트 3가지를 추출하여, Glassmorphism 카드뉴스 '이미지'에 삽입할 짧은 텍스트를 JSON 형식으로 요약하세요.

[요구사항]
1. title: 전체 내용을 아우르는 간결하고 강력한 제목 (20자 이내).
2. points: 반드시 3개 항목.
   - subtitle: 각 팩트의 소주제. 매우 짧고 강렬하게, 1~2줄 이내 (25자 이내).
   - source: 정보 출처 (10자 이내, 예: 'OpenAI', 'CoinGecko').
3. dalle_prompt: 주제와 직접 연관된 photorealistic 뉴스 사진 장면 묘사 (영문, 100자 이내).
4. 엄격한 JSON 형식만 반환 (설명 없이).

[입력 데이터]
테마: {theme}
뉴스 기사: {json.dumps(news, ensure_ascii=False)}

[출력 JSON 형식]
{{
  "title": "AI와 금융의 미래를 바꿀 3가지 팩트",
  "dalle_prompt": "Bitcoin gold coin on dark financial chart, photorealistic, cinematic lighting",
  "points": [
    {{"subtitle": "GPT-5, 인간 전문가 수준 초월 예측", "source": "arXiv"}},
    {{"subtitle": "Claude 3.5, 환각 현상 구조적 제어", "source": "Anthropic"}},
    {{"subtitle": "온체인 데이터 분석으로 상관관계 발견", "source": "CoinGecko"}}
  ]
}}
"""
    try:
        content = _generate_json(prompt)
        print("✅ Gemini 팩트 생성 완료")
        return content
    except Exception as e:
        print(f"⚠️ Gemini 팩트 생성 실패: {e}")
        return {
            "title": "AI-FinTech 핵심 동향 분석",
            "dalle_prompt": "technology abstract dark background",
            "points": [
                {"subtitle": "차세대 언어 모델, 금융 분석 정확도 혁신", "source": "업계 보고서"},
                {"subtitle": "AI 기반 자동화, 투자 전략 재정의", "source": "자체 분석"},
                {"subtitle": "규제 환경 변화, 새로운 기회 창출", "source": "포럼 발표"},
            ],
        }


def generate_weekly_sections(data: dict) -> list[dict]:
    sections = [
        {"theme": "이번 주 AI·테크 핵심",  "items": data.get("news", [])},
        {"theme": "이번 주 시장 동향",      "items": data.get("crypto", [])},
        {"theme": "이번 주 주목할 GitHub",  "items": data.get("github", [])},
    ]
    results = []
    for s in sections:
        if not s["items"]:
            continue
        facts = generate_facts(theme=s["theme"], news=s["items"])
        results.append(facts)
    if not results:
        results.append(generate_facts(theme="주간 핵심 정리", news=[]))
    return results


def generate_caption(facts: dict, news: list) -> str:
    prompt = f"""
당신은 SNS 콘텐츠 마케터입니다. 주어진 카드뉴스 팩트와 원본 기사를 바탕으로, 사용자의 참여를 유도하는 풍성한 Instagram/Threads 캡션(본문)을 작성하세요.

[요구사항]
1. 첫 문단 (Hook): 사용자의 시선을 사로잡는 흥미로운 질문이나 놀라운 사실로 시작.
2. 본문: 카드뉴스 이미지에 담긴 3가지 핵심 팩트에 대해 각각 1~2문장 상세 설명. 이모지로 가독성 강화.
3. 마지막 문단 (CTA): 댓글을 유도하는 개방형 질문.
4. 해시태그: 콘텐츠 관련 주요 키워드 5~10개.
5. 전체 길이: 300자 내외.

[입력 데이터]
카드뉴스 팩트: {json.dumps(facts, ensure_ascii=False)}
참고 뉴스: {json.dumps(news, ensure_ascii=False)}

[출력 형식]
첫 문단 (Hook)

- [팩트1 부제]: 상세 설명...
- [팩트2 부제]: 상세 설명...
- [팩트3 부제]: 상세 설명...

마지막 문단 (CTA)

#해시태그1 #해시태그2 #해시태그3
"""
    client = _client()
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            caption = resp.text
            print("✅ Gemini 캡션 생성 완료")
            return caption
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                print(f"⚠️ Gemini 캡션 생성 실패: {e}")
                return f"{facts.get('title', '')}\n\n자세한 내용은 피드를 확인해주세요.\n\n#AI #FinTech #Gems"
