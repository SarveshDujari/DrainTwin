"""Scenario simulator. Each intervention multiplies some model inputs inside a small footprint.
Results are relative what-if estimates, not engineering guarantees."""
INTERVENTIONS = {
    "drainage":          {"label": "Improve drainage",      "effects": {"drain": .6, "flow": .8, "retain": .85}},
    "permeable_surface": {"label": "Add permeable surface", "effects": {"imperv": .7}},
    "retention_basin":   {"label": "Build retention basin", "effects": {"flow": .65, "retain": .65}},
}

def recommend(flags: dict) -> list[str]:
    recs = []
    if flags["drain"] or flags["flow"]:
        recs.append("drainage")
    if flags["imperv"]:
        recs.append("permeable_surface")
    if flags["elev"] or flags["flow"]:
        recs.append("retention_basin")
    return recs or ["drainage"]
