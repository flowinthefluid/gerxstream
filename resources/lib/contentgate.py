# -*- coding: utf-8 -*-
# Python 3
"""Zentrale Sichtbarkeits- und NSFW-Logik fuer GerXStream.

Ein einziger Ort entscheidet, ob ein Inhalt sichtbar ist - fuer die
Livestream-Menues, den M3U-Export, den EPG-Grabber, die globale Suche und
die bestehenden Site-Plugins. Es gibt bewusst keine verstreuten if-Abfragen
mit abweichender Logik; alle rufen ``is_channel_visible`` / ``filter_channels``
bzw. die Achsen-Funktionen (``is_section_visible`` ...) auf.

Grundregel: **fail-closed.** Fehlt eine Angabe, ist ein Datensatz defekt oder
wirft das Laden eine Ausnahme, gilt der Inhalt als *nicht* sichtbar. NSFW ist
eine eigene, ausschliessliche Achse: Erotik-Inhalte erscheinen nur, wenn der
explizite Schalter ``showAdult`` an ist - niemals implizit ueber eine Genre-
oder Laenderauswahl.
"""

import hashlib

from resources.lib.config import cConfig

# --- Setting-IDs (stabil, niemals aendern) --------------------------------

SETTING_NSFW = 'showAdult'

# Ein Boolean-Setting je Top-Level-Bereich. Fehlt es, gilt "sichtbar".
SECTION_SETTINGS = {
    'tv':      'lsSectionTv',
    'sports':  'lsSectionSports',
    'social':  'lsSectionSocial',
    'weather': 'lsSectionWeather',
    'webcam':  'lsSectionWebcam',
}

SETTING_COUNTRY_MODE = 'lsCountryMode'      # 'all' | 'whitelist' | 'blacklist'
SETTING_COUNTRIES = 'lsCountries'           # CSV aus Laendercodes
SETTING_GENRES_HIDDEN = 'lsGenresHidden'    # CSV aus versteckten Genre-Slugs

# NSFW-Schluesselwoerter als *zweite* Verteidigungslinie fuer Fremdquellen
# ohne eigenes nsfw-Flag (bestehende Scraper). Bewusst eine Heuristik, keine
# Garantie - das gehoert so in den Hilfetext des Settings.
NSFW_KEYWORDS = (
    'porn', 'xxx', 'erotik', 'erotic', 'hentai', 'adult', 'nsfw', 'sex',
)

# Genre-Slug, der Erwachsenen-Inhalt kennzeichnet.
NSFW_GENRE = 'adult'


def _csv(value):
    return [part.strip() for part in (value or '').split(',') if part.strip()]


# --- Achsen ---------------------------------------------------------------

def is_nsfw_enabled():
    """Einzige Auswertung von ``showAdult`` im gesamten Addon."""
    return cConfig().getSettingBool(SETTING_NSFW, False)


def is_section_visible(section_id):
    setting = SECTION_SETTINGS.get(section_id)
    if not setting:
        # Unbekannter Bereich -> fail-closed.
        return False
    return cConfig().getSettingBool(setting, True)


def get_visible_sections():
    return [sid for sid in SECTION_SETTINGS if is_section_visible(sid)]


def is_country_visible(country):
    if not country:
        return False
    mode = (cConfig().getSetting(SETTING_COUNTRY_MODE, 'all') or 'all').lower()
    if mode == 'all':
        return True
    selection = set(c.lower() for c in _csv(cConfig().getSetting(SETTING_COUNTRIES, '')))
    country = country.lower()
    if mode == 'whitelist':
        # Leere Whitelist bedeutet "noch nichts gewaehlt" -> alles zeigen,
        # statt den Bereich versehentlich komplett zu leeren.
        return country in selection if selection else True
    if mode == 'blacklist':
        return country not in selection
    return True


def get_visible_countries(all_countries):
    """Sichtbare Laender aus der Gesamtmenge, Reihenfolge bleibt erhalten."""
    seen = []
    for country in all_countries:
        if country and country not in seen and is_country_visible(country):
            seen.append(country)
    return seen


def is_genre_visible(genre):
    """Ein Genre ist sichtbar, solange es nicht ausgeblendet wurde.

    NSFW wird hier NICHT behandelt - Erotik-Inhalt haengt ausschliesslich am
    ``showAdult``-Schalter (siehe ``is_channel_visible``). Blacklist-Modell:
    neue Genres sind ohne Zutun sichtbar.
    """
    hidden = set(g.lower() for g in _csv(cConfig().getSetting(SETTING_GENRES_HIDDEN, '')))
    return genre.lower() not in hidden if genre else True


def get_visible_genres(all_genres):
    return [g for g in all_genres if is_genre_visible(g)]


# --- NSFW-Erkennung -------------------------------------------------------

def is_text_nsfw(*texts):
    """Heuristische NSFW-Erkennung fuer Fremddaten ohne eigenes Flag."""
    haystack = ' '.join(t for t in texts if t).lower()
    return any(keyword in haystack for keyword in NSFW_KEYWORDS)


def _channel_is_nsfw(channel):
    """Ob ein Kanal als NSFW gilt. Fail-closed: fehlt das Flag -> True."""
    flag = channel.get('nsfw', None)
    if flag is None:
        # Keine explizite Angabe -> im Zweifel als NSFW behandeln, damit ein
        # unmarkierter Erotik-Kanal nie bei ausgeschaltetem Schalter auftaucht.
        return True
    if not isinstance(flag, bool):
        return True
    if flag:
        return True
    # Explizit als "kein NSFW" markiert: trotzdem gegen Genre/Name pruefen,
    # falls die Markierung falsch ist.
    genres = channel.get('genre') or []
    if NSFW_GENRE in [str(g).lower() for g in genres]:
        return True
    return is_text_nsfw(channel.get('name', ''), ' '.join(str(g) for g in genres))


# --- Gesamtentscheidung ---------------------------------------------------

def is_channel_visible(channel):
    """Die eine Funktion, die alle Menuegeneratoren aufrufen. Fail-closed."""
    try:
        if not isinstance(channel, dict):
            return False

        # 1) NSFW-Achse zuerst und ausschliesslich ueber den Schalter.
        if _channel_is_nsfw(channel) and not is_nsfw_enabled():
            return False

        # 2) Top-Level-Bereich.
        if not is_section_visible(channel.get('section')):
            return False

        # 3) Land (falls angegeben).
        country = channel.get('country')
        if country and not is_country_visible(country):
            return False

        # 4) Genre: sichtbar, wenn mindestens ein nicht-NSFW-Genre sichtbar ist
        #    bzw. der Kanal keine Genres fuehrt. NSFW-Genre zaehlt hier nicht,
        #    es wird allein ueber Schritt 1 gesteuert.
        genres = [str(g).lower() for g in (channel.get('genre') or []) if g]
        relevant = [g for g in genres if g != NSFW_GENRE]
        if relevant and not any(is_genre_visible(g) for g in relevant):
            return False

        return True
    except Exception:
        # Jeder Fehler in der Sichtbarkeitspruefung blendet aus, statt zu zeigen.
        return False


def filter_channels(channels):
    """Generator ueber alle sichtbaren Kanaele - der Standardweg."""
    for channel in channels or []:
        if is_channel_visible(channel):
            yield channel


# --- Cache-Invalidierung --------------------------------------------------

def visibility_fingerprint():
    """Kurzer Hash ueber alle sichtbarkeitsrelevanten Settings.

    Wird in Cache-Keys (Katalog, M3U, EPG-Auswahl) aufgenommen und beim
    Rendern verglichen. Aendert der Nutzer NSFW, Laender, Genres oder einen
    Bereich, aendert sich der Fingerprint - die betroffenen Ableitungen
    werden dadurch verworfen und neu aufgebaut.
    """
    cfg = cConfig()
    parts = [
        '1' if is_nsfw_enabled() else '0',
        (cfg.getSetting(SETTING_COUNTRY_MODE, 'all') or 'all'),
        ','.join(sorted(_csv(cfg.getSetting(SETTING_COUNTRIES, '')))),
        ','.join(sorted(_csv(cfg.getSetting(SETTING_GENRES_HIDDEN, '')))),
    ]
    for sid in sorted(SECTION_SETTINGS):
        parts.append('%s=%s' % (sid, '1' if is_section_visible(sid) else '0'))
    raw = '|'.join(parts)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()[:12]
