import CardNews from './CardNews'

function getParam(key, fallback = '') {
  return new URLSearchParams(window.location.search).get(key) ?? fallback
}

// Playwright는 ?render=1 파라미터로 호출 → wrapper 없이 .card만 렌더
const isHeadless = new URLSearchParams(window.location.search).has('render')

function App() {
  const title   = getParam('title',   '오늘의 시장 흐름')
  const summary = getParam('summary', '비트코인 1.56%↑, 알트코인도 강세.\n코스피 2.45%↑, 강한 회복세.\n글로벌 증시 혼조, 투자 주의 필요.')
  const bgUrl   = getParam('bg_url',  '')
  const date    = getParam('date',    new Date().toISOString().slice(0, 10).replace(/-/g, '.'))

  const card = <CardNews title={title} summary={summary} bgUrl={bgUrl} date={date} />

  if (isHeadless) return card

  return <div className="card-preview-wrapper">{card}</div>
}

export default App
