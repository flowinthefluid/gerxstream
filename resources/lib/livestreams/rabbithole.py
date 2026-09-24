# -*- coding: utf-8 -*-
# Python 3
"""Rabbithole-Session: zufaellige, nicht-wiederholende Webcam-Folge.

Die Engine ist reine Logik und wird mit zwei injizierten Abhaengigkeiten
getestet: ``pool_provider()`` liefert die Menge zulaessiger Kanal-IDs (bereits
durch Gate + Rechte + Kategorie-Auswahl gefiltert), ``store`` haelt den
Session-Zustand. In Kodi liegt der Zustand in einer Fenster-Property
(``Window(10000)``): er ueberlebt Plugin-Aufrufe innerhalb einer Kodi-Sitzung
und verschwindet beim Neustart - genau die gewuenschte Session-Semantik, ohne
Datei und damit ohne Speicherleck.

Aendert sich die Filterlage (Sichtbarkeit/NSFW/Kategorien) oder der Pool, wird
die Session automatisch verworfen (Signaturvergleich).
"""

import hashlib
import json
import random

_SEEN_KEY = 'gxs.rabbithole.seen'
_SIG_KEY = 'gxs.rabbithole.sig'


class DictStore(dict):
    """Einfacher Store fuer Tests."""
    def get_value(self, key):
        return self.get(key, '')

    def set_value(self, key, value):
        self[key] = value


class WindowStore(object):
    """Fenster-Property-Store (RAM, pro Kodi-Sitzung, kein Datei-Leck)."""
    def __init__(self):
        import xbmcgui
        self._win = xbmcgui.Window(10000)

    def get_value(self, key):
        try:
            return self._win.getProperty(key) or ''
        except Exception:
            return ''

    def set_value(self, key, value):
        try:
            self._win.setProperty(key, value)
        except Exception:
            pass


class RabbitholeSession(object):
    def __init__(self, pool_provider, store, extra_sig=''):
        self._pool_provider = pool_provider
        self._store = store
        self._extra_sig = extra_sig

    # --- intern ---------------------------------------------------------
    def _pool(self):
        return list(self._pool_provider() or [])

    def _signature(self, pool):
        raw = '%s|%s' % (self._extra_sig, ','.join(sorted(pool)))
        return hashlib.md5(raw.encode('utf-8')).hexdigest()[:12]

    def _seen(self):
        try:
            data = json.loads(self._store.get_value(_SEEN_KEY) or '[]')
            return data if isinstance(data, list) else []
        except (TypeError, ValueError):
            return []

    def _write_seen(self, seen):
        self._store.set_value(_SEEN_KEY, json.dumps(seen, separators=(',', ':')))

    def _ensure_session(self, pool):
        sig = self._signature(pool)
        if self._store.get_value(_SIG_KEY) != sig:
            # Filter-/Poolwechsel -> Session neu beginnen.
            self._store.set_value(_SIG_KEY, sig)
            self._write_seen([])
            return []
        return self._seen()

    # --- oeffentlich ----------------------------------------------------
    def next(self):
        """Naechste, in dieser Session noch nicht gezeigte, zufaellige ID.

        Gibt None zurueck, wenn der Pool erschoepft ist (dann kann der Aufrufer
        eine Meldung zeigen und danach reshuffle anbieten).
        """
        pool = self._pool()
        if not pool:
            return None
        seen = self._ensure_session(pool)
        remaining = [cid for cid in pool if cid not in seen]
        if not remaining:
            return None
        choice = random.choice(remaining)
        seen.append(choice)
        self._write_seen(seen)
        return choice

    def reshuffle(self):
        """Alles wieder verfuegbar machen (neue Runde), Signatur behalten."""
        self._write_seen([])

    def reset(self):
        self._store.set_value(_SIG_KEY, '')
        self._write_seen([])

    def remaining(self):
        pool = self._pool()
        seen = self._ensure_session(pool)
        return len([cid for cid in pool if cid not in seen])

    def exhausted(self):
        return self.remaining() == 0


# --- Produktions-Verdrahtung ----------------------------------------------

def visible_pool_ids(sections=('webcam', 'weather')):
    """Zulaessige IDs fuer das Rabbithole: sichtbar + freigegeben + erlaubte
    Kategorie. NSFW/Sichtbarkeit stecken bereits in visible_channels().
    """
    from resources.lib.config import cConfig
    from resources.lib.livestreams import catalog

    allowed = [c.strip().lower() for c in
               (cConfig().getSetting('rhCategories', '') or '').split(',') if c.strip()]
    ids = []
    for channel in catalog.visible_channels():
        if channel['section'] not in sections:
            continue
        if allowed:
            genres = [g.lower() for g in (channel.get('genre') or [])]
            if not any(g in allowed for g in genres):
                continue
        ids.append(channel['id'])
    return ids


def default_session():
    from resources.lib import contentgate
    from resources.lib.config import cConfig
    extra = '%s|%s' % (contentgate.visibility_fingerprint(),
                       cConfig().getSetting('rhCategories', ''))
    return RabbitholeSession(visible_pool_ids, WindowStore(), extra_sig=extra)
