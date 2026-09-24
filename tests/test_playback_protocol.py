# -*- coding: utf-8 -*-
"""Protokoll-Erkennung fuer die Webcam-Wiedergabe."""
from resources.lib.livestreams import model


def test_protocol_inference_and_validation():
    assert model.normalize_source({'url': 'rtsp://cam/live', 'protocol': 'rtsp'})['protocol'] == 'rtsp'
    assert model.normalize_source({'url': 'http://cam/video.mjpg', 'protocol': 'mjpeg'})['protocol'] == 'mjpeg'
    assert model.normalize_source({'url': 'http://cam/still.jpg', 'protocol': 'jpeg'})['protocol'] == 'jpeg'
    # Ungueltiges Protokoll faellt auf URL-Ableitung zurueck.
    assert model.normalize_source({'url': 'https://x/master.m3u8', 'protocol': 'bogus'})['protocol'] == 'hls'
