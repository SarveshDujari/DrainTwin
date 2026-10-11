import test from 'node:test';
import assert from 'node:assert/strict';
import { scoreRoute, rankRoutes, detourPoints, fetchRiskAwareRoutes, clearRouteCache, exposureReduction } from './routing.js';

const route = (lat, duration = 600) => ({ duration, distance: 4000, geometry: { type: 'LineString', coordinates: [[77.20, lat], [77.24, lat]] } });
const dry = { grid: { bounds: [28.56, 77.15, 28.70, 77.30], rows: 14, cols: 15, scores: Array.from({ length: 14 }, () => Array(15).fill(0)) }, hotspots: [] };
const wet = { grid: { ...dry.grid, scores: dry.grid.scores.map((row, i) => row.map(() => i === 7 ? 90 : 0)) }, hotspots: [{ id: 1, lat: 28.625, lng: 77.22, risk_score: 90 }] };

test('rainfall switches recommendation from fastest to lower exposure', () => {
  const roads = [route(28.625), route(28.65, 720)];
  assert.equal(rankRoutes(roads, dry).find(r => r.recommended).id, 0);
  assert.equal(rankRoutes(roads, wet).find(r => r.recommended).id, 1);
  assert.ok(scoreRoute(roads[0], wet).highRiskMetres > 3000);
});
test('long geometry segments still detect hotspots, cap extra time and unknown area', () => {
  assert.equal(scoreRoute(route(28.625), wet).hotspots, 1);
  assert.equal(rankRoutes([route(28.625), route(28.65, 1000)], wet)[0].recommended, true);
  assert.equal(rankRoutes([route(28.71)], wet)[0].recommended, false);
  assert.deepEqual(detourPoints([route(28.625)], dry), []);
  assert.equal(detourPoints([route(28.625)], wet).length, 2);
});
test('preferences and detour budget change recommendations', () => {
  const roads = [route(28.625), route(28.65, 1020)];
  assert.equal(rankRoutes(roads, wet, { preference: 'lower-risk', maxExtraMinutes: 5 }).find(r => r.recommended).id, 0);
  assert.equal(rankRoutes(roads, wet, { preference: 'lower-risk', maxExtraMinutes: 10 }).find(r => r.recommended).id, 1);
  assert.equal(rankRoutes(roads, wet, { preference: 'fastest', maxExtraMinutes: 10 }).find(r => r.recommended).id, 0);
});
test('wet scenarios request extra road routes, dry scenarios do not', async () => {
  clearRouteCache();
  const original = globalThis.fetch;
  const urls = [];
  globalThis.fetch = async url => {
    urls.push(url);
    return { ok: true, json: async () => ({ code: 'Ok', routes: [route(28.625)] }) };
  };
  try {
    const start = { lat: 28.625, lng: 77.20 }, end = { lat: 28.625, lng: 77.24 };
    const signal = new AbortController().signal;
    await fetchRiskAwareRoutes(start, end, dry, signal);
    assert.equal(urls.length, 1);
    urls.length = 0;
    const result = await fetchRiskAwareRoutes(start, end, wet, signal);
    assert.equal(urls.length, 2); // base geometry is reused across rainfall changes
    assert.equal(result.routes.length, 1); // identical geometry is deduplicated
    assert.equal(result.partial, false);
    clearRouteCache();
    globalThis.fetch = async url => {
      if (url.includes('alternatives=false')) throw new Error('Detour service unavailable');
      return { ok: true, json: async () => ({ code: 'Ok', routes: [route(28.625)] }) };
    };
    const fallback = await fetchRiskAwareRoutes(start, end, wet, signal);
    assert.equal(fallback.partial, true);
    assert.equal(fallback.routes.length, 1);
  } finally { globalThis.fetch = original; clearRouteCache(); }
});

test('detour timeout preserves published base routes; cancellation stays cancellation', async () => {
  clearRouteCache();
  const original = globalThis.fetch;
  const start = { lat:28.625,lng:77.20 }, end = { lat:28.625,lng:77.24 };
  globalThis.fetch = async (url, {signal}) => {
    if (url.includes('alternatives=false')) return new Promise((resolve,reject) => signal.addEventListener('abort', () => reject(new DOMException('Cancelled','AbortError')), {once:true}));
    return {ok:true,json:async()=>({code:'Ok',routes:[route(28.625)]})};
  };
  try {
    let published = false;
    const result = await fetchRiskAwareRoutes(start,end,wet,new AbortController().signal,base => {published = base.length === 1;},10);
    assert.equal(published,true); assert.equal(result.partial,true); assert.equal(result.routes.length,1);
    const ctl = new AbortController(); ctl.abort();
    await assert.rejects(fetchRiskAwareRoutes(start,end,wet,ctl.signal), {name:'AbortError'});
  } finally {globalThis.fetch=original;clearRouteCache();}
});
test('slower equally exposed and exact duplicate routes are removed', () => {
  const result = rankRoutes([route(28.65),route(28.65),route(28.66,800)],dry);
  assert.equal(result.length,1); assert.equal(result[0].duration,600);
});
test('nearly identical geometry is grouped without hiding a useful risk tradeoff', () => {
  assert.equal(rankRoutes([route(28.65),route(28.650001)],dry).length,1);
  assert.equal(rankRoutes([route(28.625),route(28.65,720)],wet).length,2);
});
test('exposure percentages require two completely assessed routes', () => {
  const best={riskMetres:50,outside:false}, fastest={riskMetres:100,outside:false};
  assert.equal(exposureReduction(best,fastest),50);
  assert.equal(exposureReduction(best,{...fastest,outside:true}),null);
  assert.equal(exposureReduction(best,{...fastest,riskMetres:0}),null);
});
