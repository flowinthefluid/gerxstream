# -*- coding: utf-8 -*-
# Python 3
"""GerXStream Livestream-Paket.

Adapter-/Provider-Modell fuer Live-Inhalte (Fernsehen, Sport, Social Media,
Wetter, Webcams). Alle Kataloge laufen durch ``resources.lib.contentgate``.

Module:
    taxonomy  - stabile IDs und Anzeigenamen fuer Bereiche/Genres/Laender
    model     - Kanal-/Quellen-Datenmodell mit Validierung
    catalog   - laedt und mischt Quelldateien, wendet das Gate an
    m3u       - erzeugt eine IPTV-Simple-taugliche M3U-Playlist
    epg       - XMLTV-Grabber (gzip/xz), speicherschonend per iterparse
    selector  - Reihenfolge der Quellen, Beschreibung, Failover
    export    - schreibt playlist.m3u und guide.xml in den Nutzerordner
"""
