# Quellen nach Inhalt

Stand: 2026-09-20

Das Hauptmenue listet aktivierte Site-Plugins nicht mehr flach. Jedes
Site-Plugin traegt seine Kategorie-Zugehoerigkeit selbst als Modul-Attribut
`CONTENT_CATEGORIES` (z. B. `CONTENT_CATEGORIES = ('filme', 'serien')`);
ein Plugin kann absichtlich in mehreren Gruppen stehen. Die Reihenfolge und
die Anzeigenamen der Kategorien stehen zentral in `CATEGORY_ORDER` in
`resources/lib/handler/pluginHandler.py`, das beim Aufbau des Hauptmenues
die Attribute aller aktiven Plugins einsammelt. Das aendert weder die
Einstellungen noch die globale Suche und erzeugt keine zweite
Scraper-Instanz.

| Kategorie | Kennung | Beispiele fuer Mehrfachzuordnungen |
|---|---|---|
| Filme | `filme` | KinoGer, Flixitv, Movie2K, Kool/Huhu/Oha/Vavoo |
| Serien | `serien` | KinoGer, BurningSeries, SerienStream und Flixitv |
| Animes | `animes` | AniWorld, Anime-Loads, Anime-Stream, Anime Toast, KayoAnime, Proxer, SerienStream, BurningSeries |
| Dokus | `dokus` | Dokus4.me, media.ccc.de, ARD, Arte, MediathekViewWeb und KinoX |
| Kinder | `kinder` | Kids Tube, ARD Mediathek, MediathekViewWeb |

`Weitere Quellen` ist ein bewusstes Sicherheitsnetz: Ein neues, aktiviertes
Site-Plugin ohne (oder mit unbekanntem) `CONTENT_CATEGORIES`-Attribut bleibt
sichtbar und wird nicht stillschweigend ausgeblendet. Vor einem Release
soll es dort fachlich eingeordnet werden.
