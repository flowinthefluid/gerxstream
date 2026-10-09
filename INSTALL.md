# Installation Hinweise (GerXstream)

Dieses Addon nutzt die ID `plugin.video.gerxstream`.

## Voraussetzungen

1. Kodi 22 (primaer) oder Kodi 21 (weicher Fallback)
2. `script.module.resolveurl` muss installiert sein
3. Das GerXStream Repository (`repository.gerxstream`) aus der ZIP-Datei der
   GitHub-Pages-Quelle installieren (`https://flowinthefluid.github.io/gerxstream/repo/`).
   Aktuelle Repository-ZIP: `repository.gerxstream-1.0.7.zip`.
   Anschliessend kann GerXStream über
   **Aus Repository installieren** installiert werden. ResolveURL 5.1.209 wird
   als Abhängigkeit aus demselben Repository bereitgestellt.

## ResolveURL Mindeststand

- Empfohlener Mindeststand: `5.1.208` (aktuelle Hoster-Unterstuetzung)
- Der Import in `addon.xml` verlangt mindestens `5.1.209`; Kodi installiert
  diese Version über das GerXStream Repository, falls sie noch nicht vorhanden ist.
- Beim Start wird die installierte Version immer ins Kodi-Log geschrieben
- Liegt die Version unter `5.1.208`, erzeugt der Service eine `LOGWARNING` Meldung

## Updates

- GerXStream und ResolveURL werden über Kodis Add-on-Verwaltung aktualisiert.
- Direkte Selbst-Updates aus GitHub werden nicht als Veröffentlichungsweg verwendet.
- GitHub Actions testet jeden neuen Stand und baut auf `main` den Pages-Katalog samt
   ZIPs aus den Quellen. Nach erfolgreicher Auslieferung steht Version 1.0.32 unter
   `zips/plugin.video.gerxstream/plugin.video.gerxstream-1.0.32.zip` bereit.

## Personenlisten ab 1.0.29

In den Einstellungen gibt es eigene Seitenleistenbereiche **Schauspieler** und
**Regisseure**. Dort sind Sortierung, Produktionsgruppen (Mehrfachauswahl) und
Anzahl getrennt einstellbar. Die bisherige gemeinsame Sortierung bleibt als
Vorgabe erhalten, bis eine neue Sortierung ausgewaehlt wird. Die Suche wurde
nicht verschoben; **Indexseiten 1** und **Indexseiten 2** sind jetzt **Indexseiten**.

- **A-Z**, **IMDb: bester Film** und **IMDb: Durchschnitt** sind verfuegbar.
- Fuer IMDb einen eigenen OMDb-Schluessel unter **TMDB** hinterlegen.
   Der kostenlose Tarif erlaubt 1.000 Abfragen pro Tag. Der erste Abruf kann
   laenger dauern; Filmwertungen werden 14 Tage gespeichert und fuer gemeinsame
   Filme mehrerer Personen wiederverwendet. Der Durchschnitt ist ungewichtet und
   beruecksichtigt nur verfuegbare Wertungen aus den Wikidata-Filmografien.
- Produktionsgruppen richten sich nach Film-Produktionslaendern, nicht nach
   Nationalitaet. Koproduktionen erlauben mehrere Gruppen pro Person.
- Eine Anzahl wie **100** begrenzt die Liste nach Filtern und Sortieren;
   **0** zeigt alle passenden Personen im geladenen Pool. Dieser umfasst bis zu
   500 beliebte Personen je Rolle plus eigene Schauspieler, keine vollstaendige
   weltweite Rangliste. Wikidata-Laender und Filmografien koennen unvollstaendig
   sein; unbekannte Laender werden nicht pauschal als **Other** einsortiert.

## Datenmigration bei ID-Wechsel

Beim ersten Start unter `plugin.video.gerxstream`:

1. Bestehende Daten aus `special://home/userdata/addon_data/plugin.video.xstream/`
   werden nach `special://home/userdata/addon_data/plugin.video.gerxstream/` kopiert
2. Bereits vorhandene Dateien im Ziel werden nicht ueberschrieben
3. Der Lauf wird durch Markerdatei dokumentiert:
   `special://home/userdata/addon_data/plugin.video.gerxstream/.gerxstream_data_migrated`

Falls noch eine alte Installation `plugin.video.xstream` vorhanden ist, erscheint einmalig ein Hinweisdialog.
