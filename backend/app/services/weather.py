from functools import lru_cache
from time import time
from datetime import datetime, timezone
import math
import requests

DELHI = (28.6139, 77.2090)

@lru_cache(maxsize=2)
def _fetch(bucket):
    response = requests.get('https://api.open-meteo.com/v1/forecast', timeout=8,
        params={'latitude': DELHI[0], 'longitude': DELHI[1],
                'hourly': 'precipitation', 'forecast_hours': 24,
                'timezone': 'Asia/Kolkata'})
    response.raise_for_status()
    hourly = response.json()['hourly']
    values = hourly['precipitation'][:24]
    times = hourly['time'][:24]
    if len(values) != 24 or len(times) != 24 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Incomplete 24-hour forecast')
    return {'rainfall_mm': round(sum(values), 1),
            'period_start': times[0], 'period_end': times[-1], 'timezone': 'Asia/Kolkata',
            'fetched_at': datetime.now(timezone.utc).isoformat(),
            'source': 'Open-Meteo (24 hourly precipitation intervals)'}

def forecast_rain_mm():
    return _fetch(int(time() // 900))
