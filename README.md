# 📱 ai-card-publisher

> AI 트렌드 & 코인 시황을 실시간 반영한 카드뉴스를 자동 생성하여
> Instagram / Threads에 하루 3회 자동 업로드하는 GitHub Actions 기반 자동화 시스템

## 🛠 Tech Stack
| 역할 | 기술 |
|------|------|
| 트렌드 수집 | Serper API, CoinGecko API |
| 콘텐츠 생성 | OpenAI GPT-4o |
| 이미지 생성 | OpenAI DALL-E 3 |
| 이미지 합성 | Pillow (한국어 텍스트 오버레이) |
| 이미지 호스팅 | imgbb API |
| SNS 게시 | Instagram Graph API v24.0, Threads Graph API v1.0 |
| 토큰 자동 갱신 | 매주 월요일 자동 실행 (30일 이하 시 갱신) |
| 자동화 | GitHub Actions |

## ⏰ 스케줄
| 시간 (KST) | 테마 |
|------|------|
| 오전 09:00 | AI 최신 뉴스 |
| 오후 13:00 | 코인 시황 |
| 저녁 20:00 | AI 투자 전략 |

## 🔐 GitHub Secrets 목록
| Secret | 설명 |
|--------|------|
| OPENAI_API_KEY | OpenAI API 키 |
| SERPER_API_KEY | Serper API 키 |
| IMGBB_API_KEY | imgbb 키 |
| INSTAGRAM_USER_ID | Instagram 계정 ID |
| INSTAGRAM_ACCESS_TOKEN | Instagram Long-lived Token |
| THREADS_USER_ID | Threads 계정 ID |
| THREADS_ACCESS_TOKEN | Threads Long-lived Token |
| DISCORD_WEBHOOK_URL | Discord 알림 Webhook |

## 🚀 로컬 테스트
```bash
cp .env.example .env
# .env에 실제 API 키 입력 후
pip install -r requirements.txt
python main.py
```
