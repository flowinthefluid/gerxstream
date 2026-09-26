# -*- coding: utf-8 -*-
"""Bevorzugte Hoster, gemerkter Hoster der Folgenliste und Kontextmenue."""

import json

from conftest import set_setting
from resources.lib import hosterprefs
from resources.lib.gui import hoster


VOE_DE = {'name': 'VOE', 'link': ['https://s.to/redirect/1', 'VOE'], 'languageCode': '1'}
VOE_EN = {'name': 'VOE', 'link': ['https://s.to/redirect/2', 'VOE'], 'languageCode': '2'}
DOOD = {'name': 'Dood', 'link': 'https://dood.re/e/abc'}
TAPE = {'name': 'Streamtape', 'link': 'https://streamtape.com/e/x'}
VIDOZA = {'name': 'Vidoza', 'link': 'https://vidoza.net/embed-1.html'}


def test_matching_by_name_prefix_and_host():
    assert hosterprefs.matches('voe', VOE_DE)
    assert hosterprefs.matches('DoodStream', DOOD)      # laengerer Wunschname, kurzer Seitenname
    assert hosterprefs.matches('streamtape', TAPE)
    assert hosterprefs.matches('vidoza', {'name': 'Server', 'link': 'https://vidoza.net/x'})
    assert not hosterprefs.matches('vid', VOE_DE)
    assert not hosterprefs.matches('', VOE_DE)


def test_reorder_is_stable_and_follows_preference_order():
    hosters = [TAPE, DOOD, VOE_DE, VIDOZA]
    assert hosterprefs.reorder(hosters, ['voe', 'streamtape']) == [VOE_DE, TAPE, DOOD, VIDOZA]
    assert hosterprefs.onlyPreferred(hosters, ['vidoza', 'voe']) == [VIDOZA, VOE_DE]
    assert hosterprefs.onlyPreferred(hosters, ['mixdrop']) == []


def test_site_list_overrides_list_for_all_sources():
    hosterprefs.save({'*': ['Streamtape'], 'serienstream': ['VOE', 'Vidoza']})
    assert hosterprefs.forSite('serienstream') == ['VOE', 'Vidoza']
    assert hosterprefs.forSite('kinox') == ['Streamtape']
    hosterprefs.setForSite('serienstream', [])
    assert hosterprefs.forSite('serienstream') == ['Streamtape']


def test_broken_setting_is_ignored():
    set_setting(hosterprefs.DATA_SETTING, '{kaputt')
    assert hosterprefs.load() == {}
    set_setting(hosterprefs.MODE_SETTING, 'unsinn')
    assert hosterprefs.mode() == hosterprefs.MODE_OFF


def test_seen_hosters_are_remembered_per_source():
    hosterprefs.rememberSeen('serienstream', [VOE_DE, DOOD, {'name': '[I]x[/I]'}])
    hosterprefs.rememberSeen('kinox', [TAPE])
    assert set(hosterprefs.seenNames('serienstream')) >= {'VOE', 'Dood'}
    assert 'Streamtape' not in hosterprefs.seenNames('serienstream')
    assert 'Streamtape' in hosterprefs.seenNames(hosterprefs.ALL_SOURCES)
    assert not hosterprefs.rememberSeen('../evil', [VOE_DE])


def test_sticky_hoster_keeps_name_and_language():
    hosterprefs.forgetSticky()
    assert hosterprefs.rememberSticky('a' * 32, 'serienstream', VOE_DE)
    remembered = hosterprefs.sticky('a' * 32, 'serienstream')
    assert remembered['name'] == 'VOE' and remembered['lang'] == '1'
    assert hosterprefs.stickyCandidates([VOE_EN, DOOD, VOE_DE], remembered) == [VOE_DE]
    # Andere Sprache ist kein Ersatz -> leer -> es wird wieder gefragt.
    assert hosterprefs.stickyCandidates([VOE_EN, DOOD], remembered) == []
    # Andere Queue oder Quelle: nichts gemerkt.
    assert hosterprefs.sticky('b' * 32, 'serienstream') is None
    assert hosterprefs.sticky('a' * 32, 'aniworld') is None
    hosterprefs.forgetSticky()
    assert hosterprefs.sticky('a' * 32, 'serienstream') is None


def test_sticky_needs_both_settings():
    set_setting('autoNextEpisodeEnabled', 'true')
    set_setting(hosterprefs.STICKY_SETTING, 'ask')
    assert not hosterprefs.stickyEnabled()
    set_setting(hosterprefs.STICKY_SETTING, 'sticky')
    assert hosterprefs.stickyEnabled()
    set_setting('autoNextEpisodeEnabled', 'false')
    assert not hosterprefs.stickyEnabled()


class _Params(object):
    def __init__(self, values):
        self.values = values

    def getValue(self, name):
        return self.values.get(name, False)


def test_following_episode_uses_remembered_hoster(monkeypatch):
    set_setting('autoNextEpisodeEnabled', 'true')
    set_setting(hosterprefs.STICKY_SETTING, 'sticky')
    hosterprefs.rememberSticky('c' * 32, 'serienstream', VOE_DE)
    monkeypatch.setattr(hoster.cHosterGui, '_isNativeEpisodePlaylistItem', classmethod(lambda cls, _p: True))
    gui = hoster.cHosterGui()
    params = _Params({'episodeQueue': 'c' * 32, 'episodeIndex': '3'})
    assert gui._automaticCandidates([DOOD, VOE_EN, VOE_DE], 'serienstream', params) == [VOE_DE]
    hosterprefs.forgetSticky()


def test_manual_selection_is_not_automatic(monkeypatch):
    set_setting('autoNextEpisodeEnabled', 'true')
    set_setting(hosterprefs.STICKY_SETTING, 'sticky')
    hosterprefs.rememberSticky('c' * 32, 'serienstream', VOE_DE)
    monkeypatch.setattr(hoster.cHosterGui, '_isNativeEpisodePlaylistItem', classmethod(lambda cls, _p: False))
    gui = hoster.cHosterGui()
    params = _Params({'episodeQueue': 'c' * 32, 'episodeIndex': '0'})
    assert gui._automaticCandidates([DOOD, VOE_DE], 'serienstream', params) == []
    hosterprefs.forgetSticky()


def test_preferred_autostart_candidates_and_only_filter(monkeypatch):
    monkeypatch.setattr(hoster.cHosterGui, '_isNativeEpisodePlaylistItem', classmethod(lambda cls, _p: False))
    hosterprefs.save({'*': ['Streamtape', 'VOE']})
    gui = hoster.cHosterGui()
    set_setting(hosterprefs.MODE_SETTING, 'auto')
    assert gui._automaticCandidates([DOOD, VOE_DE, TAPE], 'kinox', _Params({})) == [TAPE, VOE_DE]
    set_setting(hosterprefs.MODE_SETTING, 'only')
    assert gui._applyPreferences([DOOD, VOE_DE, TAPE], 'kinox') == [TAPE, VOE_DE]
    # manuelle Auswahl zeigt alles, nur sortiert
    assert gui._applyPreferences([DOOD, VOE_DE, TAPE], 'kinox', manual=True) == [TAPE, VOE_DE, DOOD]
    # passt nichts, bleibt die volle Liste
    assert gui._applyPreferences([DOOD, VIDOZA], 'kinox') == [DOOD, VIDOZA]


def test_try_hosters_falls_back_after_resolve_failures(monkeypatch):
    calls = []

    class Plugin(object):
        @staticmethod
        def getHosterUrl(link):
            calls.append(link)
            return [{'streamUrl': link, 'resolved': False}]

    class Progress(object):
        def iscanceled(self):
            return False

        def update(self, *_a):
            pass

    gui = hoster.cHosterGui()
    gui.dialog = Progress()
    monkeypatch.setattr(gui, 'play', lambda _part: False)   # jeder Resolve scheitert
    assert gui._tryHosters(Plugin, 'getHosterUrl', [TAPE, DOOD], 'kinox', _Params({})) is False
    assert calls == [TAPE['link'], DOOD['link']]

    started = []

    def play(part):
        started.append(part['streamUrl'])
        return True
    monkeypatch.setattr(gui, 'play', play)
    assert gui._tryHosters(Plugin, 'getHosterUrl', [TAPE, DOOD], 'kinox', _Params({})) is True
    assert started == [TAPE['link']]


def test_context_menu_always_offers_hoster_selection(real_strings):
    from resources.lib.gui.gui import cGui
    from resources.lib.gui.guiElement import cGuiElement

    captured = {}

    class Item(object):
        def addContextMenuItems(self, items):
            captured['items'] = items

    element = cGuiElement('Film', 'kinox', 'getHosters')
    element.setMediaType('movie')
    gui = cGui()
    getattr(gui, '_cGui__createContextMenu')(element, Item(), False, 'plugin://plugin.video.gerxstream/?site=kinox')
    commands = [command for _label, command in captured['items']]
    assert any('manual=1' in command for command in commands)
    json.dumps(commands)
