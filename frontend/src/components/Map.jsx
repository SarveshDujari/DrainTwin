import { useEffect, useRef } from "react";
import L from "leaflet";

export const COLORS = { low: "#94a3b8", moderate: "#eab308", high: "#f97316", critical: "#dc2626" };
const AREA = [[28.56, 77.15], [28.70, 77.30]];                       // matches the backend study area
const STOPS = [[25, [234, 179, 8]], [45, [249, 115, 22]], [65, [220, 38, 38]]];   // moderate -> high -> critical

function colour(v) {                                                 // smooth ramp, fully transparent below 20
  let rgb = STOPS[0][1];
  if (v >= STOPS[2][0]) rgb = STOPS[2][1];
  else for (let i = 0; i < 2; i++) {
    const [a, ca] = STOPS[i], [b, cb] = STOPS[i + 1];
    if (v >= a && v < b) rgb = ca.map((x, k) => x + ((cb[k] - x) * (v - a)) / (b - a));
  }
  return [...rgb.map(Math.round), Math.round(Math.max(0, Math.min(1, (v - 20) / 45)) * 0.6 * 255)];
}

function paint({ rows, cols, scores }) {                             // whole risk grid -> one small image
  const cv = document.createElement("canvas");
  cv.width = cols; cv.height = rows;
  const ctx = cv.getContext("2d"), img = ctx.createImageData(cols, rows);
  scores.forEach((row, r) => row.forEach((v, c) => img.data.set(colour(v), (r * cols + c) * 4)));
  ctx.putImageData(img, 0, 0);
  return cv.toDataURL();
}

export default function MapView({ data, shown, selectedId, onSelect, validationPoints = [] }) {
  const el = useRef(null), map = useRef(null), overlay = useRef(null), pins = useRef(null), evidencePins = useRef(null), pick = useRef(onSelect);
  pick.current = onSelect;

  useEffect(() => {                                                  // map starts immediately, independent of the API
    const m = (map.current = L.map(el.current, { preferCanvas: true, zoomControl: false, minZoom: 11 })
      .fitBounds(AREA, { padding: [60, 60] }));
    m.setMaxBounds([[AREA[0][0] - 0.1, AREA[0][1] - 0.1], [AREA[1][0] + 0.1, AREA[1][1] + 0.1]]);
    m.createPane("risk").style.zIndex = 250;                         // above tiles, below pins
    L.control.zoom({ position: "topright" }).addTo(m);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {  // free, no API key
      attribution: "© OpenStreetMap contributors", maxZoom: 19,
    }).addTo(m);
    L.rectangle(AREA, { color: "#475569", weight: 1.2, dashArray: "5 5", fill: false, interactive: false }).addTo(m);
    L.marker([AREA[1][0], AREA[0][1]], {
      interactive: false, icon: L.divIcon({ className: "area-label", html: "Study area · central Delhi", iconSize: [170, 20], iconAnchor: [0, 22] }),
    }).addTo(m);
    pins.current = L.layerGroup().addTo(m);
    evidencePins.current = L.layerGroup().addTo(m);
    const resizeTimer = setTimeout(() => m.invalidateSize(), 100);
    return () => { clearTimeout(resizeTimer); m.remove(); map.current = overlay.current = pins.current = evidencePins.current = null; };
  }, []);

  useEffect(() => {                                                  // risk heat layer: one image, smooth shading
    if (!data || !map.current) return;
    const url = paint(data.grid), [s, w, n, e] = data.grid.bounds;
    if (overlay.current) overlay.current.setUrl(url);
    else overlay.current = L.imageOverlay(url, [[s, w], [n, e]], { pane: "risk", interactive: false }).addTo(map.current);
  }, [data]);

  useEffect(() => {                                                  // pins: top-N full size, the rest small and faded
    if (!data || !pins.current) return;
    pins.current.clearLayers();
    data.hotspots.forEach((h, i) => {
      const top = i < shown, sel = h.id === selectedId;
      const m = L.circleMarker([h.lat, h.lng], {
        radius: sel ? 13 : top ? 9 : 4.5, color: "#fff", weight: top ? 2.5 : 1.5,
        fillColor: COLORS[h.severity], fillOpacity: top ? 1 : 0.4,
      }).addTo(pins.current);
      m.bindTooltip(`#${h.id} · risk ${h.risk_score}`, { direction: "top" });
      m.on("click", () => pick.current(h.id));
    });
  }, [data, shown, selectedId]);

  useEffect(() => {
    if (!evidencePins.current) return;
    evidencePins.current.clearLayers();
    (validationPoints || []).forEach(p => {
      const marker = L.circleMarker([p.lat, p.lng], { radius: 6, color: "#1d4ed8", weight: 2, fillColor: "#fff", fillOpacity: 1 });
      marker.bindTooltip(`Verified historical location: ${p.name}`, { direction: "top" });
      marker.addTo(evidencePins.current);
    });
  }, [validationPoints]);

  return <div ref={el} className="map" />;
}
