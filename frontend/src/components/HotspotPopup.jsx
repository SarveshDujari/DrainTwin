import { useEffect, useRef, useState } from "react";
import { runIntervention } from "../services/api.js";
import { COLORS } from "./Map.jsx";
import AgentBrief from "./AgentBrief.jsx";

export default function HotspotPopup({ hotspot, rainfall, onClose }) {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(null);
  useEffect(() => {
    setResult(null); setError(''); setBusy(false);
    return () => pending.current?.abort();
  }, [hotspot.id, rainfall]);

  const run = async (type) => {
    setBusy(true); setError("");
    pending.current?.abort();
    const ctl = new AbortController(); pending.current = ctl;
    try { const value = await runIntervention(hotspot.id, type, rainfall, ctl.signal); if (!ctl.signal.aborted) setResult(value); }
    catch (e) { if (!ctl.signal.aborted) setError(`Scenario unavailable: ${e.message}`); }
    finally { if (!ctl.signal.aborted) setBusy(false); }
  };

  return (
    <div className="card popup">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      <div className="popup-head">
        <i style={{ background: COLORS[hotspot.severity] }} />
        <div>
          <div className="label">Susceptibility hotspot #{hotspot.id} · rank {hotspot.rank}</div>
          <div className="score">{hotspot.risk_score}<span> / 100 · {hotspot.severity}</span></div>
        </div>
      </div>
      <div className="confidence">
        Stable across tested parameter variations (DEM error excluded): <b>{hotspot.confidence}%</b> of variants · modelled score range {hotspot.score_range[0]}–{hotspot.score_range[1]}
      </div>

      <div className="label">What stands out here</div>
      <ul>{hotspot.reasons.map((r) => <li key={r}>{r}</li>)}</ul>

      <div className="label">Illustrative intervention scenarios</div>
      <div className="row wrap">
        {hotspot.recommendations.map((r) => (
          <button key={r.type} className="chip" disabled={busy} onClick={() => run(r.type)}>{r.label}</button>
        ))}
      </div>

      {error && <p className="agent-error" role="alert">{error}</p>}
      <AgentBrief hotspotId={hotspot.id} rainfall={rainfall} />

      {result && (
        <div className="result">
          <div className="label">{result.label} · ~{result.radius_m} m radius</div>
          <div className="score">{result.before} → {result.after}<span> risk · −{result.reduction_percent}%</span></div>
          <div className="muted">{result.note}</div>
        </div>
      )}
    </div>
  );
}
