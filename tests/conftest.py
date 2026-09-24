# -*- coding: utf-8 -*-
"""Test-Bootstrap: Kodi-Stubs bereitstellen, Repo-Root importierbar machen."""
import os
import sys

import pytest

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TEST_DIR)
_STUBS = os.path.join(_TEST_DIR, 'kodistubs')

# Profil-Verzeichnis fuer die Stubs isolieren.
os.environ.setdefault('GXS_PROFILE', os.path.join(_TEST_DIR, '_profile'))
os.environ.setdefault('GXS_ADDON_PATH', _REPO_ROOT)

for path in (_STUBS, _REPO_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture(autouse=True)
def clean_settings():
    """Vor jedem Test die Settings und den cConfig-Singleton zuruecksetzen."""
    import xbmcaddon
    xbmcaddon._reset()
    # cConfig cached Addon-Instanzen; die zeigen weiter auf denselben _STORE,
    # daher genuegt das Leeren des Stores. Der Singleton bleibt bestehen.
    yield
    xbmcaddon._reset()


def set_setting(sid, value):
    from resources.lib.config import cConfig
    cConfig().setSetting(sid, value)
