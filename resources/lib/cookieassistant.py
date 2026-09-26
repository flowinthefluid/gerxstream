# -*- coding: utf-8 -*-
"""Cookie-Assistent fuer Quellen hinter Cloudflare oder DDoS-Guard.

Kodi hat keinen eingebauten Browser und kann die Cookies eines anderen
Browsers nicht auslesen. Der Assistent macht deshalb den einzigen Schritt, der
von Hand bleibt, so kurz wie moeglich:

1. Seite im Browser oeffnen und die Pruefung bestaetigen,
2. die Anfrage "als cURL kopieren",
3. einfuegen - direkt in Kodi oder ueber eine kleine Seite, die GerXStream
   fuer ein paar Minuten im Heimnetz anbietet (bequem vom PC oder Handy aus).

Cookie **und** User-Agent werden daraus automatisch gelesen und in die
Einstellungen der Quelle geschrieben. Vollautomatisch (inklusive Erneuerung
nach Ablauf) geht es nur mit FlareSolverr.
"""

import html
import os
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

import xbmc
import xbmcgui

from resources.lib.config import cConfig
from resources.lib.handler import protection
from resources.lib.tools import logger


RECEIVER_PORTS = (8765, 0)
RECEIVER_TIMEOUT = 10 * 60
MAX_UPLOAD = 512 * 1024


def _t(stringId):
    return cConfig().getLocalizedString(stringId)


# --------------------------------------------------------------------------
# Quellen
# --------------------------------------------------------------------------

def protectedSources():
    """(id, Name) aller Quellen mit Cookie-Einstellung, A-Z nach Name."""
    path = os.path.join(cConfig().getAddonInfo('path'), 'resources', 'settings.xml')
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            ids = re.findall(r'id="plugin_([a-z0-9_\-]+)_bypassCookie"', handle.read())
    except (IOError, OSError):
        ids = []
    names = {}
    try:
        from resources.lib.handler.pluginHandler import cPluginHandler
        for plugin in cPluginHandler().getAvailablePlugins():
            names[plugin.get('id')] = plugin.get('name') or plugin.get('id')
    except Exception:
        pass
    sources = [(siteId, names.get(siteId, siteId)) for siteId in ids if siteId != 'testplugin']
    # Aktive Quellen zuerst, danach der Rest.
    return sorted(sources, key=lambda item: (item[0] not in names, item[1].casefold()))


def domain(siteId):
    for key in ('plugin_%s.domainCustom', 'plugin_%s.domain'):
        value = (cConfig().getSetting(key % siteId) or '').strip()
        if value:
            break
    else:
        value = ''
        try:
            from resources.lib.handler.pluginHandler import cPluginHandler
            for plugin in cPluginHandler().getAvailablePlugins():
                if plugin.get('id') == siteId:
                    value = str(plugin.get('domain') or '')
        except Exception:
            pass
    value = re.sub(r'^https?://', '', value.strip()).strip('/')
    return value if re.fullmatch(r'[A-Za-z0-9.\-]+(:\d+)?', value or '') else ''


def statusLabel(siteId):
    cookie, _ = protection.getManualSession(siteId)
    if cookie:
        return _t(31481)
    if protection.loadSession(siteId)[0]:
        return _t(31482)
    return ''


# --------------------------------------------------------------------------
# Speichern und pruefen
# --------------------------------------------------------------------------

def store(siteId, cookieHeader, userAgent):
    cConfig().setSetting('plugin_%s_bypassCookie' % siteId, cookieHeader or '')
    if userAgent:
        cConfig().setSetting('plugin_%s_bypassUserAgent' % siteId, userAgent)
    # Eine alte automatische Sitzung wuerde sonst weiter mitgeschickt.
    protection.dropSession(siteId)


def test(siteId):
    """Ruft die Startseite mit der hinterlegten Sitzung ab.

    Liefert 'ok', 'blocked' oder 'error'.
    """
    host = domain(siteId)
    if not host:
        return 'error'
    from resources.lib.handler.requestHandler import cRequestHandler
    cookie, userAgent = protection.getManualSession(siteId)
    handler = cRequestHandler('https://%s/' % host, caching=False, ignoreErrors=True)
    if userAgent:
        handler.addHeaderEntry('User-Agent', userAgent)
    if cookie:
        handler.addHeaderEntry('Cookie', cookie)
    try:
        body = handler.request()
    except Exception as e:
        logger.info('-> [cookieassistant]: Test fehlgeschlagen (%s)' % type(e).__name__)
        return 'error'
    status = str(handler.getStatus() or '')
    if status in ('403', '429', '503'):
        return 'blocked'
    if status == '200' and body and not protection.detect(body, handler.getResponseHeader(), 200):
        return 'ok'
    return 'blocked' if body and protection.detect(body) else 'error'


def _accept(siteId, text):
    """Wertet eingefuegten Text aus. Liefert eine Meldung fuer den Nutzer."""
    cookie, userAgent = protection.parseBrowserExport(text)
    if not cookie:
        return False, _t(31483)
    if not userAgent:
        userAgent = cConfig().getSetting('plugin_%s_bypassUserAgent' % siteId) or ''
    store(siteId, cookie, userAgent)
    hints = []
    if protection.missingProtectionCookies(cookie):
        hints.append(_t(31484))
    if not userAgent:
        hints.append(_t(31485))
    return True, ' '.join([_t(31486)] + hints)


# --------------------------------------------------------------------------
# Einfuegen ueber eine Seite im Heimnetz
# --------------------------------------------------------------------------

_PAGE = '''<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GerXStream Cookie-Assistent</title>
<style>body{font-family:system-ui,sans-serif;max-width:720px;margin:24px auto;padding:0 16px;
background:#111;color:#eee}textarea{width:100%%;height:220px;box-sizing:border-box;font:13px monospace}
button{font-size:17px;padding:10px 22px;margin-top:12px}.msg{padding:10px;border-radius:6px;background:#234}
ol li{margin:6px 0}code{background:#333;padding:1px 4px}</style></head><body>
<h2>Cookie-Assistent: %(source)s</h2>%(message)s
<ol><li>Seite <code>https://%(domain)s</code> im Browser oeffnen und die Pruefung bestaetigen.</li>
<li>F12 &rarr; Reiter <b>Netzwerk</b> &rarr; Seite neu laden &rarr; oberste Zeile rechts anklicken
&rarr; <b>Kopieren &rarr; Als cURL kopieren</b> (Chrome/Edge: &bdquo;Als cURL (bash)&ldquo;).</li>
<li>Hier einfuegen und absenden.</li></ol>
<form method="post"><textarea name="data" placeholder="curl 'https://...' -H 'user-agent: ...' -H 'cookie: ...'"></textarea>
<button type="submit">An Kodi senden</button></form></body></html>'''


class _Receiver(object):
    """Einmalige, per Zufallspfad geschuetzte Eingabeseite im Heimnetz."""

    def __init__(self, siteId, sourceName):
        self.siteId = siteId
        self.sourceName = sourceName
        self.token = secrets.token_urlsafe(6)
        self.message = ''
        self.done = False
        self.server = None
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def _page(self, message=''):
                body = _PAGE % {'source': html.escape(receiver.sourceName),
                                'domain': html.escape(domain(receiver.siteId) or receiver.siteId),
                                'message': message}
                data = body.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(data)

            def _authorized(self):
                if self.path.split('?')[0].rstrip('/') != '/' + receiver.token:
                    self.send_error(404)
                    return False
                return True

            def do_GET(self):
                if self._authorized():
                    self._page()

            def do_POST(self):
                if not self._authorized():
                    return
                try:
                    length = int(self.headers.get('Content-Length') or 0)
                except ValueError:
                    length = 0
                if length <= 0 or length > MAX_UPLOAD:
                    self.send_error(413)
                    return
                raw = self.rfile.read(length).decode('utf-8', 'replace')
                text = (parse_qs(raw).get('data') or [''])[0]
                ok, message = _accept(receiver.siteId, text)
                receiver.message = message
                receiver.done = receiver.done or ok
                self._page('<p class="msg">%s</p>' % html.escape(message))

        for port in RECEIVER_PORTS:
            try:
                self.server = HTTPServer(('0.0.0.0', port), Handler)
                break
            except OSError:
                continue
        if self.server is None:
            raise OSError('no free port')
        self.server.timeout = 0.5
        threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.5},
                         daemon=True).start()

    def url(self):
        address = xbmc.getInfoLabel('Network.IPAddress') or ''
        return 'http://%s:%d/%s' % (address, self.server.server_address[1], self.token)

    def close(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass


def receiveFromBrowser(siteId, sourceName):
    address = xbmc.getInfoLabel('Network.IPAddress') or ''
    if not address or address.startswith('127.'):
        xbmcgui.Dialog().ok('GerXStream', _t(31487))
        return False
    try:
        receiver = _Receiver(siteId, sourceName)
    except OSError:
        xbmcgui.Dialog().ok('GerXStream', _t(31487))
        return False
    progress = xbmcgui.DialogProgress()
    progress.create(_t(31470), _t(31488) % receiver.url())
    started = time.time()
    monitor = xbmc.Monitor()
    try:
        while not receiver.done:
            elapsed = time.time() - started
            if progress.iscanceled() or monitor.abortRequested() or elapsed > RECEIVER_TIMEOUT:
                return False
            percent = int(100 - elapsed * 100 / RECEIVER_TIMEOUT)
            text = _t(31488) % receiver.url()
            if receiver.message:
                text += '\n' + receiver.message
            progress.update(percent, text)
            monitor.waitForAbort(0.5)
        return True
    finally:
        progress.close()
        receiver.close()


# --------------------------------------------------------------------------
# Dialogfuehrung
# --------------------------------------------------------------------------

def _instructions(siteId, sourceName):
    host = domain(siteId) or siteId
    names = ', '.join(sorted(set(name for group in protection.RELEVANT_COOKIES.values() for name in group)))
    return _t(31489) % {'source': sourceName, 'domain': host, 'cookies': names}


def _showResult(result):
    labels = {'ok': 31490, 'blocked': 31491, 'error': 31492}
    xbmcgui.Dialog().ok('GerXStream', _t(labels.get(result, 31492)))


def _chooseSource():
    sources = protectedSources()
    if not sources:
        return None, None
    labels = []
    for siteId, name in sources:
        status = statusLabel(siteId)
        labels.append('%s  [I]%s[/I]' % (name, status) if status else name)
    index = xbmcgui.Dialog().select(_t(31471), labels)
    if index < 0:
        return None, None
    return sources[index]


def run(siteId=None):
    sources = dict(protectedSources())
    if siteId and siteId in sources:
        sourceName = sources[siteId]
    else:
        siteId, sourceName = _chooseSource()
        if not siteId:
            return
    dialog = xbmcgui.Dialog()
    while True:
        status = statusLabel(siteId)
        title = '%s: %s' % (_t(31470), sourceName) + (' [I](%s)[/I]' % status if status else '')
        actions = [_t(31472), _t(31473), _t(31474), _t(31475), _t(31476)]
        choice = dialog.select(title, actions)
        if choice < 0:
            return
        if choice == 0:
            dialog.textviewer(_t(31470), _instructions(siteId, sourceName))
        elif choice in (1, 2):
            if choice == 1:
                received = receiveFromBrowser(siteId, sourceName)
            else:
                text = dialog.input(_t(31477))
                received = False
                if text:
                    received, message = _accept(siteId, text)
                    dialog.ok('GerXStream', message)
            if received and dialog.yesno('GerXStream', _t(31478)):
                _showResult(test(siteId))
        elif choice == 3:
            _showResult(test(siteId))
        elif choice == 4:
            store(siteId, '', '')
            cConfig().setSetting('plugin_%s_bypassUserAgent' % siteId, '')
            dialog.notification('GerXStream', _t(31479), xbmcgui.NOTIFICATION_INFO, 3000)
