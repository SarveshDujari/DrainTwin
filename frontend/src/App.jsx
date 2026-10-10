
import { useCallback, useEffect, useState } from "react";
import MapView from "./components/Map.jsx";
import HotspotPopup from "./components/HotspotPopup.jsx";
import HotspotCountControl from "./components/HotspotCountControl.jsx";
import RainfallControl from "./components/RainfallControl.jsx";
import RiskLegend from "./components/RiskLegend.jsx";
import StatsBar from "./components/StatsBar.jsx";
import { simulate, getForecast } from "./services/api.js";

export default function App() {
  const [rain, setRain] = useState(100);
  const [data, setData] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [topN, setTopN] = useState(12);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);

  const total = data?.total_hotspots ?? 0;
  const shown = Math.min(topN, total);

  // Debounce rainfall changes and cancel stale requests.
  useEffect(() => {
    const ctl = new AbortController();

    setLoading(true);

    const t = setTimeout(() => {
      simulate(rain, ctl.signal)
        .then((d) => {
          setData(d);
          setNote((n) =>
            n.startsWith("Backend") ? "" : n
          );
        })
        .catch((e) => {
          if (e.name !== "AbortError") {
            setNote(
              "Backend not reachable. Is uvicorn running?"
            );
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
  }, [rain]);

  // Get the next 24-hour rainfall forecast.
  const useForecast = async () => {
    try {
      const f = await getForecast();

      setRain(
        Math.min(
          250,
          Math.max(0, Math.round(f.rainfall_mm))
        )
      );

      setNote(
        `Next 24h forecast: ${f.rainfall_mm} mm (${f.source})`
      );
    } catch {
      setNote("Forecast unavailable, using scenario");
    }
  };

  const onSelect = useCallback(
    (id) => setSelectedId(id),
    []
  );

  const current = data?.hotspots?.find(
    (h) => h.id === selectedId
  );

  return (
    <div className="app">
      <MapView
        data={data}
        shown={shown}
        selectedId={current?.id}
        onSelect={onSelect}
        validationPoints={[]}
      />

      <header className="card brand">
        <b>🌧️ DrainTwin</b>
        <span>
          Central Delhi · urban flood-risk digital twin
        </span>
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

      <RainfallControl
        value={rain}
        onChange={(value) => {
          setRain(value);
          setNote("");
        }}
        onForecast={useForecast}
        note={note}
        loading={loading}
      />

      <HotspotCountControl
        total={total}
        value={topN}
        onChange={setTopN}
      />

      <RiskLegend />

      {current && (
        <HotspotPopup
          hotspot={current}
          rainfall={rain}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
