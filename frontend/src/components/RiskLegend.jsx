import { COLORS } from "./Map.jsx";

const ROWS = [["low", "Low (not shaded)", "< 25"], ["moderate", "Moderate", "25–45"], ["high", "High", "45–65"], ["critical", "Critical", "65+"]];

export default function RiskLegend() {
  return (
    <div className="card legend">
      <div className="label">Relative susceptibility index</div>
      {ROWS.map(([k, t, r]) => (
        <div key={k} className="legend-row">
          <i style={k === "low" ? { border: `2px solid ${COLORS.low}` } : { background: COLORS[k] }} />{t}<span>{r}</span>
        </div>
      ))}
    </div>
  );
}
