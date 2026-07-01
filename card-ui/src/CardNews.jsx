import './CardNews.css'

const BADGES = ['①', '②', '③']

export default function CardNews({ title, points, bgUrl, slideIndex, totalSlides, dateLabel }) {
  const bgStyle = bgUrl ? { backgroundImage: `url(${bgUrl})` } : {}
  const isWeekly = slideIndex != null && totalSlides != null

  return (
    <div className="card">
      <div className="card__bg" style={bgStyle} />
      <div className="card__gradient" />

      <div className="card__inner">
        <div className="card__topbar">
          {isWeekly ? (
            <>
              <span className="card__weekly-badge">WEEKLY REPORT</span>
              <span className="card__slide-indicator">{slideIndex} / {totalSlides}</span>
            </>
          ) : (
            <>
              <span className="card__category-badge">AI TREND</span>
              <span className="card__date-badge">{dateLabel || ''}</span>
            </>
          )}
        </div>

        <h1 className="card__title">{title}</h1>

        <div className="card__points">
          {points.map((point, i) => (
            <div key={i} className="card__glass">
              <div className="card__glass-inner">
                <span className="card__badge-num">{BADGES[i] || '·'}</span>
                <div>
                  <h2 className="card__subtitle">{point.subtitle}</h2>
                  <p className="card__source">출처: {point.source}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <footer className="card__footer">
          @jaeil.park <span>|</span> AI·코인·증시
        </footer>
      </div>
    </div>
  )
}
