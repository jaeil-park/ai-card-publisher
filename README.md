# 📱 ai-card-publisher

> AI 트렌드 · 코인 시황 · 개발 뉴스를 실시간 수집해 카드뉴스로 자동 생성,
> Instagram / Threads에 하루 7회 자동 업로드하는 GitHub Actions 기반 자동화 시스템

---

## 🛠 Tech Stack

| 역할 | 기술 |
|------|------|
| 트렌드 수집 | Naver Search API, GitHub API, CoinGecko API, Product Hunt RSS |
| 콘텐츠 생성 | Google Gemini (`google-genai`) + OpenAI GPT-4o |
| 배경 이미지 | OpenAI DALL-E 3 + Unsplash API |
| 카드 렌더링 | **React + Vite** (card-ui/) → Playwright headless 스크린샷 |
| 이미지 호스팅 | Cloudinary |
| SNS 게시 | Instagram Graph API v24.0, Threads Graph API |
| 분석 리포트 | Discord Webhook (일간 · 주간 ROI) |
| 토큰 자동 갱신 | 매주 월요일 09:00 KST |
| 자동화 | GitHub Actions |

---

## ⏰ 자동 게시 스케줄 (KST)

| 시간 | 콘텐츠 타입 |
|------|------------|
| 06:00 ☀️ | 아침 AI 브리핑 |
| 09:00 💻 | 개발 트렌드 (GitHub + HN) |
| 12:00 📊 | 시장 시황 (코인 + 증시 + 환율) |
| 15:00 🛠️ | AI 개발툴 뉴스 |
| 18:00 🚀 | AI 신제품 (Product Hunt) |
| 21:00 🧠 | AI 비서 팁 |
| 일요일 20:00 📅 | 한 주 핵심 정리 |

---

## 🗂 프로젝트 구조

```
ai-card-publisher/
├── card-ui/                  # React + Vite 카드 UI (디자인 수정 여기서)
│   ├── src/
│   │   ├── CardNews.jsx      # 카드 컴포넌트
│   │   └── CardNews.css      # 스타일 (1080×1350 Instagram 세로)
│   └── vite.config.js
├── src/
│   ├── trend_fetcher.py      # 데이터 수집 + Gemini 콘텐츠 생성
│   ├── content_generator.py  # GPT-4o 팩트 추출 + 캡션 생성
│   ├── background_maker.py   # DALL-E 3 배경 이미지 생성
│   ├── card_generator.py     # React 카드 → Playwright PNG 렌더링
│   ├── html_renderer.py      # Jinja2 + Playwright 렌더러
│   ├── image_compositor.py   # Cloudinary 업로드
│   ├── highlight_manager.py  # Instagram Story 커버 생성
│   ├── poster.py             # Instagram / Threads 게시
│   ├── analytics.py          # Discord 리포트
│   └── token_manager.py      # 토큰 자동 갱신
├── .github/workflows/
│   ├── card_news.yml         # 메인 파이프라인 (하루 7회)
│   ├── analytics.yml         # 일간·주간 리포트
│   └── token_refresh.yml     # 토큰 갱신
├── main.py
└── requirements.txt
```

---

## 🔐 GitHub Secrets (ENV_FILE)

`.env` 전체 내용을 `ENV_FILE` 시크릿 하나에 저장합니다.

```env
# AI APIs
OPENAI_API_KEY=
GOOGLE_API_KEY=

# 데이터 수집
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
UNSPLASH_ACCESS_KEY=

# 이미지 호스팅
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# SNS
INSTAGRAM_USER_ID=
INSTAGRAM_ACCESS_TOKEN=
THREADS_USER_ID=
THREADS_ACCESS_TOKEN=

# 알림
DISCORD_WEBHOOK_URL=

# GitHub (토큰 갱신용)
PAT_TOKEN=
```

---

## 🚀 로컬 테스트

```bash
# 1. 환경 설정
cp .env.example .env
# .env에 실제 API 키 입력

# 2. Python 의존성 설치
pip install -r requirements.txt
playwright install chromium

# 3. React 카드 UI 빌드
cd card-ui && npm install && npm run build && cd ..

# 4. 전체 파이프라인 실행
python main.py
```

### 카드 디자인 미리보기

```bash
cd card-ui
npm run dev
# → http://localhost:5173 에서 실시간 확인
```

---

## 🎨 카드 디자인 수정

[card-ui/src/CardNews.jsx](card-ui/src/CardNews.jsx) · [card-ui/src/CardNews.css](card-ui/src/CardNews.css) 수정 후:

```bash
npm run build --prefix card-ui
```

빌드 없이 미리보기만 할 때는 `npm run dev`로 브라우저에서 즉시 확인 가능합니다.
