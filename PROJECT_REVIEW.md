# DrainTwin submission review — 11 October 2026

## Scope and conclusion

Reviewed the React frontend, map lifecycle, routing and scoring, FastAPI endpoints, weather integration, susceptibility engine, intervention engine, AI briefing, validation pipeline, terrain/land-cover/waterway preprocessing, tests, build configuration, and submission documentation. This is a code review with local tests and measurements, not an independent hydrological validation, browser/device certification, security audit, or live external-provider availability test. Application code was not changed as part of this review.

The project is a credible scenario-exploration demo. Its greatest immediate opportunities are consistency, reliability, and explanation. The core numerical engine is already fast enough for this demo. Do not replace the model, rebuild the terrain pipeline, train ML, or implement full road-graph routing on submission day.

## Verified evidence

- Backend: 25 tests passed in 3.57 seconds outside the restricted sandbox. Initial sandbox runs encountered temporary-directory permission errors and Windows event-loop socket restrictions; these were environment issues, not established application failures.
- Frontend: four routing tests passed; production build passed.
- Built JavaScript: about 313 kB, 97 kB gzip. CSS: about 25 kB, 9 kB gzip.
- Loaded data: `real`, 64 × 64 cells, 70 fixed candidate hotspot sites. North–south cell spacing is about 243 metres; this is not street-level resolution.
- All arrays checked in the loaded data file contained finite values. This does not verify source accuracy or alignment.
- Historical validation: 42 candidate records, zero accepted verified coordinates, zero verified in-area points.
- Local engine timing: approximately 45 ms for a cold 100 mm scenario and 2 ms for a repeated scenario. This is a single local measurement, not a concurrency/load benchmark. The 100 mm JSON result is approximately 47.5 kB.

| Rainfall, mm/24 h | Active hotspot sites | Land area with index ≥45 |
|---|---:|---:|
| 0 | 0 | 0.0% |
| 25 | 0 | 0.0% |
| 50 | 0 | 0.0% |
| 100 | 37 | 2.5% |
| 150 | 70 | 37.5% |
| 200 | 70 | 76.2% |
| 250 | 70 | 92.2% |

The constant count above 150 mm is mostly explained by all fixed candidates becoming active. It does not mean the entire risk calculation is unchanged. Only approximately 0.37% of land cells hit the numeric cap of 100 at 250 mm in this data.

## A. Fix first: demo correctness and reliability

Estimates below are rough implementation-and-focused-check ranges, not promises. Related fixes share work; do not sum every row into a same-day commitment.

### 1. Old briefing or intervention responses can appear under a new selection

**Evidence:** `frontend/src/components/HotspotPopup.jsx` clears results when the hotspot/rain changes, but `run()` later sets the awaited result unconditionally. `AgentBrief.jsx` has the same pattern in `generate()`.

**Consequence:** Start a slow request, then change the hotspot or rainfall. The previous request can refill the new panel with the old result. Clearing state alone does not cancel pending work.

**Small fix:** Use an AbortController plus a request sequence or `(hotspot ID, rainfall)` key. Only apply the response if it still matches. Reset busy/error state on selection changes. Add a delayed-response regression check.

**Priority:** High. **Effort:** 30–60 minutes for both flows.

### 2. A simulation timeout can silently leave old risk data displayed

**Evidence:** `services/api.js` uses AbortError for its internal 12-second timeout. `App.jsx` ignores all AbortErrors, including that timeout, while retaining previous data. `Map.jsx` returns early when `data` becomes null without clearing old heat/pin layers.

**Consequence:** The slider may show a new rainfall value while the visible map still represents the previous one, or the backend may fail while stale map data remains visible.

**Small fix:** Distinguish timeout from caller cancellation. Track the rainfall attached to each successful result. Clear old map layers on failure, or retain them with an explicit “previous scenario; update failed” state and Retry button. Disable scenario actions until the displayed scenario is current.

**Priority:** High. **Effort:** 30–60 minutes.

### 3. A slow forecast can overwrite a later manual rainfall choice

**Evidence:** `App.jsx::useForecast` applies its result unconditionally. The forecast button has no in-flight lock or cancellation, and manual slider changes do not invalidate an outstanding forecast.

**Small fix:** Disable duplicate forecast requests and invalidate the request when the user edits rainfall. Label it “24-hour forecast” and show the forecast period/fetch time, since it is not observed rainfall right now. Show any rounding/clamping to the 0–250 mm scenario range.

**Priority:** High. **Effort:** 20–40 minutes.

### 4. Missing weather values are treated as zero rainfall

**Evidence:** `backend/app/services/weather.py` sums `float(v or 0)` and checks only that 24 entries exist.

**Consequence:** Missing hourly values can produce an understated total that looks complete.

**Small fix:** Require 24 finite, nonnegative numeric values and return an incomplete-forecast error otherwise. Preserve timestamps from the response. Add null/incomplete-response tests with mocked weather data.

**Priority:** High. **Effort:** 20–30 minutes.

### 5. Every rainfall change repeats road requests and clears existing routes

**Evidence:** `RoutePlanner.jsx` fetch effect depends on the entire `data` object and resets `raw`. `fetchRiskAwareRoutes()` obtains the base routes again before requesting up to four detours.

**Consequence:** Slider experimentation causes flicker, repeated network traffic, and waiting even though road geometry itself has not changed.

**Small fix:** Cache base routes by endpoint pair and routing server; cache detours by endpoint/waypoint combination, with a small bounded TTL cache. Re-score existing geometry immediately; show “checking additional detours” while new geometry arrives. Keep stale/new scenario labels unambiguous.

**Priority:** High. **Effort:** 45–90 minutes.

### 6. A slow detour can discard a successful base route

**Evidence:** `fetchRiskAwareRoutes()` waits for all detours with one shared timeout. If the signal aborts, it throws even when the original road routes were already retrieved. Individual failed detours are handled, but a shared timeout is not a partial-success result.

**Small fix:** Give base-route and detour work separate bounded time budgets. Publish the base routes first; return them with an “additional detours unavailable” note if detour search times out. Preserve true cancellation when endpoints or rainfall change.

**Priority:** High. **Effort:** 30–60 minutes, overlapping with item 5.

### 7. AI explanation validation does not establish factual grounding

**Evidence:** `planner.py::valid_explanation` checks length, digits and a small phrase blacklist. The checker accepted this review probe: “This road is guaranteed to remain safe and the drainage system will prevent flooding during every storm.”

**Small fix today:** Use deterministic briefings as the submission default. Rename “Verified template” in the UI to “Model-based summary” or “Offline summary.” If retaining AI, show it as optional explanatory prose and require the scenario caveat; do not claim that adding another phrase blacklist makes it factually verified.

**Priority:** High for presentation. **Effort:** 15–30 minutes for default/label changes. Reliable semantic verification is outside today's scope.

### 8. Grid resolution is described inconsistently

**Evidence:** `planner.py::fallback_brief` refers to “30 m-scale terrain,” while production calculations operate on 64 × 64 cells with roughly 243 m north–south spacing. The input terrain source and the calculation grid are different resolutions.

**Small fix:** State both: “Terrain derived from finer source data, aggregated to an approximately 240 m analysis grid.” Use current grid metadata rather than hardcoding. Put the study area, analysis resolution, and modelled-data label in one compact info panel.

**Priority:** High for credibility. **Effort:** 15–30 minutes.

## B. Routing improvements worth considering today

### 9. Detours are candidates, not road-level hotspot avoidance

**Evidence:** `routing.js::detourPoints` offsets waypoints 900 m on either side of up to two hotspots on the fastest route. The road service is asked to route through these waypoints; it is not given blocked road segments. The resulting path can still revisit the hotspot or make an inefficient excursion.

**Small fix:** Retain a detour only if it reduces measured exposure or offers a useful time/risk tradeoff. Remove routes dominated by another route with both lower time and lower exposure. If none improves exposure, say “No better detour found within your limit.” Optionally test two offset distances, while limiting request count.

**Priority:** Medium/high. **Effort:** 45–90 minutes. Full graph avoidance should wait.

### 10. Risky stretches without a hotspot centre do not trigger detour search

**Evidence:** Candidate generation is based only on proximity to the fixed hotspot list, although route scoring already uses the full risk grid.

**Small fix:** When the fastest route crosses a substantial high-risk stretch but encounters no hotspot centre, generate one pair of candidates around the highest-exposure stretch. Reuse the existing road-request mechanism and candidate limit.

**Priority:** Medium. **Effort:** 45–90 minutes. More invasive than caching, so optional today.

### 11. Near-identical routes clutter the comparison

**Evidence:** Deduplication compares the exact JSON of route coordinates. Similar paths with slightly different geometry remain separate.

**Small fix:** Group routes by high overlap of sampled road geometry, then retain the faster/lower-exposure representative. For a minimal first pass, suppress obviously dominated routes without introducing a geometry library.

**Priority:** Medium. **Effort:** 30–60 minutes.

### 12. The comparison baseline can contain unassessed road sections

**Evidence:** `rankRoutes` finds the fastest among all routes, then excludes outside-area routes from recommendations. The summary compares risk against that unrestricted fastest route even though risk beyond the grid is not measured.

**Small fix:** Keep fastest overall for travel-time context, but compare exposure percentages only against a fully assessed baseline. If the fastest route leaves the study area, explicitly withhold its exposure-reduction comparison.

**Priority:** Medium/high. **Effort:** 20–40 minutes.

### 13. “High-risk distance” uses index 45 while the displayed grid is rounded

**Evidence:** Route scoring uses integer `grid.scores`; hotspot activation uses unrounded engine scores. Values just below 45 can round up and contribute to the route's high-risk distance without activating a hotspot.

**Small fix:** Return one decimal place for routing scores, or document the rounding tolerance and consistently derive displayed thresholds. Keep the precise internal risk and display formatting separate.

**Priority:** Low/medium. **Effort:** 20–40 minutes. This is a small boundary effect, not a reason to rebuild the model.

### 14. Balanced-routing penalties are subjective

**Evidence:** The comparison cost adds 0.3 seconds per risk-weighted metre and 30 seconds per nearby hotspot. These are preferences, not measured flood delays; hotspot and grid exposure can overlap conceptually.

**Small fix:** Keep the displayed driving ETA separate, expose a short “How routes are compared” explanation, and use named constants. Use one primary exposure penalty and treat hotspot count as explanation or tie-breaker if double-counting feels too strong. Do not tune these constants just to force an impressive demo route.

**Priority:** Medium. **Effort:** 20–40 minutes for explanation/cleanup; changing weights needs scenario checks.

## C. UI, accessibility, and performance

### 15. Endpoint selection lacks useful feedback

**Evidence:** Out-of-study-area clicks in `Map.jsx` are silently ignored. Start/destination controls show only ticks, and routing is mouse/map driven.

**Small fix:** Show a short outside-area message, coordinates or a selected landmark label, and a crosshair while picking. Add two or three prechecked landmark presets for a repeatable demo and a keyboard-accessible alternative. Confirm each preset's actual coordinates before labelling it.

**Priority:** Medium/high for demo smoothness. **Effort:** 30–60 minutes. A full geocoding integration is unnecessary today.

### 16. Selected routes do not automatically fit the available map area

**Evidence:** The map fits the whole study area once, and route rendering does not adjust the view or account for the left panel.

**Small fix:** Add “Show selected route” using the route bounds and padding for the control column. Avoid auto-zooming after every slider movement.

**Priority:** Medium. **Effort:** 15–30 minutes.

### 17. Mobile/map accessibility remains incomplete

**Evidence:** Rainfall slider has no explicit accessible name. The hotspot list is hidden in CSS and not mounted in App; map circles are the main hotspot-selection mechanism. Route choices do not expose selected state with `aria-pressed` or an equivalent pattern. Many layout rules are repeated through phase-specific overrides.

**Small fix:** Add accessible labels and selected state; restore a compact optional list or selector; test tab order and 375 px/short-laptop layouts. Keep the recent shared route/rain column. Consolidate only conflicting CSS rules, not the entire stylesheet today.

**Priority:** Medium. **Effort:** 30–60 minutes for targeted improvements.

### 18. Legend and shading thresholds disagree slightly

**Evidence:** The legend says values below 25 are not shaded, but `Map.jsx::colour` starts opacity above 20.

**Small fix:** Use 25 consistently or change the legend to describe the fade-in accurately. Prefer one shared set of thresholds.

**Priority:** Low but very easy. **Effort:** 5–10 minutes.

### 19. Layers and route scores are recomputed more often than needed

**Evidence:** App passes new arrays for `routePoints`, empty routes, and validation points on renders. Map effects clear/recreate layers based on those array identities. Preference changes call `rankRoutes`, which samples and scores every geometry again. Detour hotspot checks also invoke the full scorer once per hotspot.

**Small fix:** Memoize stable arrays; separate geometry scoring from ranking preferences; use a lightweight hotspot-intersection helper for detour detection. Prioritize only if profiling shows visible lag on the demo machine.

**Priority:** Low/medium. **Effort:** 30–60 minutes. Network latency currently deserves more attention than engine optimization.

## D. Prediction, reasoning, and data integrity

### 20. No demonstrated prediction accuracy

**Evidence:** There are zero verified evaluation coordinates. The weights and thresholds are hand-set; historical records are not matched to the simulated rainfall event. Existing passing tests establish software properties, not real-world forecasting skill.

**Small action today:** Put “scenario-based susceptibility; accuracy not yet established” in the demo/info panel. Show validation status rather than a percentage. If a few locations can genuinely be checked, describe them as illustrative checks; do not manufacture a validation claim.

**Priority:** Essential disclosure. **Effort:** 15–30 minutes for UI/reporting. Independent validation is future work.

### 21. Hotspot counts saturate because locations are fixed

**Evidence:** All 70 candidate sites are active at 150 mm. Coverage still increases from 37.5% to 92.2% between 150 and 250 mm.

**Small fix:** Explain “70 fixed monitoring candidates” and emphasize affected-area coverage alongside counts. A compact rainfall-versus-coverage display would communicate change better than forcing additional hotspot pins.

**Priority:** Medium/high. **Effort:** 20–45 minutes. Do not change site detection just to make counts rise.

### 22. A 24-hour total omits rainfall intensity and persistence

**Evidence:** The engine takes a single scalar rain total; it has no hourly storm progression, measured drain capacity, antecedent storage, or observed road closure input. Zero rainfall yields zero modelled hazard regardless of prior ponding.

**Small action today:** State “24-hour rainfall scenario” consistently and make clear that zero modelled hazard does not establish that roads are currently dry. Keep hourly intensity, residual water and hydraulic dynamics in future work.

**Priority:** Essential scope clarification. **Effort:** 10–20 minutes for wording; a valid dynamic model is too large today.

### 23. Waterway proximity is not verified storm-drain capacity

**Evidence:** OSM preprocessing includes drains, ditches, canals, streams and rivers. The core model treats greater distance as worse; the experimental proxy also considers nearness to waterways as a risk contributor. They represent different possible mechanisms.

**Small fix:** Label the input “mapped waterway proximity,” explain that capacity/blockage is unknown, and keep the experimental proxy separate. Do not blend it into production without validation.

**Priority:** Medium for reasoning clarity. **Effort:** 15–30 minutes for labels/explanation.

### 24. Preprocessing caches lack version/provenance checks

**Evidence:** `build_grid.py` reuses stage files based on existence alone. Output has no build timestamp, pipeline version, source-completeness flag, or explicit `--no-osm` metadata. Any file named `delhi_grid.npz` is called `real` by the engine.

**Small fix:** Add a metadata sidecar with bounds, shape, source dates, pipeline version and whether waterways were omitted. Check it at startup and display missing-input status. Preserve the current working dataset today; do not invalidate/download every cache before submission.

**Priority:** Medium. **Effort:** 30–60 minutes for metadata and checks; full reprojection/versioned data pipelines can wait.

### 25. Terrain flow and alignment are approximations

**Evidence:** `common.py::d8_flow_acc` chooses the lowest lower neighbour rather than slope divided by neighbour distance; flats/pits stop flow. DEM crops are block-averaged while other grids are assembled on geographic bounds. These deserve alignment checks before fine-grained accuracy claims.

**Small action today:** Retain the explicit approximation labels and document these limitations. Do not silently change flow routing and regenerate all predictions on deadline day. Later: examine sinks, use distance-aware D8, and reproject inputs onto an explicit common grid with independent checks.

**Priority:** Future science improvement. **Effort today:** 10–20 minutes for documentation; scientific fixes are not a quick patch.

### 26. Intervention reductions are assumed, not observed effects

**Evidence:** `interventions.py` applies fixed multipliers. `build_evidence` ranks options by their modelled reduction, although costs, feasibility, and capacity are absent. Deterministic briefing already includes important caveats.

**Small fix:** Preserve “illustrative scenario” wording and show a brief description of which assumption changes. Avoid presenting the top numeric reduction as the best engineering investment. No new optimization engine is needed.

**Priority:** Medium for presentation. **Effort:** 15–30 minutes.

## E. Backend, testing, and submission readiness

### 27. AI timeout does not stop the underlying generation

**Evidence:** A new ThreadPoolExecutor is created per provider/request; shutdown uses `wait=False`. The source correctly notes that timed-out work can continue. Up to two provider waits can consume around 70 seconds with current defaults.

**Small fix:** Keep offline default, add a bounded concurrency gate and cache briefings by site/scenario/provider, and use SDK-level timeouts when verified supported. Return a clear busy/fallback state. Avoid repeated AI calls during the presentation.

**Priority:** Medium locally; high if publicly exposed. **Effort:** 30–60 minutes for basic concurrency protection.

### 28. Public deployment has no application-level abuse protection

**Evidence:** The API has no authentication, rate limiting, or concurrency limits for expensive briefing calls. CORS limits browser origins but does not authorize API users.

**Small fix if publishing today:** Protect or disable the AI endpoint, apply platform/proxy rate limits, restrict configured origins, and keep keys server-side. For a local demo, this is not the first blocker. No specific dependency vulnerability is claimed by this review.

**Priority:** Conditional on public exposure. **Effort:** 30–60 minutes depending on hosting.

### 29. Passing tests omit important user flows

**Evidence:** Current tests cover numerical invariants, several API responses, and mocked route ranking/search. They do not establish browser layout, forecast race handling, outdated briefing handling, external-service availability, or semantic truth of AI text. One phase-three test assumes the dataset has no verified points, so legitimate future validation can break it.

**Small fix:** Add focused regression checks for the actual fixes above. Mock validation input in tests instead of asserting the production dataset stays unverified. Rehearse a short browser checklist: endpoint swap, rapid rainfall edits, delayed response, service failure, no-risk scenario, high-risk scenario, narrow viewport.

**Priority:** High for the changed flows. **Effort:** 30–60 minutes plus the final rehearsal.

### 30. Reproducibility and submission documentation need cleanup

**Evidence:** Python requirements are unpinned. The Vite proxy applies to development; a deployed frontend needs its API URL configured. README retains old incomplete phase checkboxes despite implemented features and references a historical-validation panel that is not mounted in the current App. `.gitignore` ends with `README.md`, overriding its earlier exception for newly added README files; the root README is already tracked, so its current changes are not ignored. New routing files are currently untracked.

**Small fix:** Record tested Python/package versions without upgrading everything; verify the deployed API URL/CORS if deploying. Rewrite the README around features actually visible today, add a one-minute demo flow and limitations, and explicitly include the new routing files in the submitted archive/commit. Review files before staging; do not blindly include secrets or generated data caches.

**Priority:** High before submission. **Effort:** 30–45 minutes.

## Practical order for the remaining time

1. **Correctness first (about 1–2 hours):** old-result guards, explicit timeout/stale-map behavior, forecast completeness and selection protection (items 1–4). Keep the scope small and verify each changed flow.
2. **Route reliability next (about 1–1.5 hours):** cache base geometry and return partial results when detours fail (5–6). If time remains, suppress dominated detours (9).
3. **Credibility and polish (about 30–60 minutes):** use offline briefing by default, correct grid/forecast labels, explain fixed hotspot counts and unvalidated predictions, align legend threshold (7–8, 18, 20–22).
4. **Freeze and rehearse (about 30–45 minutes):** test suite, build, browser checks, working endpoint pair, README/submission contents. Include a clearly labelled saved demonstration recording if internet failure would otherwise derail the presentation.

If fewer than two hours remain, prioritize items 1–4, accurate labels, submission file inclusion, and a rehearsal. Do not attempt all 30 items. Keep full hydraulic modelling, live traffic, ML training, comprehensive geocoding, road-graph avoidance, citywide expansion, and terrain rebuilding out of today's submission scope.
