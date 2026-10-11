export default function StatsBar({ data, shown }) {
  const stats = data ? [
    [`${data.stats.area_at_risk_percent}%`, "Area with index ≥45"],
    [`${data.total_hotspots}/${data.candidate_sites ?? data.total_hotspots}`, "Active fixed sites"],
    [data.risk_level, "Area coverage category"],
    [`${data.stats.runoff_percent}%`, "Rain becoming runoff"],
  ] : [];
  return (
    <div className="stats">
      {stats.map(([v, l]) => <div key={l} className="card stat"><b>{v}</b><span>{l}</span></div>)}
    </div>
  );
}
