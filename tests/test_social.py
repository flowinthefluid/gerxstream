# -*- coding: utf-8 -*-
"""Social-Media: Parsing, URL-Bau, Aktivierung, Ausfall-Isolation."""
import json

from resources.lib.livestreams import social
from resources.lib.livestreams.providers import youtube, twitch
from resources.lib.config import cConfig


# --- YouTube --------------------------------------------------------------

YT_PAYLOAD = {
    'items': [
        {'id': {'videoId': 'abc123'},
         'snippet': {'title': 'Live News', 'channelTitle': 'NewsCh',
                     'thumbnails': {'medium': {'url': 'http://t/1.jpg'}}}},
        {'id': {'kind': 'channel'}, 'snippet': {'title': 'no video id'}},  # ignoriert
    ]
}


def test_youtube_parse_ignores_non_video():
    entries = youtube.parse_search_results(YT_PAYLOAD)
    assert len(entries) == 1
    assert entries[0]['video_id'] == 'abc123'
    assert entries[0]['channel'] == 'NewsCh'


def test_youtube_parse_bad_json():
    assert youtube.parse_search_results('{nope') == []
    assert youtube.parse_search_results(None) == []


def test_youtube_play_url_stable():
    assert youtube.play_url('XYZ') == 'plugin://plugin.video.youtube/play/?video_id=XYZ'


def test_youtube_search_without_key_returns_empty():
    assert youtube.search_live('', category_id='20') == []


# --- Twitch ---------------------------------------------------------------

TW_PAYLOAD = {
    'data': [
        {'user_login': 'streamer1', 'user_name': 'Streamer1', 'title': 'Ranked',
         'game_name': 'Chess', 'viewer_count': 42, 'language': 'de',
         'thumbnail_url': 'http://t/{width}x{height}.jpg'},
        {'title': 'no login'},  # ignoriert
    ]
}


def test_twitch_parse_and_thumb_substitution():
    entries = twitch.parse_streams(TW_PAYLOAD)
    assert len(entries) == 1
    assert entries[0]['channel'] == 'streamer1'
    assert '640' in entries[0]['thumb'] and '360' in entries[0]['thumb']


def test_twitch_play_url():
    assert twitch.play_url('foo') == 'plugin://plugin.video.twitch/?mode=play&channel_name=foo'


def test_twitch_without_client_id_returns_empty():
    assert twitch.get_streams('') == []


# --- Orchestrierung -------------------------------------------------------

def test_enabled_platforms_default_all():
    assert social.enabled_platforms(cConfig()) == ['youtube', 'twitch']


def test_platform_can_be_disabled():
    cConfig().setSetting('socialYoutube', 'false')
    assert social.enabled_platforms(cConfig()) == ['twitch']


def test_only_official_platforms_present():
    # Sicherstellen, dass keine abgelehnten Plattformen als Modul existieren.
    assert social.PLATFORMS == ('youtube', 'twitch')
    for bad in ('tiktok', 'chaturbate', 'onlyfans'):
        assert social.platform_module(bad) is None


def test_one_platform_failure_isolated(monkeypatch):
    # Faellt YouTube-Parsing aus, bleibt Twitch nutzbar.
    def boom(*a, **k):
        raise RuntimeError('yt down')
    monkeypatch.setattr(youtube, 'parse_search_results', boom)
    # Twitch-Parsing weiterhin ok.
    assert len(twitch.parse_streams(TW_PAYLOAD)) == 1
