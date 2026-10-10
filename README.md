# 🌧️ DrainTwin
Urban flood-risk digital twin for central Delhi: a transparent geospatial risk model, stable hotspot sites,
confidence estimates, and a what-if intervention simulator on one zoomable map. 100% free data and tools.

## Run
```bash
# backend (Python 3.10+)
cd backend && python -m pip install -r requirements.txt
python preprocessing/make_demo_data.py       # only if you have no real grid yet -> data/delhi_grid_demo.npz
python -m uvicorn app.main:app --reload      # http://localhost:8000/docs

# frontend (new terminal, Node 18+)
cd frontend && npm install && npm run dev    # http://localhost:5173

# tests
cd backend && python -m pip install -r requirements-dev.txt && python -m pytest -q
```

## Real data (replaces the demo grid)
```bash
cd backend && python -m pip install -r requirements-data.txt
python preprocessing/build_grid.py           # DEM + WorldCover + OSM -> data/delhi_grid.npz
python preprocessing/validate.py
```
The API uses `data/delhi_grid.npz` when it exists, otherwise the synthetic `delhi_grid_demo.npz`
(the UI shows a "Demo data" banner). **Re-run `build_grid.py` after updating**: Phase 1 added a water mask
and a DEM edge buffer. An older grid still works, just without the water mask.

## How the model works (Phase 1)
`risk = 100 · hazard^0.6 · (0.25 + 0.75 · susceptibility)`
- **hazard**: SCS Curve Number runoff depth, so light rain on permeable ground produces exactly zero (nothing is shaded at ~10 mm).
- **susceptibility**: 0.35 runoff convergence + 0.30 local depression (below the ~1.7 km neighbourhood) + 0.20 flatness + 0.15 distance to drains.
- **Hotspot sites** are fixed local maxima, so a hotspot's ID and position never change with the slider; it simply appears once its score passes 45.
- **Confidence**: 100 re-runs with perturbed weights / curve numbers; each hotspot shows how often it is still flagged, and a plausible score range.
- **Explanations** list only what is unusual about a spot compared with the area median, with real numbers.
- **Interventions** rescale inputs within a ~500 m radius and re-score. They are relative what-if estimates, not engineering guarantees.
- Water bodies are masked and never flagged.

Assumptions to state honestly: curve numbers (61 open ground, 98 paved), the weights, and the score thresholds (25/45/65)
are hand-set, not fitted. Phase 2 validates them against known waterlogging points.

## Status
- [x] Phase 1: engine v2, stable sites, top-N slider, canvas risk layer, confidence, tests
- [ ] Phase 2: ground-truth set and validation (hit rate vs. chance)
- [ ] Phase 3: better signals (OSM underpasses, height above drain, runoff routing, 128x128 grid, storm replay)
- [ ] Phase 4: Strands Agents explainer / intervention planner
- [ ] Phase 5: polish, docs, demo   |   Phase 6 (optional): AWS deployment

## Phase 2: historical validation (added)

The `backend/data/validation/ground_truth.csv` contains **42 source-linked candidate locations**, not 42 verified coordinates. This is intentionally a research/verification queue; no accuracy number is displayed until exact coordinates are manually reviewed. See `backend/data/validation/README.md` for the verification protocol and source links.

From `backend`:

```powershell
python preprocessing/evaluate_ground_truth.py --rainfall 150 --top-n 12 --radius 300
python -m pytest -q
```

To suggest (not verify) coordinates, use `python preprocessing/geocode_ground_truth.py --limit 10 --user-agent "DrainTwinResearch/0.1 (your-email@example.com)"`. Inspect suggested locations, correct them, and mark only genuinely checked points `verified` in the CSV. The optional **Historical validation** map panel calls `GET /api/validation` and shows verified points and results. If no points are verified, it correctly withholds accuracy statistics. A 300 m radius and 150 mm scenario are predeclared defaults, not optimized to the results.

**Caution:** The current terrain-only comparison is a drainage-weight ablation on fixed hotspot candidate sites; it is not a fully independent baseline. The area-coverage comparison is descriptive, not a significance test.

## Phase 4–5: local AI advisory in the map

Click a hotspot, then choose **Offline briefing** (always available) or **AI briefing** (AWS Strands Agents with local Ollama). The interface displays the returned mode, evidence-grounded summary, and disclaimer. If an AI request fails, the API may explicitly return `deterministic_fallback` with `agent_error`; the interface labels this as offline rather than falsely claiming AI execution.

Optional local AI setup (PowerShell, from `backend`):

```powershell
python -m pip install -r requirements-agents.txt
ollama pull gemma3:4b
$env:STRANDS_ENABLED = "1"
$env:OLLAMA_HOST = "http://localhost:11434"
$env:OLLAMA_MODEL = "gemma3:4b"
python -m uvicorn app.main:app --reload
```

In another terminal, start the frontend with `npm install` and `npm run dev`. Ollama must be running. Verify `GET /api/agent/status` and use the map's AI briefing button. No AWS account or paid LLM API is needed for this local path. The model can be slow on limited hardware; offline briefing is the reliable demo fallback.

### Demo flow

1. Start backend and frontend; confirm the real grid is loaded (no synthetic-data banner).
2. Adjust rainfall to 150 mm and observe hotspot counts and relative risk shading.
3. Click a hotspot to inspect location-specific evidence and uncertainty.
4. Try a modelled intervention and inspect before/after score.
5. Click **Offline briefing**, then optionally **AI briefing** to demonstrate Strands + Ollama.
6. Open historical validation panel: explain that candidate locations are **not verified ground truth** and that accuracy is not yet established.

### Current scope and limitations

- The 64×64 Central Delhi grid covers `[28.56, 77.15, 28.70, 77.30]` (south, west, north, east). It does not represent all Delhi.
- The Phase 3 spatial diagnostics and 80/20 comparison are exploratory; they are not proven to improve predictive skill.
- Phase 2 has 42 candidate records but requires independent coordinate verification before publishing hit rate or lift.
- Risk and intervention scores are heuristic susceptibility indicators, not flood probabilities, observed water depth, or engineered drainage designs.
- AI text is generated from the existing evidence and is not independently verified. The model cannot assess cost, site access, or construction feasibility.
- Historical storm replay, source-resolution 128×128 preprocessing, and reliable underpass extraction are not complete.
- Optional AWS deployment remains out of scope for the local demo.

## Phase 5.1 — Gemini / Ollama / offline advisory

The deterministic risk engine is authoritative for numerical values. AWS Strands
Agents may add **only a prose explanation**. Any AI response containing digits,
acknowledging the prompt, or failing basic checks is rejected. Numeric scores and
illustrative interventions are always rendered from the engine's evidence. This
is a safety guard, **not** a complete factual verification of AI prose.

Backend setup (PowerShell, from `backend/`):

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-agents.txt
Copy-Item .env.example .env
# Edit .env; GEMINI_API_KEY is optional. Do not commit your key.
python -m uvicorn app.main:app --reload
```

- `AI_PROVIDER=auto`: Gemini first when `GEMINI_API_KEY` is set, then local Ollama,
  then a deterministic template.
- `AI_PROVIDER=ollama`: local first, Gemini second if configured.
- `AI_PROVIDER=gemini`: cloud first, local second.
- `STRANDS_ENABLED=0`: deterministic only.
- Ollama must be running, and its configured model installed (e.g.
  `ollama pull gemma3:4b`). No AWS account is needed for local Strands.
- The `/api/agent/status` endpoint reports configuration, **not** a successful
  live health check. An attempted briefing determines actual availability.
- `AI_TIMEOUT_SECONDS` sets a per-provider wait limit. An underlying blocking
  model request may continue after the timeout; this is not hard cancellation.
- Gemini API access may have free-tier quotas depending on model and account; check current Google AI Studio limits; cloud requests send hotspot
  evidence to the provider. Never place the API key in Vite frontend variables.

Frontend: `cd frontend; npm install; npm run dev`. Optional
`frontend/.env`: `VITE_API_URL=http://127.0.0.1:8000` for a separately hosted
frontend. Leave blank when using the included Vite proxy.

The validation panel now uses a **fixed** 150 mm / top 12 / 300 m setup and
withholds performance figures when fewer than 10 manually verified in-area
points exist. This is not a validated flood prediction model.

### Outstanding scientific and submission work

- Manually verify historical points and their source dates; replace stale
  evaluation artifacts. Current data are insufficient for accuracy claims.
- Hydrology: revisit hotspot saturation/spacing, DEM pits, correlated DEM
  uncertainty, slope thresholds, and the conflicting waterway proxy.
- Add measured intensity/capacity data before calling interventions engineering
  recommendations. Retention basin results remain heuristic what-if scenarios.
- Test on real mobile devices, add accessible hotspot list and map clustering.
- Run cloud Gemini and local Ollama end-to-end on your machine; build frontend;
  capture screenshots, demo video, and reproducible test outputs.
- Harden public deployment with authentication/rate limits, pinned dependencies,
  request cancellation, and observability before exposing the agent endpoint.

## Phase 5.2 release notes

See [PHASE5_2_RELEASE_NOTES.md](PHASE5_2_RELEASE_NOTES.md) for changes, limitations, test status, and outstanding work. The susceptibility index is **not** a flood probability or a validated forecast. No historical predictive accuracy is claimed.
