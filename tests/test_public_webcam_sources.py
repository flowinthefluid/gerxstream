# -*- coding: utf-8 -*-
"""The shipped public webcam catalog must make both webcam and weather usable."""

from resources.lib.livestreams import catalog


def test_public_webcams_and_weather_camera_are_visible():
    catalog.load_all(force=True)
    webcam_ids = {channel['id'] for channel in catalog.channels_by_section('webcam')}
    weather_ids = {channel['id'] for channel in catalog.channels_by_section('weather')}

    assert 'gxs:webcam:de:alpspix' in webcam_ids
    assert 'gxs:webcam:de:wank-gipfel' in webcam_ids
    assert 'gxs:weather:de:zugspitze-gipfel' in weather_ids
