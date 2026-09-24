# -*- coding: utf-8 -*-
# Python 3
"""Wetterdaten aus mehreren abrufbaren Quellen, fail-soft.

Quellen (in dieser Reihenfolge):
  1. Open-Meteo (https://open-meteo.com) - frei, ohne API-Key, dokumentiert.
     Standardquelle, damit Wetter ohne Konfiguration funktioniert.
  2. OpenWeatherMap - genutzt, wenn der Nutzer einen eigenen API-Key hinterlegt.

Fail-soft: ohne Daten wird eine leere Zeile geliefert - Navigation und
Wiedergabe duerfen nie beeintraechtigt werden. Ergebnisse liegen im volatilen
Cache mit TTL (schont API-Limits und die Geraete).
"""

import json
import time

from resources.lib.config import cConfig
from resources.lib.tools import logger

_OWM_API = 'https://api.openweathermap.org/data/2.5/weather'
_OM_GEO = 'https://geocoding-api.open-meteo.com/v1/search'
_OM_FORECAST = 'https://api.open-meteo.com/v1/forecast'
_CACHE_TTL = 30 * 60  # 30 Minuten
_CACHE_KEY = 'ls_weather_%s_%s_%s'

# Kurztexte fuer die wichtigsten WMO-Wettercodes (Open-Meteo).
_WMO = {
    0: 'klar', 1: 'ueberw. klar', 2: 'wolkig', 3: 'bedeckt',
    45: 'Nebel', 48: 'Reifnebel', 51: 'Niesel', 53: 'Niesel', 55: 'Niesel',
    61: 'Regen', 63: 'Regen', 65: 'starker Regen', 71: 'Schnee', 73: 'Schnee',
    75: 'starker Schnee', 80: 'Schauer', 81: 'Schauer', 82: 'heftige Schauer',
    95: 'Gewitter', 96: 'Gewitter', 99: 'Gewitter',
}


def _cache_get(key):
    try:
        from resources.lib.tools import cCache
        return cCache().get(key, _CACHE_TTL)
    except Exception:
        return None


def _cache_set(key, value):
    try:
        from resources.lib.tools import cCache
        cCache().set(key, value)
    except Exception:
        pass


def _get_json(url):
    from resources.lib.handler.requestHandler import cRequestHandler
    raw = cRequestHandler(url).request()
    return json.loads(raw) if raw else {}


def _units():
    return cConfig().getSetting('lsWeatherUnits', 'metric') or 'metric'


def _unit_symbol(units):
    return '°C' if units == 'metric' else ('°F' if units == 'imperial' else 'K')


def _from_openweathermap(city, units, lang):
    api_key = (cConfig().getSetting('lsWeatherApiKey', '') or '').strip()
    if not api_key:
        return ''
    from urllib.parse import urlencode
    query = urlencode({'q': city, 'appid': api_key, 'units': units, 'lang': lang})
    data = _get_json('%s?%s' % (_OWM_API, query))
    if str(data.get('cod')) != '200':
        return ''
    temp = round(data.get('main', {}).get('temp', 0))
    desc = (data.get('weather') or [{}])[0].get('description', '')
    return '%s%s, %s' % (temp, _unit_symbol(units), desc)


def _from_open_meteo(city, units):
    from urllib.parse import urlencode
    geo = _get_json('%s?%s' % (_OM_GEO, urlencode({'name': city, 'count': 1, 'format': 'json'})))
    results = geo.get('results') if isinstance(geo, dict) else None
    if not results:
        return ''
    lat = results[0].get('latitude')
    lon = results[0].get('longitude')
    if lat is None or lon is None:
        return ''
    params = {'latitude': lat, 'longitude': lon, 'current': 'temperature_2m,weather_code'}
    if units == 'imperial':
        params['temperature_unit'] = 'fahrenheit'
    data = _get_json('%s?%s' % (_OM_FORECAST, urlencode(params)))
    current = data.get('current') if isinstance(data, dict) else None
    if not current:
        return ''
    temp = round(current.get('temperature_2m', 0))
    desc = _WMO.get(int(current.get('weather_code', -1)), '')
    return ('%s%s, %s' % (temp, _unit_symbol(units), desc)).strip().rstrip(',')


def current_conditions_line(city=None):
    """Wetterzeile fuer eine Stadt (oder die erste konfigurierte), sonst ''."""
    if city is None:
        cities = configured_cities()
        city = cities[0] if cities else ''
    if not city:
        return ''
    units = _units()
    lang = (cConfig().getSetting('prefLanguage', '') or 'de')[:2] or 'de'
    cache_key = _CACHE_KEY % (city.lower(), units, lang)
    cached = _cache_get(cache_key)
    if cached:
        return cached
    try:
        # Open-Meteo zuerst (keyless), dann OWM als optionale Ergaenzung.
        body = _from_open_meteo(city, units) or _from_openweathermap(city, units, lang)
        if not body:
            return ''
        line = '%s: %s  (Stand: %s)' % (city, body, time.strftime('%H:%M'))
        _cache_set(cache_key, line)
        return line
    except Exception as exc:
        logger.error('-> [weather]: Abruf fehlgeschlagen (%s): %s' % (city, exc))
        return ''


def configured_cities():
    """Vom Nutzer hinterlegte Staedte (kommagetrennt)."""
    raw = cConfig().getSetting('lsWeatherCity', '') or ''
    return [c.strip() for c in raw.split(',') if c.strip()]


def city_lines():
    """Wetterzeilen fuer alle konfigurierten Staedte (leere werden verworfen)."""
    lines = []
    for city in configured_cities():
        line = current_conditions_line(city)
        if line:
            lines.append(line)
    return lines
