# -*- coding: utf-8 -*-
"""Tests fuer den M3U-Generator inkl. NSFW-Regression."""
from resources.lib import contentgate
from resources.lib.config import cConfig
from resources.lib.livestreams import m3u


ARD = {'id': 'gxs:tv:de:ard', 'name': 'Das Erste', 'section': 'tv',
       'country': 'de', 'language': ['de'], 'genre': ['news'], 'nsfw': False,
       'publisher': 'ard', 'logo': '', 'epg_id': 'ard.de',
       'sources': [{'source_id': 's1', 'url': 'https://x/master.m3u8',
                    'protocol': 'hls', 'quality': 'hd', 'official': True,
                    'reliability': 'high', 'region': 'de', 'headers': {}}]}

ADULT = {'id': 'gxs:tv:de:xxx', 'name': 'XXX Channel', 'section': 'tv',
         'country': 'de', 'language': ['de'], 'genre': ['adult'], 'nsfw': True,
         'publisher': 'xxx', 'logo': '', 'epg_id': '',
         'sources': [{'source_id': 's1', 'url': 'https://y/master.m3u8',
                      'protocol': 'hls', 'quality': 'hd', 'official': False,
                      'reliability': 'low', 'region': 'de', 'headers': {}}]}


def test_header_and_extm3u():
    cConfig().setSetting('showAdult', 'true')
    out = m3u.generate([ARD])
    assert out.startswith('#EXTM3U')
    assert 'tvg-id="ard.de"' in out
    assert 'group-title="Fernsehen;Deutschland;Nachrichten"' in out
    assert 'plugin://plugin.video.gerxstream/' in out  # plugin-URL, keine Roh-URL


def test_direct_mode_emits_raw_url():
    cConfig().setSetting('showAdult', 'true')
    out = m3u.generate([ARD], direct=True)
    assert 'https://x/master.m3u8' in out


def test_nsfw_excluded_when_disabled():
    """REGRESSION: bei NSFW=aus kein Erotik-Kanal und keine Erotik-Gruppe in der M3U."""
    cConfig().setSetting('showAdult', 'false')
    out = m3u.generate([ARD, ADULT])
    assert 'XXX Channel' not in out
    assert 'gxs:tv:de:xxx' not in out
    assert 'Erotik' not in out
    assert 'Das Erste' in out


def test_nsfw_included_when_enabled():
    cConfig().setSetting('showAdult', 'true')
    out = m3u.generate([ARD, ADULT])
    assert 'XXX Channel' in out


def test_fingerprint_comment_present():
    cConfig().setSetting('showAdult', 'false')
    out = m3u.generate([ARD])
    assert '# gerxstream visibility=' in out
