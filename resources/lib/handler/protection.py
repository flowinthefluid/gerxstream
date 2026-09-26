# -*- coding: utf-8 -*-
# Python 3
"""Umgang mit Bot-Schutzsystemen vor einzelnen Quellen.

Manche Seiten stehen hinter Cloudflare oder DDoS-Guard. Deren Pruefung
verlangt eine Browser-Umgebung mit JavaScript, die Kodi nicht hat - der
Abruf endet deshalb mit 403 und einer Hinweisseite statt mit Inhalt.

Dieses Modul loest die Pruefung **nicht** automatisch. Es nimmt stattdessen
entgegen, was der Nutzer in seinem eigenen Browser bereits bestaetigt hat:
das dort gesetzte Cookie und den passenden User-Agent. Beides wird pro Quelle
in den Einstellungen hinterlegt und anschliessend bei jedem Abruf
mitgeschickt. Es wird nichts umgangen, was der Nutzer nicht ohnehin schon
selbst durchlaufen hat; die Sitzung wird lediglich von Browser zu Addon
uebertragen.

Wichtig: Cookie und User-Agent gehoeren zusammen. Beide Systeme binden das
Cookie an den User-Agent, mit dem es ausgestellt wurde. Wird nur das Cookie
hinterlegt, laeuft die Pruefung sofort wieder an.
"""

import json
import os
import re
import threading
import time
from urllib.parse import urlparse

from resources.lib.config import cConfig
from resources.lib.tools import logger

# Kennungen der unterstuetzten Schutzsysteme.
CLOUDFLARE = 'cloudflare'
DDOS_GUARD = 'ddos-guard'

# Merkmale im Antwortkoerper. DDoS-Guard steht bewusst vorn: dessen
# Sperrseite enthaelt ebenfalls "Checking your browser", wuerde also sonst
# als Cloudflare gemeldet.
#
# Die Muster sind absichtlich eng. Ein blosses "turnstile" oder "cloudflare"
# reicht nicht - viele intakte Seiten binden Cloudflare-Skripte ein oder
# nutzen Turnstile nur im Anmeldeformular. Ein Fehlalarm waere schlimmer als
# eine nicht erkannte Sperre: er legt eine funktionierende Quelle lahm.
_BODY_MARKERS = (
    (DDOS_GUARD, re.compile(r'ddos-guard|check\.ddos-guard\.net', re.I)),
    (CLOUDFLARE, re.compile(
        r'cf-browser-verification|cf_chl_|/cdn-cgi/challenge-platform|'
        r'<title>\s*Just a moment', re.I)),
)
_HEADER_MARKERS = (
    (DDOS_GUARD, re.compile(r'ddos-guard', re.I)),
    (CLOUDFLARE, re.compile(r'cf-mitigated', re.I)),
)

# Statuscodes, mit denen Schutzsysteme antworten.
_BLOCK_STATUS = (403, 429, 503)

# Sperrseiten sind klein. Alles darueber ist echter Inhalt, selbst wenn
# irgendwo im Seitenquelltext ein Schutz-Schlagwort vorkommt.
_MAX_CHALLENGE_SIZE = 120000

# Cookies, die das jeweilige System nach bestandener Pruefung setzt.
RELEVANT_COOKIES = {
    CLOUDFLARE: ('cf_clearance', '__cf_bm'),
    DDOS_GUARD: ('__ddg1_', '__ddg2_', '__ddg8_', '__ddg9_', '__ddg10_', '__ddgid_'),
}

# Ein Hinweis je Quelle und Sitzung reicht.
_notified = set()
_pendingNotifications = []
_notificationLock = threading.Lock()

# Abgelegte Sitzungen: damit die Bestaetigung nicht bei jedem Kodi-Start
# erneut noetig ist. Cloudflare setzt cf_clearance ueblicherweise auf einige
# Stunden bis Tage; 12 Stunden sind ein Kompromiss zwischen "haelt lange" und
# "merkt rechtzeitig, dass es abgelaufen ist".
SESSION_FILE = 'protection_sessions.json'
SESSION_MAX_AGE = 12 * 60 * 60

_sessionCache = None


def _sessionPath():
    profile = cConfig().getAddonInfo('profile')
    try:
        from xbmcvfs import translatePath
        profile = translatePath(profile)
    except Exception:
        pass
    return os.path.join(profile, SESSION_FILE)


def _loadStore():
    global _sessionCache
    if _sessionCache is not None:
        return _sessionCache
    _sessionCache = {}
    path = _sessionPath()
    try:
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                _sessionCache = data
    except Exception as exc:
        logger.info('-> [protection]: Sitzungsspeicher nicht lesbar: %s' % exc)
    return _sessionCache


def _saveStore(store):
    path = _sessionPath()
    try:
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(store, handle)
    except Exception as exc:
        logger.info('-> [protection]: Sitzungsspeicher nicht schreibbar: %s' % exc)


def storeSession(siteId, cookieHeader, userAgent, kind=''):
    """Haelt eine funktionierende Sitzung ueber Neustarts hinweg fest."""
    if not siteId or not cookieHeader:
        return
    store = _loadStore()
    store[siteId] = {'cookie': cookieHeader, 'userAgent': userAgent or '',
                     'kind': kind, 'ts': int(time.time())}
    _saveStore(store)
    logger.info('-> [protection]: Sitzung fuer %s gespeichert' % siteId)


def loadSession(siteId):
    """Gespeicherte Sitzung, sofern noch nicht zu alt."""
    entry = _loadStore().get(siteId)
    if not isinstance(entry, dict):
        return '', ''
    if int(time.time()) - int(entry.get('ts') or 0) > SESSION_MAX_AGE:
        return '', ''
    return entry.get('cookie') or '', entry.get('userAgent') or ''


def dropSession(siteId):
    """Verwirft eine Sitzung, die von der Gegenstelle abgelehnt wurde."""
    store = _loadStore()
    if store.pop(siteId, None) is not None:
        _saveStore(store)
        logger.info('-> [protection]: abgelaufene Sitzung fuer %s verworfen' % siteId)


def _settingName(siteId, suffix):
    return 'plugin_%s_%s' % (siteId, suffix)


def detect(body, headers=None, status=None):
    """Erkennt das Schutzsystem. Liefert dessen Kennung oder None.

    Zwei Bedingungen muessen zusammenkommen, damit etwas als Sperre gilt:
    ein eindeutiges Merkmal **und** eine Antwort, die wie eine Sperrseite
    aussieht - also ein Sperr-Statuscode oder eine auffaellig kleine Seite.
    Ein 403 allein genuegt nicht, ein Schlagwort allein auch nicht.

    Hintergrund: eine Quelle lieferte mit Status 200 rund 200 KB echten
    Inhalt und enthielt trotzdem ein Cloudflare-Schlagwort. Ohne die
    Groessen- und Statuspruefung waere sie faelschlich als gesperrt
    behandelt worden.
    """
    text = body if isinstance(body, str) else ''
    if isinstance(body, bytes):
        text = body.decode('utf-8', 'replace')

    rendered = ''
    if headers is not None:
        try:
            rendered = str(headers)
        except Exception:
            rendered = ''

    looksBlocked = (status in _BLOCK_STATUS) or (0 < len(text) <= _MAX_CHALLENGE_SIZE)
    if not looksBlocked:
        return None

    for kind, pattern in _BODY_MARKERS:
        if pattern.search(text):
            return kind
    for kind, pattern in _HEADER_MARKERS:
        if pattern.search(rendered):
            return kind
    return None


def parseCookieString(value):
    """Zerlegt eine Cookie-Zeile aus dem Browser in Name/Wert-Paare.

    Angenommen wird sowohl die Kurzform "a=1; b=2" als auch ein einzelnes
    Paar. Werte duerfen Gleichheitszeichen enthalten (Base64), deshalb wird
    nur am ersten getrennt.
    """
    cookies = {}
    if not value:
        return cookies
    for part in str(value).replace('\n', ';').split(';'):
        part = part.strip()
        if not part or '=' not in part:
            continue
        name, _, raw = part.partition('=')
        name = name.strip()
        raw = raw.strip().strip('"')
        if name and raw:
            cookies[name] = raw
    return cookies


def _cookieHeader(pairs):
    return '; '.join('%s=%s' % (name, value) for name, value in pairs.items())


def _unescapeWindowsCurl(text):
    # Chrome "Als cURL (cmd) kopieren" maskiert Sonderzeichen mit ^.
    if '^"' in text:
        text = re.sub(r'\^(.)', r'\1', text)
    return text


def parseBrowserExport(text):
    """Cookie und User-Agent aus dem, was ein Browser zum Kopieren anbietet.

    Erkannt werden:
    * "Als cURL kopieren" (Chrome, Edge, Firefox; bash und cmd),
    * kopierte Anfrage-Header ("Cookie: ..." und "User-Agent: ..."),
    * cookies.txt im Netscape-Format und JSON-Exporte von Cookie-Erweiterungen,
    * eine blosse Cookie-Zeile "name=wert; name2=wert2".

    Liefert (cookieHeader, userAgent); beides kann leer sein.
    """
    text = str(text or '').strip()
    if not text:
        return '', ''
    cookies = {}
    userAgent = ''

    # JSON-Export (Cookie-Editor, EditThisCookie): [{"name":..,"value":..}]
    if text[:1] in '[{':
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if isinstance(data, dict):
            data = data.get('cookies') or [data]
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and entry.get('name') and entry.get('value') is not None:
                    cookies[str(entry['name']).strip()] = str(entry['value']).strip()
            if cookies:
                return _cookieHeader(cookies), ''

    if re.match(r'^\s*curl\s', text, re.I):
        text = _unescapeWindowsCurl(text)
        for quote, header in re.findall(r'''(?:-H|--header)\s+(['"])(.*?)\1''', text, re.S):
            name, _, value = header.partition(':')
            name = name.strip().lower()
            if name == 'cookie':
                cookies.update(parseCookieString(value))
            elif name == 'user-agent':
                userAgent = value.strip()
        for quote, value in re.findall(r'''(?:\s-b|--cookie)\s+(['"])(.*?)\1''', text, re.S):
            cookies.update(parseCookieString(value))
        for quote, value in re.findall(r'''(?:\s-A|--user-agent)\s+(['"])(.*?)\1''', text, re.S):
            userAgent = value.strip()
        return _cookieHeader(cookies), userAgent

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    netscape = False
    for line in lines:
        fields = line.split('\t')
        if len(fields) == 7 and not line.startswith('#'):
            # domain, subdomains, path, secure, ablauf, name, wert
            netscape = True
            if fields[5].strip():
                cookies[fields[5].strip()] = fields[6].strip()
            continue
        match = re.match(r'^(cookie|user-agent)\s*:\s*(.*)$', line, re.I)
        if match:
            if match.group(1).lower() == 'cookie':
                cookies.update(parseCookieString(match.group(2)))
            else:
                userAgent = match.group(2).strip()
    if cookies or userAgent or netscape:
        return _cookieHeader(cookies), userAgent

    # Einzelne Zeile: nur Cookies, oder nur ein User-Agent.
    if text.startswith('Mozilla/'):
        return '', text
    return _cookieHeader(parseCookieString(text)), ''


def missingProtectionCookies(cookieHeader):
    """Ob in einer Cookie-Zeile keines der bekannten Schutz-Cookies steckt."""
    names = set(parseCookieString(cookieHeader).keys())
    known = set(name for group in RELEVANT_COOKIES.values() for name in group)
    return not (names & known)


def flaresolverrUrl():
    """Adresse eines FlareSolverr-Dienstes, falls eingerichtet.

    FlareSolverr faehrt einen echten Browser und loest die Pruefung dort.
    Damit erneuert sich die Sitzung von selbst, sobald sie ablaeuft - das
    ist der Unterschied zwischen "einmal eintragen" und "bei jedem Start
    erneut bestaetigen".
    """
    if not cConfig().getSettingBool('flaresolverrEnabled', False):
        return ''
    url = (cConfig().getSetting('flaresolverrUrl') or '').strip()
    if not url:
        return ''
    if not url.startswith('http'):
        url = 'http://' + url
    return url.rstrip('/')


def solveWithFlaresolverr(siteId, targetUrl, timeout=60):
    """Laesst FlareSolverr die Pruefung loesen. Liefert (cookie, userAgent)."""
    endpoint = flaresolverrUrl()
    if not endpoint or not targetUrl:
        return '', ''
    payload = json.dumps({'cmd': 'request.get', 'url': targetUrl,
                          'maxTimeout': timeout * 1000}).encode('utf-8')
    try:
        # Bewusst urllib statt cRequestHandler: dieser Aufruf geht an einen
        # lokalen Dienst und darf nicht selbst wieder durch die
        # Schutzerkennung laufen.
        from urllib.request import Request, urlopen
        request = Request(endpoint + '/v1', data=payload,
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=timeout + 10) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        logger.info('-> [protection]: FlareSolverr nicht erreichbar (%s): %s'
                    % (endpoint, exc))
        return '', ''

    if data.get('status') != 'ok':
        logger.info('-> [protection]: FlareSolverr meldet %s: %s'
                    % (data.get('status'), str(data.get('message'))[:180]))
        return '', ''

    solution = data.get('solution') or {}
    cookies = solution.get('cookies') or []
    header = '; '.join('%s=%s' % (c.get('name'), c.get('value'))
                       for c in cookies
                       if isinstance(c, dict) and c.get('name'))
    userAgent = solution.get('userAgent') or ''
    if header:
        storeSession(siteId, header, userAgent, 'flaresolverr')
        logger.info('-> [protection]: FlareSolverr hat %s geloest (%d Cookies)'
                    % (siteId, len(cookies)))
    return header, userAgent


def getManualSession(siteId):
    """Hinterlegtes Cookie und User-Agent einer Quelle.

    Liefert (cookieHeader, userAgent); beide koennen leer sein.
    """
    if not siteId or not re.fullmatch(r'[a-z0-9_-]+', str(siteId)):
        return '', ''
    raw = cConfig().getSetting(_settingName(siteId, 'bypassCookie'))
    userAgent = cConfig().getSetting(_settingName(siteId, 'bypassUserAgent'))
    cookies = parseCookieString(raw)
    if not cookies:
        return '', userAgent or ''
    header = '; '.join('%s=%s' % (k, v) for k, v in cookies.items())
    return header, userAgent or ''


def hasManualSession(siteId):
    header, _ = getManualSession(siteId)
    return bool(header)


def getSession(siteId):
    """Die zu verwendende Sitzung, in dieser Reihenfolge:

    1. was der Nutzer ausdruecklich eingetragen hat,
    2. eine gespeicherte, noch gueltige Sitzung,
    3. nichts - dann wird erst beim Blockieren geloest.

    Punkt 2 ist der Grund, warum nach dem ersten Mal keine erneute
    Bestaetigung noetig ist.
    """
    if not siteId or not re.fullmatch(r'[a-z0-9_-]+', str(siteId)):
        return '', ''
    header, userAgent = getManualSession(siteId)
    if header:
        return header, userAgent
    return loadSession(siteId)


def recover(siteId, targetUrl):
    """Nach einer erkannten Sperre eine neue Sitzung beschaffen.

    Eine gespeicherte Sitzung, die gerade abgelehnt wurde, ist wertlos und
    wird verworfen - sonst wuerde sie bei jedem Abruf erneut probiert.
    Liefert (cookie, userAgent) oder ('', ''), wenn nichts zu holen ist.
    """
    if not siteId:
        return '', ''
    dropSession(siteId)
    if not flaresolverrUrl():
        return '', ''
    return solveWithFlaresolverr(siteId, targetUrl)


def notifyOnce(siteId, kind, url='', interactive=True):
    """Erklaert einmal je Quelle, wie sich die Sperre aufloesen laesst.

    Ohne diesen Hinweis sieht der Nutzer nur eine leere Liste und hat keinen
    Anhaltspunkt, woran es liegt.
    """
    label = {CLOUDFLARE: 'Cloudflare', DDOS_GUARD: 'DDoS-Guard'}.get(kind, kind)
    logger.info('-> [protection]: %s aktiv fuer %s (%s)' % (label, siteId, url))
    # Die globale Suche ruft Quellen parallel auf. Ein modaler Kodi-Dialog
    # aus einem Worker (oder danach vor dem Rendern) unterbricht den gesamten
    # Suchablauf. Automatische Suchen protokollieren die Sperre daher nur;
    # der Hinweis bleibt bei einem direkten Aufruf der betroffenen Quelle.
    with _notificationLock:
        if siteId in _notified:
            return
        _notified.add(siteId)

    stored = hasManualSession(siteId)
    names = ', '.join(RELEVANT_COOKIES.get(kind, ()))
    if stored:
        message = (
            '%s blockiert diese Quelle weiterhin, obwohl ein Cookie '
            'hinterlegt ist. Wahrscheinlich ist es abgelaufen oder der '
            'User-Agent passt nicht dazu. Bitte beides in den Einstellungen '
            'der Quelle erneuern.' % label)
    else:
        message = (
            '%s schuetzt diese Quelle. Kodi kann die Pruefung nicht selbst '
            'bestaetigen.\n\n'
            'So wird die Quelle nutzbar: die Seite einmal im Browser oeffnen '
            'und die Pruefung dort bestaetigen. Danach hilft der '
            'Cookie-Assistent (Einstellungen > Allgemein > Netzwerk) beim '
            'Uebernehmen - dort genuegt es, die Anfrage im Browser "als cURL" '
            'zu kopieren und einzufuegen, auch bequem vom Handy oder PC aus. '
            'Benoetigt wird das Cookie %s zusammen mit dem User-Agent des '
            'Browsers.' % (label, names))
    source = urlparse(url).netloc or siteId
    if source:
        message += '\n\nBetroffene Quelle: %s' % source
    if not interactive:
        logger.info('-> [protection]: Automatische Suche ueberspringt Hinweisdialog fuer %s' % source)
        return
    _showNotification(message)


def _showNotification(message):
    try:
        import xbmcgui
        xbmcgui.Dialog().ok('GerXStream', message)
    except Exception as exc:
        logger.info('-> [protection]: Hinweisdialog nicht moeglich: %s' % exc)


def showPendingNotifications():
    """Zeigt aus parallelen Such-Workern gesammelte Hinweise sicher an."""
    with _notificationLock:
        pending = list(_pendingNotifications)
        del _pendingNotifications[:]
    for message in pending:
        _showNotification(message)


def discardPendingNotifications():
    """Discard notifications left by older automatic-search code paths."""
    with _notificationLock:
        del _pendingNotifications[:]
