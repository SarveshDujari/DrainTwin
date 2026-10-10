export default function HotspotCountControl({ total, value, onChange }) {
  const shown = Math.min(value, total);
  return (
    <div className="card count">
      <div className="label">Hotspots</div>
      <div className="count-num"><b>{shown}</b><span> of {total}</span></div>
      <input type="range" min="1" max={Math.max(total, 1)} value={Math.max(shown, 1)}
             disabled={total < 2} onChange={(e) => onChange(+e.target.value)} aria-label="Number of hotspots shown" />
      <div className="muted">Top by risk</div>
    </div>
  );
}
