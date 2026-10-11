
import { useCallback, useEffect, useRef, useState } from "react";
import MapView from "./components/Map.jsx";
import HotspotPopup from "./components/HotspotPopup.jsx";
import HotspotCountControl from "./components/HotspotCountControl.jsx";
import RainfallControl from "./components/RainfallControl.jsx";
import RiskLegend from "./components/RiskLegend.jsx";
import StatsBar from "./components/StatsBar.jsx";
import RoutePlanner from "./components/RoutePlanner.jsx";
import { simulate, getForecast } from "./services/api.js";

export default function App() {
  const [rain, setRain] = useState(100);
  const [data, setData] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [topN, setTopN] = useState(12);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [simulationError, setSimulationError] = useState('');
  const [retry, setRetry] = useState(0);
  const [forecastBusy, setForecastBusy] = useState(false);
  const forecastRequest = useRef(null);
  const [mapMessage, setMapMessage] = useState('');
  const [fitRequest, setFitRequest] = useState(0);
  const [focusMap, setFocusMap] = useState(false);
  useEffect(() => () => forecastRequest.current?.abort(), []);
  const [routeMode, setRouteMode] = useState(false);
  const [start, setStart] = useState(null);
  const [end, setEnd] = useState(null);
  const [picking, setPicking] = useState(null);
  const [routes, setRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const updateRoutes = useCallback((next) => {
    setRoutes(next);
    setSelectedRoute(next.find(r => r.recommended)?.id ?? next[0]?.id ?? null);
  }, []);
  const pickPoint = useCallback((point) => {
    setMapMessage('');
    if (picking === 'start') { setStart(point); setPicking('end'); }
    else if (picking === 'end') { setEnd(point); setPicking(null); }
  }, [picking]);

  const total = data?.total_hotspots ?? 0;
  const shown = Math.min(topN, total);

  // Debounce rainfall changes and cancel stale requests.
  useEffect(() => {
    const ctl = new AbortController();

    setLoading(true);
    setSimulationError('');
    setData(null);

    const t = setTimeout(() => {
      simulate(rain, ctl.signal)
        .then((d) => {
          if (ctl.signal.aborted) return;
          setData(d);
          setNote((n) =>
            n.startsWith("Backend") ? "" : n
          );
        })
        .catch((e) => {
          if (!ctl.signal.aborted) {
            setData(null);
            setSimulationError(e.message.includes('timed out') ? e.message : 'Scenario unavailable. Check the backend connection and retry.');
          }
        })
        .finally(() => {
          if (!ctl.signal.aborted) {
            setLoading(false);
          }
        });
    }, 200);

    return () => {
      clearTimeout(t);
      ctl.abort();
    };
  }, [rain, retry]);

  // Get the next 24-hour rainfall forecast.
  const useForecast = async () => {
    forecastRequest.current?.abort();
    const ctl = new AbortController(); forecastRequest.current = ctl;
    setForecastBusy(true);
    try {
      const f = await getForecast(ctl.signal);
      if (ctl.signal.aborted) return;

      setRain(
        Math.min(
          250,
          Math.max(0, Math.round(f.rainfall_mm))
        )
      );

      setNote(
        `24-hour forecast: ${f.rainfall_mm} mm. Scenario uses ${Math.min(250, Math.max(0, Math.round(f.rainfall_mm)))} mm. ${f.period_start} to ${f.period_end} (${f.timezone}). Fetched ${new Date(f.fetched_at).toLocaleTimeString()}.`
      );
    } catch {
      if (!ctl.signal.aborted) setNote("Complete forecast unavailable; manual scenario retained.");
    } finally { if (!ctl.signal.aborted) setForecastBusy(false); }
  };

  const onSelect = useCallback(
    (id) => setSelectedId(id),
    []
  );

  const current = data?.hotspots?.find(
    (h) => h.id === selectedId
  );

  return (
    <div className={`app ${routeMode ? 'routing-mode' : ''} ${focusMap && routeMode ? 'route-map-focus' : ''}`}>
      <MapView
        data={data}
        shown={shown}
        selectedId={current?.id}
        onSelect={onSelect}
        validationPoints={[]}
        routePoints={routeMode ? [start, end] : []}
        routes={routeMode ? routes : []}
        selectedRoute={selectedRoute}
        onPoint={routeMode && picking ? pickPoint : null}
        onOutside={() => setMapMessage('Choose a point inside the dashed Central Delhi study area.')}
        fitRequest={fitRequest}
      />

      <header className="card brand">
        <b>🌧️ DrainTwin</b>
        <span>
          Central Delhi · urban flood-risk digital twin
        </span>
        <div className="brand-actions"><button className="chip" onClick={() => { setRouteMode(v => !v); setSelectedId(null); if (!start) setPicking('start'); }}>
          {routeMode ? 'Back to hotspots' : 'Plan a route'}
        </button>
        </div>
      </header>

      <StatsBar
        data={data}
        shown={shown}
      />

      {data?.data_source === "demo" && (
        <div className="banner">
          Demo data (synthetic). Run{" "}
          <code>build_grid.py</code>{" "}
          for real Delhi terrain.
        </div>
      )}

      <div className={routeMode ? 'route-controls' : 'scenario-controls'}>
      {routeMode && <RoutePlanner start={start} end={end} picking={picking} onPick={setPicking}
        message={mapMessage} onFit={() => { setFocusMap(window.innerWidth <= 720); setFitRequest(v => v + 1); }}
        onPreset={(which, point) => { setMapMessage(''); if (which === 'start') setStart(point); else setEnd(point); setPicking(null); }}
        onSwap={() => { setStart(end); setEnd(start); setPicking(null); }}
        onReset={() => { setStart(null); setEnd(null); setPicking('start'); setRoutes([]); }}
        data={loading ? null : data} onRoutes={updateRoutes} selected={selectedRoute} onSelect={setSelectedRoute} />}
      <RainfallControl
        value={rain}
        onChange={(value) => {
          forecastRequest.current?.abort(); setForecastBusy(false);
          setRain(value);
          setNote("");
        }}
        onForecast={useForecast}
        note={note}
        loading={loading}
        forecastBusy={forecastBusy}
        error={simulationError}
        onRetry={() => setRetry(v => v + 1)}
      />
      </div>
      {routeMode && focusMap && <button className="card return-controls" onClick={() => setFocusMap(false)}>Back to route controls</button>}

      {!routeMode && <HotspotCountControl
        total={total}
        value={topN}
        onChange={setTopN}
      />}

      <RiskLegend />

      {!routeMode && current && (
        <HotspotPopup
          key={`${current.id}:${rain}`}
          hotspot={current}
          rainfall={rain}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
