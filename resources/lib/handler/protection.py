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

import re

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


def notifyOnce(siteId, kind, url=''):
    """Erklaert einmal je Quelle, wie sich die Sperre aufloesen laesst.

    Ohne diesen Hinweis sieht der Nutzer nur eine leere Liste und hat keinen
    Anhaltspunkt, woran es liegt.
    """
    label = {CLOUDFLARE: 'Cloudflare', DDOS_GUARD: 'DDoS-Guard'}.get(kind, kind)
    logger.info('-> [protection]: %s aktiv fuer %s (%s)' % (label, siteId, url))
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
            'und die Pruefung dort bestaetigen. Danach in den '
            'Entwickler-Werkzeugen des Browsers das Cookie (%s) sowie den '
            'User-Agent auslesen und beide in den Einstellungen dieser '
            'Quelle eintragen.\n\n'
            'Beide Angaben gehoeren zusammen - das Cookie gilt nur fuer den '
            'User-Agent, mit dem es ausgestellt wurde.' % (label, names))
    try:
        import xbmcgui
        xbmcgui.Dialog().ok('GerXStream', message)
    except Exception as exc:
        logger.info('-> [protection]: Hinweisdialog nicht moeglich: %s' % exc)
