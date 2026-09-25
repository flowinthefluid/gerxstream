# -*- coding: utf-8 -*-
# Python 3

"""Compatibility hooks for the former in-addon updater.

GerXStream and ResolveURL are released through the installed Kodi repository.
Kodi verifies and installs those packages itself, so this module must never
download or unpack add-ons from an unrelated forge at runtime.
"""

from xbmc import LOGINFO
from xbmcgui import Dialog

from resources.lib.tools import addon_log as log


def _show_repository_notice(silent):
    message = 'Aktualisierungen werden über das GerXStream Repository installiert.'
    log('[GerXStream] %s' % message, LOGINFO)
    if not silent:
        Dialog().ok('GerXStream', message)


def resolverUpdate(silent=False):
    """Keep legacy callers harmless; Kodi updates ResolveURL via the repository."""
    _show_repository_notice(silent)
    return None


def GerXStreamDevUpdate(silent=False):
    """Keep legacy callers harmless; Kodi updates GerXStream via the repository."""
    _show_repository_notice(silent)
    return None


def devUpdates():
    """Entry point for the former manual-update menu item."""
    _show_repository_notice(False)
