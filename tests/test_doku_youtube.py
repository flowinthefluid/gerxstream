# -*- coding: utf-8 -*-
"""The separated YouTube documentary source must remain importable."""

import sites.doku_youtube as doku_youtube


def test_doku_youtube_exports_only_shared_existing_entry_points():
    assert callable(doku_youtube.showYTChannels)
    assert callable(doku_youtube.showYTGenre)
