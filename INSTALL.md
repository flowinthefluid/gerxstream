# Installation Hinweise (GerXstream)

Dieses Addon nutzt die ID `plugin.video.gerxstream`.

## Voraussetzungen

1. Kodi 22 (primaer) oder Kodi 21 (weicher Fallback)
2. `script.module.resolveurl` muss installiert sein
3. Solange noch kein eigenes Repo aktiv verdrahtet ist, muss das ResolveURL-Repo vorab in Kodi hinzugefuegt werden

## ResolveURL Mindeststand

- Erwarteter Mindeststand: `5.1.208`
- Beim Start wird die installierte Version immer ins Kodi-Log geschrieben
- Liegt die Version darunter, erzeugt der Service eine `LOGWARNING` Meldung

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
