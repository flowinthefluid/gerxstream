# Installation Hinweise (GerXstream)

Dieses Addon nutzt die ID `plugin.video.gerxstream`.

## Voraussetzungen

1. Kodi 22 (primaer) oder Kodi 21 (weicher Fallback)
2. `script.module.resolveurl` muss installiert sein
3. Empfohlen: das GerXStream Repository (`repository.gerxstream`) als Quelle
   hinzufuegen — darueber lassen sich sowohl GerXStream als auch die
   ResolveURL-Repository-Quelle (`repository.resolveurl`) direkt installieren,
   ohne das ResolveURL-Repo von Hand suchen zu muessen. Siehe
   `docs/REPO-SPEC.md` fuer die Repo-Struktur.

## ResolveURL Mindeststand

- Empfohlener Mindeststand: `5.1.208` (aktuelle Hoster-Unterstuetzung)
- Der Import in `addon.xml` verlangt lediglich `5.1.0` und ist `optional`,
  damit eine bereits vorhandene, aeltere ResolveURL-Installation GerXStream
  nicht am Start hindert (Kodi deaktiviert Addons sonst hart, wenn eine
  vorhandene Abhaengigkeit die verlangte Version unterschreitet)
- Beim Start wird die installierte Version immer ins Kodi-Log geschrieben
- Liegt die Version unter `5.1.208`, erzeugt der Service eine `LOGWARNING` Meldung

## Hinweise zum Selbst-Update

- Das alte xStream Selbst-Update ist absichtlich deaktiviert
- Beim Start wird einmalig protokolliert: `Selbst-Update deaktiviert, kein Repo hinterlegt`
- Im Dialog "Plugin Informationen" wird derselbe Hinweis sichtbar angezeigt

## Datenmigration bei ID-Wechsel

Beim ersten Start unter `plugin.video.gerxstream`:

1. Bestehende Daten aus `special://home/userdata/addon_data/plugin.video.xstream/`
   werden nach `special://home/userdata/addon_data/plugin.video.gerxstream/` kopiert
2. Bereits vorhandene Dateien im Ziel werden nicht ueberschrieben
3. Der Lauf wird durch Markerdatei dokumentiert:
   `special://home/userdata/addon_data/plugin.video.gerxstream/.gerxstream_data_migrated`

Falls noch eine alte Installation `plugin.video.xstream` vorhanden ist, erscheint einmalig ein Hinweisdialog.
