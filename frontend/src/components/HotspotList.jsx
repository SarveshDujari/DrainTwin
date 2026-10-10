export default function HotspotList({ hotspots = [], selectedId, onSelect }) {
  return <nav className="card hotspot-list" aria-label="Select susceptibility hotspots">
    <div className="label">Explore hotspots</div>
    <div className="hotspot-list-scroll">{hotspots.slice(0, 30).map(h =>
      <button key={h.id} type="button" aria-current={h.id === selectedId ? "true" : undefined}
        onClick={() => onSelect(h.id)}>
        <span>#{h.id} · {h.severity}</span><b>{h.risk_score}/100</b>
      </button>)}</div>
    {!hotspots.length && <p className="muted">No active sites for this scenario.</p>}
  </nav>;
}
