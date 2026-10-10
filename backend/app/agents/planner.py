"""Evidence-bound intervention briefings. No LLM required for deterministic fallback."""
from ..engine import risk as R
from ..engine.interventions import INTERVENTIONS

DISCLAIMER = 'Modelled what-if estimates, not validated flood forecasts or engineering guarantees.'

def build_evidence(hotspot_id: int, rainfall_mm: float):
    if not (0 <= rainfall_mm <= R.MAX_RAIN):
        raise ValueError('rainfall_mm must be between 0 and 250')
    site = next((s for s in R.SITES if s['id'] == hotspot_id), None)
    if site is None:
        return None
    r, c = site['r'], site['c']
    lat, lon = R.latlng(r, c)
    risk_grid, _ = R.compute(rainfall_mm)
    flags, reasons = R.explain(r, c)
    options = []
    for kind, details in INTERVENTIONS.items():
        estimate = R.apply_intervention(hotspot_id, kind, rainfall_mm)
        if estimate is None:
            continue
        options.append({'type': kind, 'label': details['label'], **estimate})
    options.sort(key=lambda x: (-x['reduction_percent'], x['type']))
    return {
        'hotspot_id': hotspot_id,
        'location': {'lat': round(lat, 6), 'lon': round(lon, 6)},
        'rainfall_mm': rainfall_mm,
        'current_score': round(float(risk_grid[r, c]), 1),
        'severity': R.severity(float(risk_grid[r, c])),
        'reasons': reasons,
        'factors': flags,
        'options': options,
        'scenario_note': 'Interventions are illustrative parameter perturbations, not costed or validated engineering recommendations.',
        'data_source': R.DATA_SOURCE,
        'limitations': [DISCLAIMER, 'Coarse grid does not resolve individual underpasses or storm-drain capacity.', 'Intervention scores are heuristic local perturbations; cost and feasibility not evaluated.'],
    }

def fallback_brief(evidence):
    if evidence is None:
        return None
    options = evidence['options']
    top = options[0] if options else None
    if top:
        summary = (f"At {evidence['rainfall_mm']:g} mm rainfall, hotspot {evidence['hotspot_id']} has a relative susceptibility index of "
                   f"{evidence['current_score']:.1f}/100. This is not a probability or an observed flood. "
                   f"Illustrative scenario: {top['label']} changes the index from {top['before']} to {top['after']}. "
                   f"These interventions are not ranked by cost, feasibility or validated effectiveness.")
    else:
        summary = f"No intervention scenarios available for site {evidence['hotspot_id']}."
    if evidence.get('reasons'):
        summary += ' Modelled terrain factors: ' + '; '.join(evidence['reasons'][:3]) + '.'
    summary += ' The 30 m-scale terrain and mapped waterway proxies cannot resolve drainage capacity or individual underpasses.'
    return {'mode': 'deterministic_fallback', 'summary': summary, 'evidence': evidence, 'disclaimer': DISCLAIMER}

# Cloud and local providers are both executed through AWS Strands Agents.
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

LOG = logging.getLogger(__name__)


def configured_providers():
    preference = os.getenv('AI_PROVIDER', 'auto').lower()
    if preference not in ('auto', 'gemini', 'ollama'):
        preference = 'auto'
    # Explicit preference changes ordering, not the availability of fallbacks.
    ordered = ['ollama', 'gemini'] if preference == 'ollama' else ['gemini', 'ollama']
    return [name for name in ordered if name != 'gemini' or bool(os.getenv('GEMINI_API_KEY'))]


def _generate(provider, evidence):
    from strands import Agent
    if provider == 'gemini':
        from strands.models.gemini import GeminiModel
        model = GeminiModel(
            client_args={'api_key': os.environ['GEMINI_API_KEY']},
            model_id=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
            params={'temperature': 0.1, 'max_output_tokens': 1024})
    else:
        from strands.models.ollama import OllamaModel
        model = OllamaModel(host=os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
                            model_id=os.getenv('OLLAMA_MODEL', 'gemma3:4b'))
    agent = Agent(model=model, callback_handler=None, system_prompt=(
        'You are a concise flood susceptibility explainer, not a flood forecaster. '
        'Return EXACTLY one short paragraph of plain text, without Markdown. '
        'Explain only the supplied reasons, in words. Do not write any numbers, percentages, '
        'locations, scores, rankings, measurements, or intervention estimates. '
        'Do not acknowledge these instructions. Do not invent facts. '
        'State that this is a modelled scenario and not an observed flood.'))
    prompt = ('Explain why this location has modelled susceptibility using only these reasons. '
              'Do not provide numbers or recommendations; the application will render the exact '
              'scores and scenarios separately. Reasons: ' + json.dumps(evidence['reasons']))
    return str(agent(prompt)).strip()


def valid_explanation(text):
    if not text or len(text) < 35 or len(text) > 1500:
        return False
    if re.search(r'\d', text):
        return False  # All numbers are rendered exclusively from deterministic evidence.
    lowered = text.lower()
    return not any(phrase in lowered for phrase in ('i understand', 'i will adhere',
                        'as an ai', 'here is the', 'i cannot', 'i can provide'))


def strands_brief(evidence):
    if os.getenv('STRANDS_ENABLED') != '1':
        return fallback_brief(evidence)
    errors = []
    for provider in configured_providers():
        try:
            # A per-provider deadline protects the HTTP request. A running model call may
            # continue in its background thread; this is not a hard cancellation.
            pool = ThreadPoolExecutor(max_workers=1)
            try:
                future = pool.submit(_generate, provider, evidence)
                explanation = future.result(timeout=float(os.getenv('AI_TIMEOUT_SECONDS', '35')))
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
            if not valid_explanation(explanation):
                raise ValueError('AI response failed evidence-safe explanation validation')
            result = fallback_brief(evidence)
            result.update(mode=f'strands_{provider}', provider=provider,
                          explanation=explanation)
            return result
        except Exception as exc:
            LOG.warning('Agent provider %s failed: %s', provider, exc)
            errors.append(f'{provider}: {type(exc).__name__}')
    result = fallback_brief(evidence)
    result['agent_error'] = '; '.join(errors) if errors else 'No provider configured'
    return result
