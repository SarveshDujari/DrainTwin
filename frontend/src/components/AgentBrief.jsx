import { useEffect, useRef, useState } from 'react';
import { getAgentStatus, getAgentBrief } from '../services/api.js';

export default function AgentBrief({hotspotId, rainfall}) {
  const [status,setStatus] = useState(null);
  const [brief,setBrief] = useState(null);
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  const pending = useRef(null);
  useEffect(() => {
    let active=true;
    getAgentStatus().then(s=>{if(active)setStatus(s);}).catch(()=>{if(active)setStatus({strands_enabled:false});});
    return ()=>{active=false;};
  }, []);
  useEffect(()=>{setBrief(null);setError('');setBusy(false);return ()=>pending.current?.abort();},[hotspotId,rainfall]);
  async function generate(useAgent) {
    setBusy(true);setError('');setBrief(null);
    pending.current?.abort();
    const ctl = new AbortController(); pending.current = ctl;
    try {
      const result=await getAgentBrief(hotspotId,rainfall,useAgent,ctl.signal);
      if (ctl.signal.aborted) return;
      setBrief(result);
      if(useAgent && result.mode==='deterministic_fallback') setError('AI unavailable; showing the model-based offline summary.');
    } catch(e) {if (!ctl.signal.aborted) setError(`Unable to generate briefing: ${e.message}`);}
    finally {if (!ctl.signal.aborted) setBusy(false);}
  }
  return <section className="agent-section" aria-label="Flood advisory">
    <div className="label">Evidence-grounded advisory</div>
    <p className="agent-hint">Numerical values below come from the deterministic model, not the LLM.</p>
    <div className="row">
      <button className="chip chip-accent" disabled={busy} onClick={()=>generate(false)}>Offline briefing</button>
      <button className="chip" disabled={busy || !status?.strands_enabled} onClick={()=>generate(true)}>Optional AI explanation</button>
    </div>
    {!status?.strands_enabled && <p className="muted">Enable Strands to use Gemini or Ollama; offline works without either.</p>}
    {busy && <p role="status" className="muted">Generating advisory… cloud or local AI may take a while.</p>}
    {error && <p role="alert" className="agent-error">{error}</p>}
    {brief && <div className="agent-output" aria-live="polite">
      <div className="label">{brief.provider ? `Optional AI prose · ${brief.provider==='gemini'?'Gemini':'Ollama'}` : 'Model-based summary · offline'}</div>
      <p>{brief.summary}</p>
      {brief.explanation && <p>{brief.explanation}</p>}
      <div className="label">Model inputs and illustrative scenarios</div>
      <p>Rainfall: {brief.evidence.rainfall_mm} mm · Susceptibility index: {brief.evidence.current_score}/100</p>
      <ul>{brief.evidence.options.map(o=><li key={o.type}>{o.label}: {o.before} → {o.after} (modelled {o.reduction_percent}% change)</li>)}</ul>
      <p className="muted">{brief.disclaimer}</p>
    </div>}
  </section>;
}
