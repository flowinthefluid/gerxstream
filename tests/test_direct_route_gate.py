# -*- coding: utf-8 -*-
"""Abnahme Area 4: die direkte Kanal-Route ist NSFW-/Rechte-gegated
(Favorit / IPTV-Simple plugin://-URL koennen NSFW nicht umgehen)."""
from resources.lib.livestreams import model, catalog
from resources.lib.config import cConfig


def _nsfw_channel():
    return model.normalize_channel({
        'name': 'Adult Cam', 'section': 'webcam', 'country': 'us', 'nsfw': True,
        'genre': ['adult'],
        'sources': [{'url': 'https://x/a.m3u8', 'official': True}]})


def test_get_channel_blocks_nsfw_when_disabled(monkeypatch):
    ch = _nsfw_channel()
    monkeypatch.setattr(catalog, 'load_all', lambda force=False: [ch])
    cConfig().setSetting('showAdult', 'false')
    assert catalog.get_channel(ch['id']) is None      # kein Leak ueber direkte Route


def test_get_channel_allows_nsfw_when_enabled(monkeypatch):
    ch = _nsfw_channel()
    monkeypatch.setattr(catalog, 'load_all', lambda force=False: [ch])
    cConfig().setSetting('showAdult', 'true')
    assert catalog.get_channel(ch['id']) is not None


def test_get_channel_blocks_unapproved(monkeypatch):
    ch = model.normalize_channel({
        'name': 'NoRights', 'section': 'webcam', 'country': 'us', 'nsfw': False,
        'sources': [{'url': 'http://y/v.mjpg', 'official': False}]})  # unknown rights
    monkeypatch.setattr(catalog, 'load_all', lambda force=False: [ch])
    cConfig().setSetting('showAdult', 'true')
    assert catalog.get_channel(ch['id']) is None
