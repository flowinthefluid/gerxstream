# Installation Hinweise (GerXstream)

Dieses Addon nutzt die ID `plugin.video.gerxstream`.

## Voraussetzungen

1. Kodi 22 (primaer) oder Kodi 21 (weicher Fallback)
2. `script.module.resolveurl` muss installiert sein
3. Das GerXStream Repository (`repository.gerxstream`) aus der ZIP-Datei der
   GitLab-Pages-Quelle installieren. Anschliessend kann GerXStream über
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

## Datenmigration bei ID-Wechsel

Beim ersten Start unter `plugin.video.gerxstream`:

1. Bestehende Daten aus `special://home/userdata/addon_data/plugin.video.xstream/`
   werden nach `special://home/userdata/addon_data/plugin.video.gerxstream/` kopiert
2. Bereits vorhandene Dateien im Ziel werden nicht ueberschrieben
3. Der Lauf wird durch Markerdatei dokumentiert:
   `special://home/userdata/addon_data/plugin.video.gerxstream/.gerxstream_data_migrated`

Falls noch eine alte Installation `plugin.video.xstream` vorhanden ist, erscheint einmalig ein Hinweisdialog.
