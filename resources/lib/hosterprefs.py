# -*- coding: utf-8 -*-
"""Bevorzugte Hoster je Quelle und der gemerkte Hoster einer Folgen-Queue.

Zwei Dinge teilen sich hier dieselbe Abgleich-Logik:

* **Bevorzugte Hoster** sind eine dauerhafte Einstellung. Sie gelten entweder
  fuer alle Quellen oder fuer genau eine Quelle, weil jede Seite andere Hoster
  anbietet. Eine eigene Liste einer Quelle ersetzt die allgemeine Liste.
* **Der gemerkte Hoster** gilt nur fuer eine laufende Episoden-Wiedergabeliste.
  Wer bei der ersten Folge "VOE Deutsch" waehlt, bekommt bei den naechsten
  Folgen derselben Liste wieder "VOE Deutsch", ohne gefragt zu werden. Er lebt
  als Fenster-Eigenschaft und verschwindet mit Kodi-Stop bzw. einer neuen
  manuellen Auswahl.

Gespeichert werden nur Hosternamen, nie Links oder Stream-URLs.
"""

import json
import os
import re
import time
from urllib.parse import urlparse

from resources.lib.config import cConfig


MODE_SETTING = 'preferredHosterMode'
DATA_SETTING = 'preferredHosters'
STICKY_SETTING = 'autoNextEpisodeHoster'
ALL_SOURCES = '*'

MODE_OFF = 'off'
MODE_SORT = 'sort'
MODE_ONLY = 'only'
MODE_AUTO = 'auto'
MODES = (MODE_OFF, MODE_SORT, MODE_ONLY, MODE_AUTO)

STICKY_PROPERTY = 'GerXStream.StickyHoster'

SEEN_FILE = 'seen_hosters.json'
SEEN_PER_SITE = 60
MAX_PREFERRED = 20


def normalize(value):
    """Vergleichsform eines Hosternamens: nur Kleinbuchstaben und Ziffern."""
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower())


def _cleanName(value):
    # Kodi-Formatierungen wie [I]..[/I] gehoeren nicht zum Hosternamen.
    value = re.sub(r'\[/?[A-Za-z]+[^\]]*\]', '', str(value or ''))
    return re.sub(r'\s+', ' ', value).strip()[:60]


def _hosterLink(hoster):
    link = hoster.get('link', '') if isinstance(hoster, dict) else ''
    if isinstance(link, (list, tuple)):
        link = link[0] if link else ''
    return link if isinstance(link, str) else ''


def _tokens(hoster):
    """Vergleichbare Namen eines Hoster-Eintrags der Seitenplugins."""
    if not isinstance(hoster, dict):
        return []
    tokens = []
    name = normalize(_cleanName(hoster.get('name')))
    if name:
        tokens.append(name)
    try:
        host = (urlparse(_hosterLink(hoster)).hostname or '').lower()
    except ValueError:
        host = ''
    if host.startswith('www.'):
        host = host[4:]
    label = normalize(host.split('.')[0]) if host else ''
    if len(label) >= 3 and label not in tokens:
        tokens.append(label)
    return tokens


def matches(preferred, hoster):
    """Ob ein bevorzugter Name auf einen Hoster-Eintrag passt.

    "voe" passt auf "VOE", "voe.sx" und "VOE (HD)"; "doodstream" auch auf
    den kuerzeren Seitennamen "Dood". Kurze Namen duerfen nur exakt oder als
    Anfang passen, damit "vid" nicht jeden Hoster mit "vid..." trifft.
    """
    wanted = normalize(preferred)
    if not wanted:
        return False
    for token in _tokens(hoster):
        if token == wanted:
            return True
        if len(wanted) >= 3 and token.startswith(wanted):
            return True
        if len(token) >= 4 and wanted.startswith(token):
            return True
    return False


def rank(hoster, preferred):
    """Position des ersten passenden bevorzugten Namens oder None."""
    for index, name in enumerate(preferred or ()):
        if matches(name, hoster):
            return index
    return None


def reorder(hosters, preferred):
    """Bevorzugte Hoster nach vorn, sonst die Reihenfolge der Quelle behalten."""
    if not preferred:
        return list(hosters)
    decorated = []
    for position, hoster in enumerate(hosters):
        found = rank(hoster, preferred)
        decorated.append((found if found is not None else len(preferred), position, hoster))
    decorated.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in decorated]


def onlyPreferred(hosters, preferred):
    """Nur passende Hoster; leere Liste, wenn keiner passt."""
    return [hoster for hoster in reorder(hosters, preferred) if rank(hoster, preferred) is not None]


# --------------------------------------------------------------------------
# Einstellungen
# --------------------------------------------------------------------------

def mode():
    value = cConfig().getSetting(MODE_SETTING, MODE_OFF) or MODE_OFF
    return value if value in MODES else MODE_OFF


def load():
    """Alle Listen als {quelle: [namen]}; kaputte Einstellung ergibt {}."""
    raw = cConfig().getSetting(DATA_SETTING, '') or ''
    try:
        data = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    cleaned = {}
    for site, names in data.items():
        if not isinstance(site, str) or not isinstance(names, list):
            continue
        names = [_cleanName(name) for name in names if isinstance(name, str) and _cleanName(name)]
        if names:
            cleaned[site] = names[:MAX_PREFERRED]
    return cleaned


def save(data):
    cleaned = {}
    for site, names in (data or {}).items():
        names = [_cleanName(name) for name in names or () if _cleanName(name)]
        if site and names:
            cleaned[site] = names[:MAX_PREFERRED]
    cConfig().setSetting(DATA_SETTING, json.dumps(cleaned, ensure_ascii=False, separators=(',', ':')))
    return cleaned


def setForSite(site, names):
    data = load()
    if names:
        data[site or ALL_SOURCES] = list(names)
    else:
        data.pop(site or ALL_SOURCES, None)
    return save(data)


def forSite(site, data=None):
    """Liste einer Quelle, sonst die Liste fuer alle Quellen."""
    data = load() if data is None else data
    return list(data.get(site) or data.get(ALL_SOURCES) or [])


# --------------------------------------------------------------------------
# Von den Quellen tatsaechlich angebotene Hoster (fuer die Auswahlliste)
# --------------------------------------------------------------------------

def _seenPath():
    from xbmcvfs import translatePath
    profile = translatePath(cConfig().getAddonInfo('profile'))
    if not os.path.isdir(profile):
        os.makedirs(profile)
    return os.path.join(profile, SEEN_FILE)


def _loadSeen():
    try:
        with open(_seenPath(), 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def rememberSeen(site, hosters):
    """Merkt sich die Hosternamen, die eine Quelle gerade angeboten hat.

    So zeigt die Auswahl "Bevorzugte Hoster" je Quelle genau die Namen, die
    diese Quelle wirklich verwendet, statt hunderter ResolveURL-Domains.
    """
    if not site or not re.fullmatch(r'[A-Za-z0-9_\-]+', str(site)):
        return False
    names = []
    for hoster in hosters or ():
        name = _cleanName(hoster.get('name')) if isinstance(hoster, dict) else ''
        if name and normalize(name) and name not in names:
            names.append(name)
    if not names:
        return False
    data = _loadSeen()
    known = data.get(site) if isinstance(data.get(site), dict) else {}
    now = int(time.time())
    for name in names:
        known[name] = now
    newest = sorted(known.items(), key=lambda item: item[1], reverse=True)[:SEEN_PER_SITE]
    data[site] = dict(newest)
    path = _seenPath()
    temporary = path + '.new'
    try:
        with open(temporary, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(',', ':'))
        os.replace(temporary, path)
        return True
    except (IOError, OSError, TypeError, ValueError):
        return False


def seenNames(site=None):
    """Bekannte Hosternamen einer Quelle (oder aller Quellen), A-Z."""
    data = _loadSeen()
    sites = [site] if site and site != ALL_SOURCES else list(data.keys())
    names = {}
    for key in sites:
        entries = data.get(key)
        if not isinstance(entries, dict):
            continue
        for name in entries:
            names.setdefault(normalize(name), name)
    return sorted(names.values(), key=lambda value: value.casefold())


# --------------------------------------------------------------------------
# Gemerkter Hoster einer laufenden Episoden-Wiedergabeliste
# --------------------------------------------------------------------------

def stickyEnabled():
    return (cConfig().getSettingBool('autoNextEpisodeEnabled', False)
            and cConfig().getSetting(STICKY_SETTING, 'ask') == 'sticky')


def _window():
    import xbmcgui
    return xbmcgui.Window(10000)


def rememberSticky(queueId, site, hoster):
    """Haelt den Hoster fest, den der Nutzer fuer diese Folgenliste gewaehlt hat."""
    if not queueId or not isinstance(hoster, dict):
        return False
    name = _cleanName(hoster.get('name'))
    if not normalize(name):
        return False
    value = {'queue': str(queueId), 'site': str(site or ''), 'name': name,
             'lang': str(hoster.get('languageCode', '') or '')}
    _window().setProperty(STICKY_PROPERTY, json.dumps(value, separators=(',', ':')))
    return True


def sticky(queueId, site):
    """Gemerkter Hoster fuer genau diese Queue und Quelle, sonst None."""
    raw = _window().getProperty(STICKY_PROPERTY)
    if not raw or not queueId:
        return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        forgetSticky()
        return None
    if not isinstance(value, dict) or value.get('queue') != str(queueId):
        return None
    if value.get('site') and site and value.get('site') != str(site):
        return None
    return value


def forgetSticky():
    try:
        _window().clearProperty(STICKY_PROPERTY)
    except Exception:
        pass


def stickyCandidates(hosters, remembered):
    """Hoster mit gleichem Namen; gleiche Sprache zuerst."""
    if not remembered:
        return []
    name = remembered.get('name', '')
    language = str(remembered.get('lang', '') or '')
    sameName = [hoster for hoster in hosters if matches(name, hoster)
                and normalize(_cleanName(hoster.get('name'))) == normalize(name)]
    if not sameName:
        sameName = [hoster for hoster in hosters if matches(name, hoster)]
    if not language:
        return sameName
    sameLanguage = [hoster for hoster in sameName if str(hoster.get('languageCode', '') or '') == language]
    # Eine andere Sprache ist kein gleichwertiger Ersatz: dann lieber fragen.
    return sameLanguage if any('languageCode' in hoster for hoster in sameName) else sameName
