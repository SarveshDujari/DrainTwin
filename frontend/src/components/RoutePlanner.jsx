import { useEffect, useMemo, useState } from 'react';
import { fetchRiskAwareRoutes, rankRoutes, exposureReduction } from '../services/routing.js';
import { LANDMARKS } from '../services/landmarks.js';

export default function RoutePlanner({ start, end, picking, onPick, onReset, onSwap, onPreset, onFit, message, data, onRoutes, selected, onSelect }) {
  const [raw, setRaw] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [partial, setPartial] = useState(false);
  const [retry, setRetry] = useState(0);
  const [preference, setPreference] = useState('balanced');
  const [maxExtraMinutes, setMaxExtraMinutes] = useState(5);
  const endpointKey = JSON.stringify([start, end]);
  const [rawKey, setRawKey] = useState('');
  useEffect(() => {
    setError(''); setBusy(false); setPartial(false);
    if (!start || !end || !data) return;
    const ctl = new AbortController();
    let cancelled = false;
    setBusy(true);
    fetchRiskAwareRoutes(start, end, data, ctl.signal, base => {
      if (!cancelled) { setRaw(old => rawKey === endpointKey ? old : base); setRawKey(endpointKey); }
    }).then(result => {
      if (!cancelled) { setRaw(result.routes); setRawKey(endpointKey); setPartial(result.partial); }
    }).catch(e => {
      if (!cancelled) setError(e.name === 'AbortError' ? 'Routing timed out. Please retry.' : e.message);
    }).finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; ctl.abort(); };
  }, [start, end, data, retry]);
  const routes = useMemo(() => data && rawKey === endpointKey ? rankRoutes(raw, data, { preference, maxExtraMinutes }) : [], [raw, rawKey, endpointKey, data, preference, maxExtraMinutes]);
  const best = routes.find(r => r.recommended);
  const fastest = routes.find(r => r.fastest);
  const savedExposure = exposureReduction(best, fastest);
  useEffect(() => { onRoutes(routes); }, [routes, onRoutes]);
  return <section className="card route-planner">
    <b>Plan a route</b>
    <p className="muted">Choose two points on the map inside the study area.</p>
    <details className="route-details"><summary>Choose landmark presets</summary><div className="route-settings">{['start', 'end'].map(which => <label key={which}>{which === 'start' ? 'Start preset' : 'Destination preset'}<select aria-label={`${which} landmark preset`} value="" onChange={e => { const p = LANDMARKS[Number(e.target.value)]; if (p) onPreset(which, {lat:p.lat,lng:p.lng}); }}><option value="" disabled>Choose landmark</option>{LANDMARKS.map((p, i) => <option key={p.name} value={i}>{p.name}</option>)}</select></label>)}</div>
    <p className="muted">Landmark centres snap to nearby roads; entrances may differ.</p></details>
    <div className="row">
      <button className={`chip ${picking === 'start' ? 'chip-accent' : ''}`} onClick={() => onPick('start')}>Start {start ? '✓' : ''}</button>
      <button className={`chip ${picking === 'end' ? 'chip-accent' : ''}`} onClick={() => onPick('end')}>Destination {end ? '✓' : ''}</button>
      <button className="chip" onClick={onReset}>Reset</button>
      <button className="chip" disabled={!start || !end} onClick={onSwap}>Swap</button>
      <button className="chip" disabled={!routes.length} onClick={onFit}>Show selected route</button>
    </div>
    <p className="muted">Start: {start ? `${start.lat.toFixed(4)}, ${start.lng.toFixed(4)}` : 'not selected'}<br/>Destination: {end ? `${end.lat.toFixed(4)}, ${end.lng.toFixed(4)}` : 'not selected'}</p>
    {message && <p role="alert" className="agent-error">{message}</p>}
    <details className="route-details"><summary>{preference === 'balanced' ? 'Balance time & risk' : preference === 'fastest' ? 'Fastest' : 'Lower risk'} · up to {maxExtraMinutes} extra min</summary><div className="route-settings">
      <label>Route preference<select value={preference} onChange={e => setPreference(e.target.value)}>
        <option value="balanced">Balance time & risk</option><option value="fastest">Fastest</option><option value="lower-risk">Lower risk</option>
      </select></label>
      <label>Maximum extra time<select value={maxExtraMinutes} onChange={e => setMaxExtraMinutes(Number(e.target.value))}>
        {[0, 5, 10, 15].map(m => <option value={m} key={m}>{m} minutes</option>)}
      </select></label>
    </div></details>
    <p className="muted" aria-live="polite">{picking ? `Click the map to set your ${picking === 'start' ? 'starting point' : 'destination'}.` : 'Change rainfall to compare hotspot exposure.'}</p>
    {busy && <p role="status">{routes.length ? 'Available routes shown; checking additional detours…' : 'Finding road routes…'}</p>}
    {error && <div><p role="alert" className="agent-error">{error}</p><button className="chip" onClick={() => setRetry(v => v + 1)}>Retry routes</button></div>}
    {!data && <p className="muted">Waiting for drainage risk data…</p>}
    {best && <div className="route-summary" role="status">{savedExposure > 0 ? `${savedExposure}% less modelled risk exposure than the fastest route, for ${Math.ceil(best.extraMinutes)} extra min.` : best.fastest ? 'The fastest route also fits your selected preference.' : 'Recommended for your selected preference and detour limit.'}
      {best.hotspots > 0 && <div>Still passes near {best.hotspots} modelled hotspot{best.hotspots === 1 ? '' : 's'}.</div>}
    </div>}
    {fastest?.outside && <p className="muted">The fastest route leaves the assessed area; its exposure cannot be compared as a percentage.</p>}
    {[...routes].sort((a,b) => Number(b.recommended)-Number(a.recommended)).map(r => <button key={r.id} aria-pressed={selected === r.id} className={`route-option ${selected === r.id ? 'active' : ''}`} onClick={() => onSelect(r.id)}>
      <strong>{r.recommended ? 'Recommended' : `Route ${r.id + 1}`} · {Math.round(r.duration / 60)} min</strong>
      <span>{(r.distance / 1000).toFixed(1)} km · {r.hotspots} nearby hotspot{r.hotspots === 1 ? '' : 's'}{r.fastest ? ' · fastest' : ` · +${Math.ceil(r.extraMinutes)} min`}</span>
      <span>{(r.highRiskMetres / 1000).toFixed(1)} km through modelled high-risk areas</span>
      {r.outside && <span>Leaves study area — risk partly unknown</span>}
    </button>)}
    {!busy && routes.length === 1 && <p className="muted">One useful route remains after removing duplicate or worse alternatives.</p>}
    {!busy && best?.fastest && best.hotspots > 0 && <p className="muted">No better detour found for your preference within the extra-time limit.</p>}
    {partial && <p className="muted">Some detours could not be checked. Comparing available routes.</p>}
    {routes.length > 0 && <p className="muted">Uses your preference with up to {maxExtraMinutes} extra minutes, inside the study area. Hotspots counted within 300 m. {routes.every(r => !r.recommended) ? 'No route meets these conditions.' : 'The same route may still be best when rainfall changes.'}</p>}
    <p className="muted">Demo · estimated driving time, without live traffic. Modelled hotspots, not confirmed road closures. Internet required.</p>
    <details className="muted"><summary>How routes are compared</summary>Balanced mode adds a preference penalty for distance-weighted grid risk and nearby hotspots. These are assumed preferences, not predicted flood delays. Driving times exclude these penalties. Lower-risk mode prioritizes modelled exposure within your detour limit.</details>
  </section>;
}
