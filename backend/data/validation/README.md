# DrainTwin Phase 2 — validation protocol

This folder starts with **42 source-linked candidate locations**, NOT 42 validated geographic points.

- `ground_truth.csv` preserves each name, road, source, year, evidence type, and coordinate review status.
- `reported`: named in an official historical incident table; `reported_watchlist`: named in a government list of locations reported waterlogged in 2024; `vulnerable`: prospective monitoring list, **not** confirmed event.
- `pending`: no usable coordinate; `provisional`: geocoder or legacy approximate coordinate; `verified`: manually inspected exact location on a map against the named road/underpass and source.
- Do **not** change `verification_status` to `verified` merely because a geocoder returned a coordinate.
- The script **excludes pending/provisional entries**, and points outside the study area. Do not represent candidate counts as test sample size.

## Workflow

1. From `backend`, run `python preprocessing/geocode_ground_truth.py --limit 10 --user-agent "DrainTwinResearch/0.1 (you@example.com)"` to propose coordinates; Nominatim requires identifiable contact and <=1 request/second. Repeat in small batches; geocode suggestions are cached.
2. Open each candidate in a map and verify **the precise road point**, not just a broad locality. Correct latitude/longitude, set `verification_status=verified`, and add a verification note and coordinate source.
3. Run `python preprocessing/evaluate_ground_truth.py --rainfall 150 --top-n 12 --radius 300`.
4. For exploratory debugging only, add `--include-provisional`; **never** cite those figures as validation.
5. Keep evaluation choices (150 mm, top 12, 300 m) fixed **before inspecting results**. Use the capture curve to show sensitivity, not to cherry-pick a favorable number.

## Metrics and limitations

- Hit rate: fraction of verified in-bound observations within 300 metres of a top-N model site.
- Area baseline: proportion of the study area within the same 300-metre buffers, approximated by reproducible equal-area random sampling. Lift = hit rate / area coverage. This is **not** a random-site statistical significance test.
- Terrain-only ablation removes the drainage weight **but reuses fixed sites**; this is not a fully independently generated terrain-only model.
- Source locations can be broad, duplicated, clustered, or repaired since the event. Historical events do not correspond to the user-selected hypothetical rainfall.
- Hold out independent test points if you later tune weights on any of these locations.
- Study boundary is central Delhi, not all of Delhi. Points outside must not enter the denominator.

Sources: Delhi Traffic Police 2021 waterlogging table https://traffic.delhipolice.gov.in/water-logging-area ; PWD 2025 Monsoon Order (2024 reports), p.13 https://pwddelhi.gov.in/writeread/Circular/PWDFloodControl2025.pdf ; New Indian Express 2025 https://www.newindianexpress.com/cities/delhi/2025/Apr/30/ahead-of-monsoon-delhi-pwd-identifies-7-key-waterlogged-spots-for-stricter-oversight
