export default function RainfallControl({ value, onChange, onForecast, note, loading, forecastBusy, error, onRetry }) {
  return (
    <div className="card rain">
      <div className="label">Rain scenario {loading && <span className="dots">· updating</span>}</div>
      <div className="rain-value">{value}<span> mm / 24h</span></div>
      <input aria-label="Rainfall scenario in millimetres over 24 hours" type="range" min="0" max="250" step="5" value={value} onChange={(e) => onChange(+e.target.value)} />
      <div className="scale"><span>0</span><span>125</span><span>250</span></div>
      <div className="row">
        {[50, 100, 150, 200].map((v) => <button key={v} className="chip" onClick={() => onChange(v)}>{v}</button>)}
        <button className="chip chip-accent" disabled={forecastBusy} onClick={onForecast}>{forecastBusy ? 'Fetching…' : '24-hour forecast'}</button>
      </div>
      {note && <div className="muted">{note}</div>}
      {error && <div role="alert" className="agent-error">{error} <button className="chip" onClick={onRetry}>Retry scenario</button></div>}
    </div>
  );
}
