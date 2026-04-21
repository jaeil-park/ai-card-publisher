import CardNews from './CardNews'

const params = new URLSearchParams(window.location.search)
const isHeadless = params.has('render')

const DEMO_POINTS = [
  { subtitle: 'GPT-5, 인간 전문가 수준 초월 예측', source: 'arXiv' },
  { subtitle: 'Claude 3.5, 환각 현상 구조적 제어', source: 'Anthropic' },
  { subtitle: '온체인 데이터 분석으로 상관관계 발견', source: 'CoinGecko' },
]

function App() {
  const title  = params.get('title')  ?? 'AI와 금융의 미래를 바꿀 3가지 팩트'
  const bgUrl  = params.get('bg_url') ?? ''
  const points = (() => {
    try { return JSON.parse(params.get('points') ?? 'null') || DEMO_POINTS }
    catch { return DEMO_POINTS }
  })()

  const card = <CardNews title={title} points={points} bgUrl={bgUrl} />

  if (isHeadless) return card
  return <div className="card-preview-wrapper">{card}</div>
}

export default App
