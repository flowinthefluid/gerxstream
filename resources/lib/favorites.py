# -*- coding: utf-8 -*-
# Python 3
"""Kleine, persistente Nutzerlisten fuer die Kategorien."""

import re

from resources.lib.config import cConfig


FAVORITE_ACTORS_SETTING = 'favoriteActors'
MAX_FAVORITE_ACTORS = 100


def _normaliseName(value):
    """Bereitet einen manuell eingegebenen Namen fuer die TMDB-Suche vor."""
    if not isinstance(value, str):
        return ''
    return re.sub(r'\s+', ' ', value).strip()[:100]


def favoriteActors():
    """Liest die kommagetrennte Favoritenliste, ohne Dubletten auszugeben."""
    raw = cConfig().getSetting(FAVORITE_ACTORS_SETTING, '')
    result = []
    seen = set()
    for value in re.split(r'[,;\r\n]+', raw or ''):
        name = _normaliseName(value)
        key = name.casefold()
        if name and key not in seen:
            result.append(name)
            seen.add(key)
    return result[:MAX_FAVORITE_ACTORS]


def addFavoriteActor(name):
    """Fuegt einen Namen hinzu und gibt ``True`` nur bei einer echten Aenderung zurueck."""
    name = _normaliseName(name)
    if not name:
        return False
    names = favoriteActors()
    if name.casefold() in {entry.casefold() for entry in names}:
        return False
    if len(names) >= MAX_FAVORITE_ACTORS:
        return False
    names.append(name)
    cConfig().setSetting(FAVORITE_ACTORS_SETTING, ', '.join(names))
    return True
