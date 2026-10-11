const inArea = ([lng, lat], [s, w, n, e]) => lat >= s && lat <= n && lng >= w && lng <= e;
const routeCache = new Map();
const CACHE_TTL = 10 * 60 * 1000;
export const clearRouteCache = () => routeCache.clear();
export function exposureReduction(best, fastest) {
  if (!best || !fastest || best.outside || fastest.outside || fastest.riskMetres <= 0) return null;
  return Math.round((1 - best.riskMetres / fastest.riskMetres) * 100);
}
const routeKey = r => JSON.stringify(r.geometry.coordinates);
function footprint(route) {
  const cells = new Set(), points = route.geometry.coordinates;
  for (let i = 1; i < points.length; i++) {
    const a = points[i-1], b = points[i];
    const steps = Math.max(1, Math.ceil(Math.hypot((a[0]-b[0])*98000,(a[1]-b[1])*111000)/40));
    for (let j=0;j<=steps;j++) cells.add(`${Math.round((a[0]+(b[0]-a[0])*j/steps)*1000)},${Math.round((a[1]+(b[1]-a[1])*j/steps)*1000)}`);
  }
  return cells;
}

// Remove slower candidates offering no improvement in either exposure metric.
export function usefulRoutes(scored) {
  const ordered = [...scored].sort((a,b)=>a.duration-b.duration || a.riskMetres-b.riskMetres);
  const unique = ordered.filter((r, i) => !ordered.slice(0, i).some(p => routeKey(p) === routeKey(r)));
  const nondominated = unique.filter(r => !unique.some(p => p !== r && p.outside === r.outside &&
    p.duration <= r.duration && p.riskMetres <= r.riskMetres && p.hotspots <= r.hotspots &&
    (p.duration < r.duration || p.riskMetres < r.riskMetres || p.hotspots < r.hotspots)));
  const kept = [];
  for (const route of nondominated) {
    const cells = footprint(route);
    const similar = kept.some(p => p.route.outside === route.outside && p.route.hotspots === route.hotspots &&
      Math.abs(p.route.duration-route.duration) <= 30 && Math.abs(p.route.riskMetres-route.riskMetres) <= Math.max(5,route.riskMetres*.02) &&
      [...cells].filter(c=>p.cells.has(c)).length / Math.max(cells.size,p.cells.size,1) >= .9);
    if (!similar) kept.push({route,cells});
  }
  return kept.map(p=>p.route);
}

// Sample every 40 m, including between vertices: short geometries must not miss hotspots.
export function scoreRoute(route, data) {
  const hits = new Set();
  let outside = false;
  let riskMetres = 0, highRiskMetres = 0;
  const coords = route.geometry.coordinates;
  const kx = 111320 * Math.cos(28.63 * Math.PI / 180);
  for (let i = 1; i < coords.length; i++) {
    const a = coords[i - 1], b = coords[i];
    const length = Math.hypot((b[0] - a[0]) * kx, (b[1] - a[1]) * 110540);
    const steps = Math.max(1, Math.ceil(length / 40));
    for (let j = 0; j <= steps; j++) {
      const p = [a[0] + (b[0] - a[0]) * j / steps, a[1] + (b[1] - a[1]) * j / steps];
      if (!inArea(p, data.grid.bounds)) outside = true;
      if (j < steps && inArea(p, data.grid.bounds) && data.grid.scores) {
        const [s, w, n, e] = data.grid.bounds;
        const row = Math.min(data.grid.rows - 1, Math.floor((n - p[1]) / (n - s) * data.grid.rows));
        const col = Math.min(data.grid.cols - 1, Math.floor((p[0] - w) / (e - w) * data.grid.cols));
        const risk = data.grid.scores[row][col];
        riskMetres += length / steps * risk / 100;
        if (risk >= 45) highRiskMetres += length / steps;
      }
      for (const h of data.hotspots) {
        if (Math.hypot((p[0] - h.lng) * kx, (p[1] - h.lat) * 110540) <= 300) hits.add(h.id);
      }
    }
  }
  return { ...route, hotspots: hits.size, outside, riskMetres, highRiskMetres };
}

export function rankRoutes(routes, data, { preference = 'balanced', maxExtraMinutes = 5 } = {}) {
  const scored = usefulRoutes(routes.map((r, id) => ({ ...scoreRoute(r, data), id })));
  const fastest = Math.min(...scored.map(r => r.duration));
  const eligible = scored.filter(r => !r.outside && r.duration <= fastest + maxExtraMinutes * 60);
  // A kilometre at index 100 adds five illustrative minutes to the comparison cost.
  // This is a preference penalty, never added to the displayed driving ETA.
  const cost = r => r.duration + r.riskMetres * 0.3 + r.hotspots * 30;
  const compare = preference === 'fastest' ? (a, b) => a.duration - b.duration
    : preference === 'lower-risk' ? (a, b) => a.riskMetres - b.riskMetres || a.hotspots - b.hotspots || a.duration - b.duration
    : (a, b) => cost(a) - cost(b) || a.duration - b.duration;
  const recommended = eligible.sort(compare)[0];
  return scored.map(r => ({ ...r, fastest: r.duration === fastest, recommended: r.id === recommended?.id, extraMinutes: (r.duration - fastest) / 60 }));
}

export async function fetchRoutes(start, end, signal, via = null, timeout = via ? 8000 : 15000) {
  const base = (import.meta.env?.VITE_ROUTING_URL || 'https://router.project-osrm.org').replace(/\/$/, '');
  const locations = via ? [start, via, end] : [start, end];
  const points = locations.map(p => `${p.lng},${p.lat}`).join(';');
  if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
  const key = `${base}/${points}`;
  const cached = routeCache.get(key);
  if (cached && Date.now() - cached.time < CACHE_TTL) return cached.routes;
  const ctl = new AbortController();
  let timedOut = false;
  const abort = () => ctl.abort();
  signal?.addEventListener('abort', abort, { once: true });
  const timer = setTimeout(() => { timedOut = true; ctl.abort(); }, timeout);
  try {
  const response = await fetch(`${base}/route/v1/driving/${points}?alternatives=${via ? 'false' : '3'}&overview=full&geometries=geojson&radiuses=${locations.map(() => 500).join(';')}`, { signal: ctl.signal });
  if (!response.ok) throw new Error('Routing service unavailable. Please try again.');
  const result = await response.json();
  if (result.code !== 'Ok' || !result.routes?.length) throw new Error('No road route found. Choose points closer to a road.');
  if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
  if (routeCache.size >= 64) routeCache.delete(routeCache.keys().next().value);
  routeCache.set(key, { time: Date.now(), routes: result.routes });
  return result.routes;
  } catch (error) {
    if (timedOut && !signal?.aborted) throw new Error('Road lookup timed out. Please retry.');
    throw error;
  } finally { clearTimeout(timer); signal?.removeEventListener('abort', abort); }
}

export function detourPoints(routes, data) {
  if (!routes.length || !data.hotspots.length) return [];
  const fastest = [...routes].sort((a, b) => a.duration - b.duration)[0];
  const kx = 111320 * Math.cos(28.63 * Math.PI / 180);
  const encountered = data.hotspots.filter(h => scoreRoute(fastest, { ...data, hotspots: [h] }).hotspots);
  const [s, w, n, e] = data.grid.bounds;
  return encountered.sort((a, b) => b.risk_score - a.risk_score).slice(0, 2).flatMap(h => {
    const coords = fastest.geometry.coordinates;
    let nearest = 0, distance = Infinity;
    coords.forEach((p, i) => {
      const d = Math.hypot((p[0] - h.lng) * kx, (p[1] - h.lat) * 110540);
      if (d < distance) { distance = d; nearest = i; }
    });
    const a = coords[Math.max(0, nearest - 1)], b = coords[Math.min(coords.length - 1, nearest + 1)];
    const dx = (b[0] - a[0]) * kx, dy = (b[1] - a[1]) * 110540;
    const length = Math.hypot(dx, dy) || 1;
    return [-1, 1].map(side => ({ lng: h.lng - side * dy / length * 900 / kx, lat: h.lat + side * dx / length * 900 / 110540 }))
      .filter(p => p.lat > s && p.lat < n && p.lng > w && p.lng < e);
  });
}

export async function fetchRiskAwareRoutes(start, end, data, signal, onBase = () => {}, detourTimeout = 8000) {
  const base = await fetchRoutes(start, end, signal);
  if (signal.aborted) throw new DOMException('Cancelled', 'AbortError');
  onBase(base);
  const candidates = detourPoints(base, data);
  const results = await Promise.allSettled(candidates.map(p => fetchRoutes(start, end, signal, p, detourTimeout)));
  if (signal.aborted) throw new DOMException('Aborted', 'AbortError');
  const all = [...base, ...results.flatMap(r => r.status === 'fulfilled' ? r.value : [])];
  const seen = new Set();
  return {
    routes: all.filter(r => {
      const key = JSON.stringify(r.geometry.coordinates);
      if (seen.has(key)) return false;
      seen.add(key); return true;
    }),
    partial: results.some(r => r.status === 'rejected'),
  };
}
