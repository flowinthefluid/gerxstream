# -*- coding: utf-8 -*-
"""Stream-URL-Validierung (fail-closed)."""
import pytest

from resources.lib.livestreams import model


@pytest.mark.parametrize('url, ok', [
    ('https://x/master.m3u8', True),
    ('http://cam/video.mjpg', True),
    ('rtsp://cam:554/live', True),
    ('rtmp://server/app/stream', True),
    ('plugin://plugin.video.youtube/play/?video_id=x', True),
    ('', False),
    ('javascript:alert(1)', False),
    ('data:text/html,x', False),
    ('file:///etc/passwd', False),
    ('/relative/path.m3u8', False),
    ('plugin://', False),        # kein Addon-Host
    ('not a url', False),
])
def test_is_valid_stream_url(url, ok):
    assert model.is_valid_stream_url(url) is ok


def test_invalid_url_rejects_source():
    assert model.normalize_source({'url': 'javascript:x'}) is None


def test_invalid_url_rejects_channel():
    ch = model.normalize_channel({
        'name': 'X', 'section': 'tv', 'nsfw': False,
        'sources': [{'url': 'file:///x'}]})
    assert ch is None  # keine gueltige Quelle -> Kanal verworfen
