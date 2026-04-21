import './CardNews.css'

export default function CardNews({ title, points, bgUrl }) {
  const bgStyle = bgUrl ? { backgroundImage: `url(${bgUrl})` } : {}

  return (
    <div className="card">
      <div className="card__bg" style={bgStyle} />
      <div className="card__gradient" />

      <div className="card__inner">
        <h1 className="card__title">{title}</h1>

        <div className="card__points">
          {points.map((point, i) => (
            <div key={i} className="card__glass">
              <h2 className="card__subtitle">{point.subtitle}</h2>
              <p className="card__source">출처: {point.source}</p>
            </div>
          ))}
        </div>

        <footer className="card__footer">
          GEMS <span>|</span> @GEMS.OFFICIAL
        </footer>
      </div>
    </div>
  )
}
