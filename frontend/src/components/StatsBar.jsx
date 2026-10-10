export default function StatsBar({ data, shown }) {
  const stats = data ? [
    [`${shown}/${data.total_hotspots}`, "Hotspots shown"],
    [data.risk_level, "Area coverage category"],
    [`${data.stats.runoff_percent}%`, "Rain becoming runoff"],
    [`${data.stats.area_at_risk_percent}%`, "Area with index ≥45"],
  ] : [];
  return (
    <div className="stats">
      {stats.map(([v, l]) => <div key={l} className="card stat"><b>{v}</b><span>{l}</span></div>)}
    </div>
  );
}
