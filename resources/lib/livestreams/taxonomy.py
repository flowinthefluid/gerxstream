# -*- coding: utf-8 -*-
# Python 3
"""Stabile Taxonomie: interne IDs getrennt von uebersetzbaren Anzeigetexten.

Interne IDs (ASCII-Slugs) sind ueber Releases hinweg stabil und niemals an
Display-Texte gebunden. Anzeigenamen kommen aus ``strings.po`` (ueber die
String-ID) mit einem festen deutschen Fallback, falls eine Uebersetzung noch
fehlt - dasselbe Muster wie in ``resources/lib/categories.py``.
"""

# --- Top-Level-Bereiche ---------------------------------------------------
# id -> (string_id, fallback)
SECTIONS = (
    ('tv',      (30961, 'Fernsehen')),
    ('sports',  (30962, 'Sport & E-Sport')),
    ('social',  (30963, 'Social Media')),
    ('weather', (30964, 'Wetter')),
    ('webcam',  (30965, 'Webcams')),
)
SECTION_IDS = tuple(sid for sid, _ in SECTIONS)
_SECTION_LABELS = dict(SECTIONS)

# --- Genres ---------------------------------------------------------------
GENRES = (
    ('news',     (31100, 'Nachrichten')),
    ('sports',   (31101, 'Sport')),
    ('kids',     (31102, 'Kinder')),
    ('doc',      (31103, 'Dokumentation')),
    ('music',    (31104, 'Musik')),
    ('movies',   (31105, 'Filme')),
    ('series',   (31106, 'Serien')),
    ('drama',    (31107, 'Drama')),
    ('comedy',   (31108, 'Comedy')),
    ('anime',    (31109, 'Anime')),
    ('shopping', (31110, 'Shopping')),
    ('regional', (31111, 'Regional')),
    ('public',   (31112, 'Oeffentlich-rechtlich')),
    ('nature',   (31113, 'Natur')),
    ('adult',    (31114, 'Erotik')),   # nur bei aktivem NSFW-Schalter sichtbar
    # --- Webcam-Themen (dienen als thematischer Weg im Webcam-Baum) ---
    ('landmark', (31115, 'Sehenswuerdigkeiten')),
    ('building', (31116, 'Gebaeude')),
    ('mountains',(31117, 'Berge')),
    ('animals',  (31118, 'Tiere')),
    ('birds',    (31119, 'Voegel')),
    ('beach',    (31120, 'Straende')),
    ('pier',     (31121, 'Piers & Haefen')),
    ('park',     (31122, 'Parks')),
    ('traffic',  (31123, 'Verkehr')),
    ('city',     (31124, 'Stadt')),
    ('ski',      (31125, 'Ski & Schnee')),
    ('weather',  (31126, 'Wetter')),
)
GENRE_IDS = tuple(gid for gid, _ in GENRES)
_GENRE_LABELS = dict(GENRES)

# Welche Genres im Webcam-Baum als thematischer Weg angeboten werden.
WEBCAM_CATEGORY_IDS = ('landmark', 'building', 'mountains', 'animals', 'birds',
                       'beach', 'pier', 'park', 'traffic', 'city', 'ski',
                       'nature', 'weather')

# --- Laender (Kern; weitere kommen aus dem Katalog dazu) -------------------
COUNTRIES = (
    ('de', 'Deutschland'),
    ('at', 'Oesterreich'),
    ('ch', 'Schweiz'),
    ('hr', 'Kroatien'),
    ('gb', 'Grossbritannien'),
    ('us', 'USA'),
    ('fr', 'Frankreich'),
    ('it', 'Italien'),
    ('es', 'Spanien'),
    ('tr', 'Tuerkei'),
    ('int', 'International'),
)
_COUNTRY_LABELS = dict(COUNTRIES)


def _localized(string_id, fallback):
    try:
        from resources.lib.config import cConfig
        text = cConfig().getLocalizedString(string_id)
        if text and not str(text).startswith('#'):
            return text
    except Exception:
        pass
    return fallback


def section_label(section_id):
    entry = _SECTION_LABELS.get(section_id)
    return _localized(*entry) if entry else section_id


def genre_label(genre_id):
    entry = _GENRE_LABELS.get(genre_id)
    return _localized(*entry) if entry else genre_id


def country_label(country_id):
    return _COUNTRY_LABELS.get((country_id or '').lower(), (country_id or '').upper())


def is_known_section(section_id):
    return section_id in SECTION_IDS
