import './CardNews.css'

export default function CardNews({ title, summary, bgUrl, date }) {
  const lines = summary ? summary.split('\n').slice(0, 3) : []

  const bgStyle = bgUrl
    ? { backgroundImage: `url(${bgUrl})` }
    : { background: '#14141e' }

  return (
    <div className="card">
      <div className="card__bg" style={bgStyle} />
      <div className="card__panel" />

      <header className="card__topbar">
        <span className="card__badge">🤖 AI DAILY</span>
        <span className="card__date">{date}</span>
      </header>

      <main className="card__content">
        <h1 className="card__title">{title}</h1>
        <div className="card__summary">
          {lines.map((line, i) => (
            <p key={i} className="card__summary-line">{line}</p>
          ))}
        </div>
      </main>

      <footer className="card__watermark">✨ AI Generated Content</footer>
    </div>
  )
}
