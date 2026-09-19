# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showGenre:    24 Stunden
# showEntries:   3 Stunden
#
# WordPress-Seite (Jannah-Theme). Kein eigener Hoster: die Beitraege
# verlinken direkt auf Google-Drive-Ordner mit den Episodendateien, benannt
# nach Staffel ("Season 1", "Season 2", ...).
#
# Aufbau (an Live-Daten geprueft):
#   Uebersicht  aria-label="<Titel>" href="<Beitrag>" class="post-thumb">
#               ...<img ... (data-src|src)="<Bild>.jpg"
#               Zwei Layouts liefern das leicht unterschiedlich (Raster
#               lazy-laedt ueber data-src, Suche direkt ueber src) - das
#               Muster deckt beides ab.
#   Detailseite <h3 class="toggle-head"><Staffelname></h3>
#               <div class="toggle-content"><a href="drive.google.com/..."
#               class="...">Season N</a></div>

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'kayoanime'
SITE_NAME = 'KayoAnime'
SITE_ICON = 'kayoanime.png'

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'kayoanime.com')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_SEARCH = URL_MAIN + '/?s=%s'

# Kategorien der Seite, Pfad -> Menuename.
SECTIONS = (
    ('category/anime-series', 'Anime Series'),
    ('category/anime-movie', 'Anime Movies'),
    ('category/chinese-anime', 'Chinese Anime'),
    ('category/ongoing-anime', 'Ongoing'),
    ('category/action', 'Action'),
    ('category/adventure', 'Adventure'),
    ('category/comedy', 'Comedy'),
    ('category/drama', 'Drama'),
    ('category/fantasy', 'Fantasy'),
    ('category/romance', 'Romance'),
    ('category/school', 'School'),
    ('category/mecha', 'Mecha'),
    ('category/mystery', 'Mystery'),
    ('category/psychological', 'Psychological'),
    ('category/martial-arts', 'Martial Arts'),
)

# Deckt beide beobachteten Kachel-Layouts ab: das Raster laedt Bilder ueber
# data-src nach, die Suchergebnisse liefern src direkt.
ITEM_PATTERN = (r'aria-label="([^"]+)" href="(https://%s/[a-z0-9-]+/)" '
                r'class="post-thumb">.*?<img[^>]*?(?:data-src|src)='
                r'"(https://[^"]+\.(?:jpg|jpeg|png|webp))"')

# Staffelbloecke auf der Detailseite: Ueberschrift plus die Google-Drive-
# Verweise darunter.
BLOCK_PATTERN = r'<h3 class="toggle-head">([^<]*)<span[^>]*></span></h3><div class="toggle-content">(.*?)</div>'
LINK_PATTERN = r'href="(https://drive\.google\.com/[^"]+)"[^>]*>([^<]+)</a>'


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    for path, title in SECTIONS:
        params.setParam('sUrl', '%s/%s/' % (URL_MAIN, path))
        cGui().addFolder(cGuiElement(title, SITE_IDENTIFIER, 'showEntries'), params)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('sUrl')

    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    if cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, False):
        oRequest.cacheTime = 60 * 60 * 3  # 3 Stunden
    sHtmlContent = oRequest.request()
    if not sHtmlContent:
        if not sGui:
            oGui.showInfo()
        return

    isMatch, aResult = cParser.parse(sHtmlContent, ITEM_PATTERN % cParser.escape(DOMAIN))
    if not isMatch:
        if not sGui:
            oGui.showInfo()
        return

    total = len(aResult)
    for sTitle, sUrl, sImage in aResult:
        oGuiElement = cGuiElement(sTitle, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('tvshow')
        if sImage:
            oGuiElement.setThumbnail(sImage)
        params.setParam('entryUrl', sUrl)
        params.setParam('sName', sTitle)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        # Vollstaendige Seite (15 Kacheln) -> weitere Seite anhaengen.
        if total >= 15 and '/page/' not in entryUrl:
            params.setParam('sUrl', entryUrl.rstrip('/') + '/page/2/')
            oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        elif total >= 15:
            isMatch, sPage = cParser.parseSingleResult(entryUrl, r'/page/(\d+)/')
            if isMatch:
                nextUrl = entryUrl.replace('/page/%s/' % sPage, '/page/%s/' % (int(sPage) + 1))
                params.setParam('sUrl', nextUrl)
                oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        oGui.setView('tvshows')
        oGui.setEndOfDirectory()


def showHosters():
    """Staffelbloecke der Detailseite; jeder Block verlinkt einen Google-Drive-Ordner."""
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    if not sUrl:
        return hosters
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    if not sHtmlContent:
        return hosters

    isMatch, aBlocks = cParser.parse(sHtmlContent, BLOCK_PATTERN)
    if not isMatch:
        return hosters
    for sBlockTitle, sBlock in aBlocks:
        isLink, aLinks = cParser.parse(sBlock, LINK_PATTERN)
        if not isLink:
            continue
        for sLink, sLabel in aLinks:
            sLabel = sLabel.strip() or sBlockTitle.strip() or 'Google Drive'
            hosters.append({'link': sLink, 'name': 'Google Drive',
                            'displayedName': 'Google Drive [I]%s[/I]' % sLabel})
    if hosters:
        hosters.append('getHosterUrl')
    return hosters


def getHosterUrl(sUrl=False):
    # Google-Drive-Ordner, kein Hoster im klassischen Sinn - ResolveURL kann
    # ihn nicht aufloesen. Kodi kann eine Drive-Ordneradresse nicht direkt
    # abspielen, sie wird deshalb unresolved durchgereicht und im
    # Wiedergabefenster als Verweis angezeigt statt eine leere Wiedergabe
    # vorzutaeuschen.
    return [{'streamUrl': sUrl, 'resolved': False}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)
