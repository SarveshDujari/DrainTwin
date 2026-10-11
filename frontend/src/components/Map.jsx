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
  return [...rgb.map(Math.round), Math.round(Math.max(0, Math.min(1, (v - 25) / 40)) * 0.6 * 255)];
}

function paint({ rows, cols, scores }) {                             // whole risk grid -> one small image
  const cv = document.createElement("canvas");
  cv.width = cols; cv.height = rows;
  const ctx = cv.getContext("2d"), img = ctx.createImageData(cols, rows);
  scores.forEach((row, r) => row.forEach((v, c) => img.data.set(colour(v), (r * cols + c) * 4)));
  ctx.putImageData(img, 0, 0);
  return cv.toDataURL();
}

export default function MapView({ data, shown, selectedId, onSelect, validationPoints = [], routePoints = [], routes = [], selectedRoute, onPoint, onOutside, fitRequest }) {
  const routeLayer = useRef(null), pointHandler = useRef(onPoint);
  const outsideHandler = useRef(onOutside);
  outsideHandler.current = onOutside;
  pointHandler.current = onPoint;
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
    routeLayer.current = L.layerGroup().addTo(m);
    m.on('click', e => {
      const { lat, lng } = e.latlng;
      if (lat >= AREA[0][0] && lat <= AREA[1][0] && lng >= AREA[0][1] && lng <= AREA[1][1]) pointHandler.current?.({ lat, lng });
      else if (pointHandler.current) outsideHandler.current?.();
    });
    const resizeTimer = setTimeout(() => m.invalidateSize(), 100);
    return () => { clearTimeout(resizeTimer); m.remove(); map.current = overlay.current = pins.current = evidencePins.current = null; };
  }, []);

  useEffect(() => {                                                  // risk heat layer: one image, smooth shading
    if (!map.current) return;
    if (!data) { if (overlay.current) { overlay.current.remove(); overlay.current = null; } return; }
    const url = paint(data.grid), [s, w, n, e] = data.grid.bounds;
    if (overlay.current) overlay.current.setUrl(url);
    else overlay.current = L.imageOverlay(url, [[s, w], [n, e]], { pane: "risk", interactive: false }).addTo(map.current);
  }, [data]);

  useEffect(() => {                                                  // pins: top-N full size, the rest small and faded
    if (!pins.current) return;
    pins.current.clearLayers();
    if (!data) return;
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

  useEffect(() => {
    if (!routeLayer.current) return;
    routeLayer.current.clearLayers();
    [...routes].sort((a, b) => Number(a.id === selectedRoute) - Number(b.id === selectedRoute)).forEach(r => {
      L.geoJSON(r.geometry, { style: { color: r.id === selectedRoute ? '#0d9488' : '#64748b', weight: r.id === selectedRoute ? 6 : 3, opacity: r.id === selectedRoute ? 0.95 : 0.5 }, interactive: false }).addTo(routeLayer.current);
    });
    routePoints.forEach((p, i) => {
      if (p) L.marker([p.lat, p.lng], { interactive: false }).bindTooltip(i === 0 ? 'Start' : 'Destination', { permanent: true }).addTo(routeLayer.current);
    });
  }, [routes, routePoints, selectedRoute]);

  useEffect(() => {
    if (!fitRequest || !map.current) return;
    const route = routes.find(r => r.id === selectedRoute);
    if (!route) return;
    const m = map.current, size = m.getSize();
    const panelWidth = document.querySelector('.route-controls')?.getBoundingClientRect().width || 0;
    m.fitBounds(L.geoJSON(route.geometry).getBounds(), { paddingTopLeft: [panelWidth + 12, 120], paddingBottomRight: [30, size.x > 720 ? 160 : 75], maxZoom: 15 });
  }, [fitRequest]);

  return <div ref={el} className={`map ${onPoint ? 'picking-point' : ''}`} />;
}
