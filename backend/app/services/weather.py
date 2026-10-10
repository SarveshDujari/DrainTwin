from functools import lru_cache
from time import time
import requests

DELHI = (28.6139, 77.2090)

@lru_cache(maxsize=2)
def _fetch(bucket):
    response = requests.get('https://api.open-meteo.com/v1/forecast', timeout=8,
        params={'latitude': DELHI[0], 'longitude': DELHI[1],
                'hourly': 'precipitation', 'forecast_hours': 24,
                'timezone': 'Asia/Kolkata'})
    response.raise_for_status()
    values = response.json()['hourly']['precipitation'][:24]
    if len(values) != 24:
        raise ValueError('Incomplete 24-hour forecast')
    return {'rainfall_mm': round(sum(float(v or 0) for v in values), 1),
            'source': 'Open-Meteo (next 24 hours)'}

def forecast_rain_mm():
    return _fetch(int(time() // 900))
