const BASE = (import.meta.env?.VITE_API_URL || '').replace(/\/$/, '');
export async function request(path, { method = 'GET', body, signal, timeout = 12000 } = {}) {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
  const abort = () => controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  try {
    if (signal?.aborted) { controller.abort(); throw new DOMException('Cancelled', 'AbortError'); }
    const response = await fetch(`${BASE}${path}`, { method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined, signal: controller.signal });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`HTTP ${response.status}: ${detail.slice(0, 250)}`);
    }
    const result = await response.json();
    if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
    return result;
  } catch (error) {
    if (timedOut && !signal?.aborted) throw new Error('Request timed out. Please retry.');
    throw error;
  } finally { clearTimeout(timer); signal?.removeEventListener('abort', abort); }
}
export const simulate = (rainfall_mm, signal) => request('/api/simulate', {method:'POST',body:{rainfall_mm},signal});
export const runIntervention = (hotspot_id, type, rainfall_mm, signal) => request('/api/intervention', {method:'POST',body:{hotspot_id,type,rainfall_mm},signal});
export const getForecast = (signal) => request('/api/weather', {signal});
export const getValidation = (signal) => request('/api/validation?rainfall_mm=150&top_n=12&radius_m=300', {signal});
export const getAgentStatus = () => request('/api/agent/status');
export const getAgentBrief = (hotspot_id, rainfall_mm, use_agent=false, signal) => request('/api/agent/brief', {method:'POST',body:{hotspot_id,rainfall_mm,use_agent},signal,timeout:85000});
