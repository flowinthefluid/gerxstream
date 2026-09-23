# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
#
# Proxer.me verlangt fuer praktisch alle Inhalte ein Konto - Detailseiten
# antworten ohne Anmeldung mit 302 auf die Startseite. Zugangsdaten werden
# deshalb wie bei aniworld.py und serienstream.py pro Nutzer in den
# Einstellungen hinterlegt (proxer.user / proxer.pass); es sind die eigenen
# Zugangsdaten des Nutzers, das Addon bringt keine mit.
#
# Stand der Ueberpruefung - bewusst offengelegt, weil ohne Konto nicht alles
# pruefbar war:
#   geprueft   Anmeldeformular: POST auf /login?<token>=1 mit den Feldern
#              username, password, secretkey (fuer Zwei-Faktor, optional)
#              und remember=1. Der Token in der Ziel-URL wechselt je Aufruf,
#              die Seite muss deshalb zuerst geladen und die action-URL
#              ausgelesen werden.
#   geprueft   Oeffentlich sichtbare Aktualisierungsliste auf /anime:
#              <a class="tip" title="<Titel>" href="/info/<id>#top">
#              <img src="//cdn.proxer.me/cover/<id>.jpg">
#   UNGEPRUEFT Aufbau der Detail- und Episodenseiten hinter der Anmeldung.
#              Weder live (302 ohne Konto) noch ueber das Webarchiv (keine
#              Aufnahmen) einsehbar. Die Muster unten sind aus der
#              oeffentlich sichtbaren Struktur abgeleitet und protokollieren
#              ausdruecklich, wenn sie nicht greifen - sie sind nicht
#              bestaetigt und muessen mit einem echten Konto nachgeprueft
#              werden.

import xbmcgui

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'proxer'
SITE_NAME = 'Proxer.Me'
SITE_ICON = 'proxer.png'
CONTENT_CATEGORIES = ('animes',)

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'proxer.me')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_LOGIN = URL_MAIN + '/login'
URL_ANIME = URL_MAIN + '/anime'
URL_SEARCH = URL_MAIN + '/search?s=search&name=%s'

# Oeffentlich sichtbare Kacheln der Aktualisierungsliste.
ITEM_PATTERN = (r'<a class="tip" title="([^"]+)"[^>]*href="(/info/\d+)[^"]*">'
                r'\s*<img[^>]+src="([^"]+)"')


def _credentials():
    return (cConfig().getSetting('proxer.user'), cConfig().getSetting('proxer.pass'))


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    username, password = _credentials()
    if not username or not password:
        # Gleiche Behandlung wie bei aniworld und serienstream: ohne
        # Zugangsdaten hat das Menue keinen Zweck.
        xbmcgui.Dialog().ok(cConfig().getLocalizedString(30241),
                            cConfig().getLocalizedString(30263))
        return
    params = ParameterHandler()
    params.setParam('sUrl', URL_ANIME)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30500), SITE_IDENTIFIER, 'showEntries'), params)  # Neues
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def _login():
    """Meldet sich an. Der Sitzungs-Cookie bleibt im Cookie-Speicher des
    requestHandlers und traegt die folgenden Abrufe.

    Die Ziel-URL des Formulars enthaelt einen wechselnden Token, sie muss
    deshalb erst aus der Anmeldeseite gelesen werden.
    """
    username, password = _credentials()
    if not username or not password:
        return False
    sHtmlContent = cRequestHandler(URL_LOGIN, caching=False).request()
    if not sHtmlContent:
        logger.info('-> [%s]: Anmeldeseite nicht erreichbar' % SITE_NAME)
        return False
    isMatch, sAction = cParser.parseSingleResult(
        sHtmlContent, r'<form method="post" action="(/login\?[^"]+)"')
    if not isMatch:
        logger.info('-> [%s]: Formularziel der Anmeldung nicht gefunden - '
                    'die Seite hat ihr Anmeldeformular geaendert' % SITE_NAME)
        return False

    oRequest = cRequestHandler(URL_MAIN + sAction, caching=False)
    oRequest.addHeaderEntry('Referer', URL_LOGIN)
    oRequest.addHeaderEntry('Upgrade-Insecure-Requests', '1')
    oRequest.addParameters('username', username)
    oRequest.addParameters('password', password)
    oRequest.addParameters('remember', '1')
    sResponse = oRequest.request()
    if not sResponse:
        logger.info('-> [%s]: Anmeldung ohne Antwort' % SITE_NAME)
        return False
    # Steht das Anmeldeformular danach immer noch da, hat es nicht geklappt.
    if 'mod_login_password' in sResponse:
        logger.info('-> [%s]: Anmeldung abgelehnt - Zugangsdaten pruefen'
                    % SITE_NAME)
        return False
    return True


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('sUrl')

    if not _login():
        if not sGui:
            oGui.showInfo(SITE_NAME, cConfig().getLocalizedString(30263))
        return

    sHtmlContent = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False)).request()
    if not sHtmlContent:
        if not sGui:
            oGui.showInfo()
        return

    isMatch, aResult = cParser.parse(sHtmlContent, ITEM_PATTERN)
    if not isMatch:
        logger.info('-> [%s]: keine Eintraege gefunden - Aufbau der Seite '
                    'hinter der Anmeldung ist ungeprueft, Muster ggf. '
                    'veraltet: %s' % (SITE_NAME, entryUrl))
        if not sGui:
            oGui.showInfo()
        return

    seen = set()
    entries = []
    for sTitle, sPath, sImage in aResult:
        if sPath in seen:
            continue
        seen.add(sPath)
        entries.append((sTitle, sPath, sImage))

    total = len(entries)
    for sTitle, sPath, sImage in entries:
        oGuiElement = cGuiElement(sTitle, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('tvshow')
        if sImage:
            oGuiElement.setThumbnail('https:' + sImage if sImage.startswith('//') else sImage)
        params.setParam('entryUrl', URL_MAIN + sPath)
        params.setParam('sName', sTitle)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        oGui.setView('tvshows')
        oGui.setEndOfDirectory()


def showHosters():
    """Streams einer Serie.

    UNGEPRUEFT: der Aufbau dieser Seite war ohne Konto nicht einsehbar. Statt
    ein erratenes, enges Muster zu setzen, wird allgemein nach Einbettungen
    auf fremde Domains gesucht und der Fehlschlag deutlich protokolliert.
    """
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    if not sUrl:
        return hosters
    if not _login():
        return hosters
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    if not sHtmlContent:
        return hosters

    isMatch, aResult = cParser.parse(
        sHtmlContent,
        r'(?:<iframe[^>]+src|data-src|data-url)="(https?://(?!%s)[^"]+)"'
        % cParser.escape(DOMAIN))
    if not isMatch:
        logger.info('-> [%s]: keine Einbettung gefunden. Der Aufbau der '
                    'Seiten hinter der Anmeldung ist nicht verifiziert und '
                    'muss mit einem Konto nachgeprueft werden: %s'
                    % (SITE_NAME, sUrl))
        return hosters

    seen = set()
    for sLink in aResult:
        if sLink in seen:
            continue
        seen.add(sLink)
        sName = cParser.urlparse(sLink)
        hosters.append({'link': sLink, 'name': sName, 'displayedName': sName})
    if hosters:
        hosters.append('getHosterUrl')
    return hosters


def getHosterUrl(sUrl=False):
    return [{'streamUrl': sUrl, 'resolved': False}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)
