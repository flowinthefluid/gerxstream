# -*- coding: utf-8 -*-
"""Tests fuer die Kanal-/Quellen-Validierung (fail-closed)."""
from resources.lib.livestreams import model


def test_valid_channel_normalized():
    channel = model.normalize_channel({
        'name': 'Das Erste', 'section': 'tv', 'country': 'DE',
        'language': ['DE'], 'genre': ['News'], 'nsfw': False,
        'publisher': 'ard',
        'sources': [{'url': 'https://x/master.m3u8', 'official': True}],
    })
    assert channel is not None
    assert channel['country'] == 'de'
    assert channel['genre'] == ['news']
    assert channel['sources'][0]['protocol'] == 'hls'
    assert channel['id'].startswith('gxs:tv:de:')


def test_channel_without_sources_rejected():
    assert model.normalize_channel({'name': 'X', 'section': 'tv', 'sources': []}) is None


def test_channel_without_name_rejected():
    assert model.normalize_channel({'section': 'tv',
                                    'sources': [{'url': 'http://x'}]}) is None


def test_channel_unknown_section_rejected():
    assert model.normalize_channel({'name': 'X', 'section': 'bogus',
                                    'sources': [{'url': 'http://x'}]}) is None


def test_nsfw_non_bool_becomes_none():
    channel = model.normalize_channel({
        'name': 'X', 'section': 'tv',
        'nsfw': 'yes',  # kein echtes bool
        'sources': [{'url': 'http://x'}],
    })
    assert channel['nsfw'] is None


def test_protocol_inferred_from_plugin_url():
    source = model.normalize_source({'url': 'plugin://plugin.video.youtube/play/?x=1'})
    assert source['protocol'] == 'plugin'


def test_source_without_url_rejected():
    assert model.normalize_source({'quality': 'hd'}) is None
