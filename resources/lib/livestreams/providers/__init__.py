# -*- coding: utf-8 -*-
# Python 3
"""Provider-/Adapter-Registry fuer Livestream-Quellen.

Ein Provider liefert Kanal-Metadaten (``catalog()``); Netzzugriffe gehoeren in
den Service, nicht in den Menueaufbau. Kuratierte Kataloge liegen als JSON
unter ``resources/livestreams/sources/`` bzw. im Nutzerprofil und werden von
``resources.lib.livestreams.catalog`` geladen - dafuer braucht es kein
Provider-Modul. Eigene, dynamische Quellen (APIs, dokumentierte Feeds) kommen
als Modul hierher; siehe docs/livestreams-architektur.md §10.

Bewusst NICHT enthalten: Provider, die ungesicherte fremde Kameras aufspueren
(Geraetesuchmaschinen, Dork-Scraper, Insecam-artige Aggregatoren). Solche
Quellen liefern keine Freigabe-Metadaten und werden vom Rechte-Gate ohnehin
als 'unknown' ausgeschlossen.
"""
