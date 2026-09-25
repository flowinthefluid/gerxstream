# -*- coding: utf-8 -*-
# Python 3
"""Social-Media-Orchestrierung: nur offizielle, delegierende Plattformen.

Enthalten: YouTube und Twitch (Wiedergabe/Anmeldung ueber deren offizielle
Kodi-Addons). Bewusst NICHT enthalten: TikTok/Chaturbate/OnlyFans - diese
erfordern Scraping bzw. das Umgehen von Zugriffskontrollen und sind hier
ausgeschlossen.

Jede Plattform faellt unabhaengig aus: ein Fehler bei einer Plattform darf die
anderen nicht beeintraechtigen.
"""

PLATFORMS = ('youtube', 'twitch')

_TOGGLE = {'youtube': 'socialYoutube', 'twitch': 'socialTwitch'}


def enabled_platforms(cfg):
    """IDs der vom Nutzer aktivierten Plattformen (Default: an)."""
    return [pid for pid in PLATFORMS if cfg.getSettingBool(_TOGGLE[pid], True)]


def platform_module(pid):
    if pid == 'youtube':
        from resources.lib.livestreams.providers import youtube
        return youtube
    if pid == 'twitch':
        from resources.lib.livestreams.providers import twitch
        return twitch
    return None
