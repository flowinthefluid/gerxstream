# -*- coding: utf-8 -*-
# Python 3
"""Alternative Domains je Quelle, umschaltbar aus dem Menue heraus.

Viele Quellen sind unter mehreren Adressen erreichbar. Wird eine davon
gesperrt (in Deutschland regelmaessig ueber DNS-Sperren der Zugangsanbieter),
funktioniert die Quelle unter einer anderen Adresse weiter. Bisher liess sich
das nur ueber ein Textfeld tief in den Einstellungen aendern - dieses Modul
macht die bekannten Alternativen als Menuepunkt auswaehlbar.

Aufnahmekriterium: nur Adressen, die nachweislich **dieselbe Installation**
bedienen. Geprueft wurde das nicht an der blossen Erreichbarkeit, sondern am
Fingerabdruck der Seite - gleicher Theme-Ordner bzw. gleiche Stylesheet-Namen
bedeuten dieselbe Installation, unterschiedliche bedeuten einen
eigenstaendigen Betreiber, der nur denselben Markennamen benutzt. Diese
Unterscheidung ist wichtig: ein fremder Betreiber unter gleichem Namen hat
andere Filme und andere Hoster-Links, gehoert also in ein eigenes Plugin und
nicht in diese Liste.

Sicherheit: die Umschaltung nimmt ausschliesslich Werte aus dieser Liste an.
Eine Domain, die frei aus der plugin://-URL stammt, wird nie uebernommen -
sonst koennte ein praeparierter Link eine Quelle auf eine fremde Adresse
umbiegen (vgl. S8 im Befundkatalog).
"""

from resources.lib.config import cConfig
from resources.lib.tools import logger

# siteId -> Adressen derselben Installation, bevorzugte zuerst.
# Der Kommentar nennt den Beleg, an dem die Zusammengehoerigkeit haengt.
ALTERNATES = {
    # identische Stylesheets (custom4.css, slider.css)
    'burningseries': ('burningseries.ac', 'burningseries.cx', 'bs.cine.to'),
    # identische Stylesheets (all.css, cssreset-min.css)
    'kinox': ('w11.kinox.to', 'kinoz.to', 'www21.kinox.to'),
    # identischer Theme-Ordner /templates/hdfilme/
    'hdfilme_1': ('hdfilme.to', 'hdfilme.cafe', 'hdfilme.bid'),
    # identischer Theme-Ordner /templates/xcine/
    'xcine': ('xcine.hair', 'xcine.online'),
    # streamcloud.watch leitet per 301 auf streamcloud.download
    'streamcloud': ('streamcloud.download', 'streamcloud.watch'),
}


def getAlternates(siteId):
    """Bekannte Adressen einer Quelle. Leeres Tupel, wenn keine hinterlegt."""
    return ALTERNATES.get(siteId, ())


def _settingName(siteId):
    return 'plugin_%s.domain' % siteId


def currentDomain(siteId, fallback=''):
    return cConfig().getSetting(_settingName(siteId), fallback)


def applyDomain(siteId, domain):
    """Uebernimmt eine Adresse - aber nur eine aus der hinterlegten Liste.

    Liefert True, wenn geschrieben wurde. Ein nicht gelisteter Wert wird
    abgelehnt und protokolliert, statt still uebernommen zu werden.
    """
    if domain not in getAlternates(siteId):
        logger.info('-> [domains]: Adresse %r fuer %r nicht in der Liste, '
                    'abgelehnt' % (domain, siteId))
        return False
    cConfig().setSetting(_settingName(siteId), domain)
    logger.info('-> [domains]: %s benutzt jetzt %s' % (siteId, domain))
    return True
