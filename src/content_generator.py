import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

def generate_facts(theme: str, news: list) -> dict:
    """
    GPT-4o를 이용해 최신 뉴스에서 3가지 핵심 팩트를 추출하고 JSON으로 반환합니다.
    """
    prompt = f"""
당신은 데이터 저널리스트입니다. 주어진 최신 뉴스 데이터에서 가장 중요한 핵심 팩트 3가지를 추출하여, Glassmorphism 카드뉴스 '이미지'에 삽입할 짧은 텍스트를 JSON 형식으로 요약하세요.

[요구사항]
1.  **제목 (title):** 전체 내용을 아우르는 간결하고 강력한 제목 (20자 이내).
2.  **핵심 팩트 (points):** 반드시 3개 항목으로 구성.
    - **subtitle:** 각 팩트의 소주제. **매우 짧고 강렬하게, 1~2줄 이내로 요약 (25자 이내).** 상세 설명은 캡션에 들어갈 것이므로, 여기서는 핵심만 언급.
    - **source:** 정보 출처 (10자 이내, 예: 'OpenAI', 'CoinGecko').
3.  **이미지 프롬프트 (dalle_prompt):** 주제와 직접 연관된 photorealistic 뉴스 사진 장면 묘사 (영문, 100자 이내).
4.  **엄격한 JSON 형식 준수:** 다른 설명 없이 JSON 객체만 반환해야 합니다.

[입력 데이터]
테마: {theme}
뉴스 기사: {json.dumps(news, ensure_ascii=False)}

[출력 JSON 형식]
{{
  "title": "AI와 금융의 미래를 바꿀 3가지 팩트",
  "dalle_prompt": "Bitcoin gold coin on dark financial chart, photorealistic, cinematic lighting",
  "points": [
    {{
      "subtitle": "GPT-5, 인간 전문가 수준 초월 예측",
      "source": "arXiv"
    }},
    {{
      "subtitle": "Claude 3.5, 환각 현상 구조적 제어",
      "source": "Anthropic"
    }}
  ]
}}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = json.loads(resp.choices[0].message.content)
        print("✅ GPT-4o 팩트 생성 완료")
        return content
    except Exception as e:
        print(f"⚠️ GPT-4o 팩트 생성 실패: {e}")
        return {
            "title": "AI-FinTech 핵심 동향 분석",
            "points": [
                {"subtitle": "차세대 언어 모델, 금융 분석 정확도 혁신", "source": "업계 보고서"},
                {"subtitle": "AI 기반 자동화, 투자 전략 재정의", "source": "자체 분석"},
                {"subtitle": "규제 환경 변화, 새로운 기회 창출", "source": "포럼 발표"}
            ]
        }

def generate_weekly_sections(data: dict) -> list[dict]:
    """주간 써머리 리포트용: AI/테크, 시장, GitHub 3섹션을 각각 facts로 반환"""
    sections = [
        {"theme": "이번 주 AI·테크 핵심",   "items": data.get("news", [])},
        {"theme": "이번 주 시장 동향",       "items": data.get("crypto", [])},
        {"theme": "이번 주 주목할 GitHub",   "items": data.get("github", [])},
    ]
    results = []
    for s in sections:
        if not s["items"]:
            continue
        facts = generate_facts(theme=s["theme"], news=s["items"])
        results.append(facts)
    # 최소 1개는 보장
    if not results:
        results.append(generate_facts(theme="주간 핵심 정리", news=[]))
    return results


def generate_caption(facts: dict, news: list) -> str:
    """
    추출된 팩트(facts)와 원본 뉴스(news)를 바탕으로 풍성한 SNS 캡션을 생성합니다.
    """
    prompt = f"""
당신은 SNS 콘텐츠 마케터입니다. 주어진 카드뉴스 팩트와 원본 기사를 바탕으로, 사용자의 참여를 유도하는 풍성한 Instagram/Threads 캡션(본문)을 작성하세요.

[요구사항]
1.  **첫 문단 (Hook):** 사용자의 시선을 사로잡는 흥미로운 질문이나 놀라운 사실로 시작하세요.
2.  **본문:** 카드뉴스 이미지에 담긴 3가지 핵심 팩트(`facts`)에 대해, `news` 데이터를 참고하여 각각 1~2문장의 상세한 설명을 덧붙이세요. 이모지를 적절히 사용하여 가독성을 높이세요.
3.  **마지막 문단 (CTA):** 사용자들이 댓글을 달고 싶게 만드는 개방형 질문을 던지세요.
4.  **해시태그:** 콘텐츠와 관련된 주요 키워드로 5~10개의 해시태그를 생성하세요.
5.  **전체 길이:** 300자 내외로 간결하게 작성하세요.

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
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        caption = resp.choices[0].message.content
        print("✅ GPT-4o 캡션 생성 완료")
        return caption
    except Exception as e:
        print(f"⚠️ GPT-4o 캡션 생성 실패: {e}")
        return f"{facts.get('title', '')}\n\n자세한 내용은 피드를 확인해주세요.\n\n#AI #FinTech #Gems"