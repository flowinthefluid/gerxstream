# -*- coding: utf-8 -*-
# Python 3
"""Dialoge fuer 'Laender auswaehlen' / 'Genres auswaehlen'.

Dynamische Auswahl statt statischer <option>-Listen: die Auswahl folgt dem
tatsaechlichen Katalog. Ergebnis landet in stabilen CSV-Settings
(``lsCountries`` / ``lsGenresHidden``), niemals an Anzeigetexte gebunden.
Nach dem Speichern wird die Ansicht neu aufgebaut.
"""

import xbmc
import xbmcgui

from resources.lib import contentgate
from resources.lib.config import cConfig
from resources.lib.livestreams import catalog, taxonomy


def _all_countries():
    seen = []
    for channel in catalog.load_all():
        country = channel.get('country')
        if country and country not in seen:
            seen.append(country)
    # Bekannte Kern-Laender zuerst, dann der Rest aus dem Katalog.
    ordered = [c for c, _ in taxonomy.COUNTRIES if c in seen]
    ordered += [c for c in seen if c not in ordered]
    return ordered


def _all_genres():
    seen = []
    for channel in catalog.load_all():
        for genre in channel.get('genre') or []:
            if genre and genre not in seen:
                seen.append(genre)
    ordered = [g for g in taxonomy.GENRE_IDS if g in seen]
    ordered += [g for g in seen if g not in ordered]
    # 'adult' erscheint hier nur, wenn der NSFW-Schalter an ist - sonst
    # taucht Erotik gar nicht als waehlbares Genre auf.
    if not contentgate.is_nsfw_enabled():
        ordered = [g for g in ordered if g != contentgate.NSFW_GENRE]
    return ordered


def edit_countries():
    countries = _all_countries()
    if not countries:
        xbmcgui.Dialog().ok('GerXStream', cConfig().getLocalizedString(31200))
        return
    labels = [taxonomy.country_label(c) for c in countries]
    current = set(x.strip().lower() for x in (cConfig().getSetting('lsCountries', '') or '').split(',') if x.strip())
    preselect = [i for i, c in enumerate(countries) if c in current] if current else list(range(len(countries)))
    chosen = xbmcgui.Dialog().multiselect(cConfig().getLocalizedString(30974), labels, preselect=preselect)
    if chosen is None:
        return
    selected = [countries[i] for i in chosen]
    cConfig().setSetting('lsCountries', ','.join(selected))
    # Sobald der Nutzer aktiv waehlt, auf Whitelist umstellen (sofern noch 'all').
    if (cConfig().getSetting('lsCountryMode', 'all') or 'all') == 'all':
        cConfig().setSetting('lsCountryMode', 'whitelist')
    xbmc.executebuiltin('Container.Refresh')


def edit_genres():
    genres = _all_genres()
    if not genres:
        xbmcgui.Dialog().ok('GerXStream', cConfig().getLocalizedString(31200))
        return
    labels = [taxonomy.genre_label(g) for g in genres]
    hidden = set(x.strip().lower() for x in (cConfig().getSetting('lsGenresHidden', '') or '').split(',') if x.strip())
    # Vorauswahl = sichtbare Genres (also NICHT versteckte).
    preselect = [i for i, g in enumerate(genres) if g not in hidden]
    chosen = xbmcgui.Dialog().multiselect(cConfig().getLocalizedString(30977), labels, preselect=preselect)
    if chosen is None:
        return
    visible = {genres[i] for i in chosen}
    # Alles, was nicht gewaehlt wurde, wird versteckt. NSFW bleibt unberuehrt -
    # 'adult' wird nie hierueber aktiviert (haengt nur an showAdult).
    new_hidden = [g for g in genres if g not in visible and g != contentgate.NSFW_GENRE]
    cConfig().setSetting('lsGenresHidden', ','.join(new_hidden))
    xbmc.executebuiltin('Container.Refresh')


def edit_rh_categories():
    """Welche Webcam-Kategorien das Rabbithole zieht (Whitelist, leer = alle).

    NSFW ist hier bewusst NICHT waehlbar - Erotik gibt es ausschliesslich ueber
    den NSFW-Schalter im NSFW-Einstellungsbereich, nie ueber eine Kategoriewahl.
    """
    categories = [c for c in taxonomy.WEBCAM_CATEGORY_IDS if c != contentgate.NSFW_GENRE]
    labels = [taxonomy.genre_label(c) for c in categories]
    current = set(x.strip().lower() for x in (cConfig().getSetting('rhCategories', '') or '').split(',') if x.strip())
    preselect = [i for i, c in enumerate(categories) if c in current] if current else list(range(len(categories)))
    chosen = xbmcgui.Dialog().multiselect(cConfig().getLocalizedString(31242), labels, preselect=preselect)
    if chosen is None:
        return
    selected = [categories[i] for i in chosen]
    # Alle gewaehlt = keine Einschraenkung -> leer speichern (== "alle").
    cConfig().setSetting('rhCategories', '' if len(selected) == len(categories) else ','.join(selected))
