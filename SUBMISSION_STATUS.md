# Submission improvements

This implements the selected quick-fix list from the 11 October review, without replacing the scientific model.

## Completed

- Cancel/ignore old intervention, AI and forecast responses; a manual rainfall change supersedes a forecast.
- Distinguish timeout from cancellation, clear old risk layers, and offer scenario retry.
- Reject missing, nonnumeric, negative and nonfinite hourly forecast values; show timestamp range and retrieval time.
- Cache road geometry for ten minutes with a bounded cache; rescore geometry for new rainfall.
- Publish base routes before detours finish; preserve base routes on detour timeout/failure.
- Remove dominated, exact duplicate and near-identical route candidates.
- Withhold percentage exposure comparisons against partially unassessed routes.
- Keep offline summaries as the default/example path and optional AI prose explicitly labelled; reject known guarantee claims while acknowledging that text filters are not proof of truth.
- Correct analysis-resolution labels, emphasize area coverage and fixed monitoring candidates, and add an About panel describing scientific limitations.
- Remove the About this model button and panel at the user's request; keep the limitations in the README and presenter narration guide.
- Add landmark-area presets, coordinate feedback, boundary messages and picking cursor.
- Add selected-route fitting; narrow screens can temporarily hide controls and restore them afterward.
- Align legend/shading thresholds; label rainfall slider and selected route buttons accessibly.
- Rewrite the README for currently visible features and add source ZIP packaging independent of Git tracking state.

## Validation

Validation completed: **33 backend tests passed**, **10 frontend service/routing tests passed**, and the **production build passed**. Focused regression cases cover forecast completeness, unsupported safety claims, API timeout/cancellation, route cache reuse, partial route success, preference limits, duplicate suppression and unassessed comparisons.

Before removing the About panel, browser rehearsal covered landmark selection, changing rainfall, lower-risk preference, endpoint swap, route fitting, model disclosure and responsive panel spacing. At a 375 x 740 viewport, the measured gap between route and rainfall panels was 14 pixels. The reverse landmark journey at 200 mm produced a distinct lower-risk recommendation in that session. The About panel has since been removed; use the narration guide in README. These live road results depend on the provider and may change. AI-provider availability and flood accuracy are not established by these checks.

## Preserved scope

No ML accuracy, observed road safety, hydraulic capacity, live traffic, or validated intervention benefit is claimed. Public routing/weather remain network dependencies. Landmark centres are verified against the linked published locations, not independently surveyed vehicle entrances.

`PROJECT_REVIEW.md` preserves the pre-fix audit. Use this file and README for the current implementation status.
