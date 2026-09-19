# Coding-Plan für GerXStream

Dieses Dokument richtet sich an jeden (menschlichen oder KI-)Agenten, der an
diesem Repository weiterarbeitet. Es beschreibt Architektur, Konventionen und
Sicherheitsregeln, die beim Ändern von Code einzuhalten sind. Für konkrete,
bereits geprüfte Einzelfunde siehe [BEFUNDE.md](BEFUNDE.md); für die geplante
Repo-/Update-Struktur siehe [REPO-SPEC.md](REPO-SPEC.md).

## 1. Was dieses Addon ist

Kodi-Video-Addon (`plugin.video.gerxstream`), Python 3, Zielplattform Kodi 22
„Piers" mit Kodi 21 „Omega" als Fallback. Es fungiert als Meta-Suchmaschine:
Eigenständige „Site-Plugins" unter [sites/](../sites/) kapseln jeweils eine
Webseite und liefern Kodi-Listen (Ordner/Streams) über eine gemeinsame
GUI-Abstraktion.

## 2. Startablauf

```
default.py        Einstiegspunkt für Kodi-Aufrufe (plugin://…)
  -> gerxstream.py  parseUrl(): liest Parameter, ruft Site-Funktionen auf
service.py          Hintergrunddienst: Migration, Cache-Pflege, Update-Status-Logs
```

`resources/lib/handler/ParameterHandler.py` parst die `plugin://`-URL,
`resources/lib/handler/requestHandler.py` erledigt HTTP(S), `resources/lib/gui/`
baut die Kodi-`ListItem`s.

## 3. Site-Plugin-Konventionen

Jede Datei in `sites/` folgt demselben Muster:

```python
def showMovies(sSearchText=None, sCat=None):
    oGui = cGui()
    ...
    oGui.setEndOfDirectory()
```

- Einstiegsfunktionen (von außen über die URL aufrufbar) **müssen** in der
  Whitelist `SCRAPER_ENTRY_FUNCTIONS` in [gerxstream.py](../gerxstream.py)
  eingetragen sein. Ohne Eintrag ist die Funktion nicht routbar (S1/S8-Härtung,
  siehe unten) — beim Hinzufügen neuer Site-Funktionen immer zuerst dort
  ergänzen.
- GUI-Aufbau ausschließlich über `cGuiElement`/`cGui` (`resources/lib/gui/`),
  niemals direkt `xbmcplugin`/`xbmcgui` in einer `sites/*.py`-Datei verwenden.
- HTTP-Zugriffe ausschließlich über `cRequestHandler`
  (`resources/lib/handler/requestHandler.py`) — er kümmert sich um Timeouts,
  TLS-Prüfung und Caching. Kein `requests`/`urllib` direkt in Site-Plugins.
- Text-/HTML-Parsing über `cParser` (`resources/lib/tools.py`), lokalisierte
  Strings über `cConfig().getLocalizedString(<id>)`
  (`resources/language/*/strings.po`).
- Einstellungen ausschließlich über `cConfig().getSetting*(...)` lesen, nie
  `xbmcaddon` direkt in Site-Plugins importieren.

## 4. Sicherheitsregeln (nicht verhandelbar)

Diese Regeln wurden nach konkreten Sicherheitsfunden in `docs/BEFUNDE.md`
festgelegt und dürfen bei neuem Code nicht erneut verletzt werden:

1. **Kein `eval()`/`exec()` auf Daten, die von außen kommen** (URL-Parameter,
   HTTP-Antworten, TMDB-Antworten). Strukturen als `dict`/`list` durchreichen
   oder `ast.literal_eval()` mit `try/except (ValueError, SyntaxError)`.
2. **TLS-Prüfung bleibt aktiv** (`ssl_verify`-Default ist `True`). Wird eine
   Ausnahme für eine einzelne Quelle gebraucht, nur über ein explizites,
   standardmäßig deaktiviertes Setting (`plugin_<id>_allowInsecureTLS`) und mit
   `LOGWARNING`-Eintrag inkl. Domainname.
3. **URL-/Funktionsrouting nur über die Whitelist** `SCRAPER_ENTRY_FUNCTIONS`
   in `gerxstream.py`. Kein dynamisches `__import__`/`getattr` auf ungefilterte
   Namen aus der URL.
4. **Keine hartcodierten Zugangsdaten/API-Keys im Code.** Nutzer-eigene Keys
   werden aus den Einstellungen des jeweiligen Addons gelesen (Beispiel:
   `sites/kids_tube.py::_youtubeApiKey()` liest den Schlüssel aus
   `plugin.video.youtube`).
5. **Zip-Extraktion/Update-Pfade** (`resources/lib/updateManager.py`) müssen
   Zielpfade gegen ein bekanntes Wurzelverzeichnis normalisieren
   (`os.path.commonpath`), bevor geschrieben/gelöscht wird (Zip-Slip-Schutz).
   `plugin_id` für Updates wird gegen `cConfig().getAddonInfo('id')` geprüft,
   nicht ungeprüft aus Settings übernommen.
6. **Cache-Inhalte** werden über `json.dumps`/`json.loads` serialisiert, nie
   über `eval()`/`repr()`.

## 5. Verifikation vor jedem Commit

```powershell
python -W error::SyntaxWarning -m compileall -q -f -x "\.tmp|design|__pycache__" .
python -m pyflakes .
```

Beide Kommandos müssen sauber durchlaufen (Exit-Code 0 / keine neuen Findings)
bevor committet wird. Bei Bulk-Edits über mehrere Dateien (Regex-Ersetzungen,
Encoding-Fixes) zusätzlich gegen eine bekannte gute Referenzversion prüfen
(`ast.literal_eval`-Wertevergleich für String-Literale, byteweiser Vergleich
bei reinen Encoding-Fixes) — ungeprüfte Bulk-Edits waren in der Vergangenheit
die Ursache für stille Korruption in mehreren Site-Plugins gleichzeitig.

## 6. Branding

Aktuelles Markendesign: violett→smaragdgrünes „GX"-Pfeilsymbol mit Wortmarke
„GerXstream". Quelldateien: [resources/clearlogo.png](../resources/clearlogo.png),
[resources/icon.png](../resources/icon.png), [resources/banner.png](../resources/banner.png),
[resources/fanart.jpg](../resources/fanart.jpg). Neue Grafiken (z. B. weitere
In-GUI-Badges unter `resources/art/`) müssen zu diesem Farbschema passen und
dürfen keine Elemente des ursprünglichen Vorgänger-Projekts (rotes „X"-Logo)
enthalten.

## 7. Commit-Konventionen

- Commit-Nachrichten auf Deutsch, kurz und beschreibend, kein KI-Autor als
  Co-Author/Trailer.
- Größere Reparaturen (Encoding-, Regex-, Semantik-Fixes über mehrere Dateien)
  einzeln committen, nicht mit funktionalen Änderungen mischen.

## 8. Wo was liegt

| Bereich | Pfad |
|---|---|
| Einstiegspunkt / Routing-Whitelist | [gerxstream.py](../gerxstream.py) |
| Hintergrunddienst (Migration, Cache, Update-Status) | [service.py](../service.py) |
| GUI-Aufbau (`ListItem`, InfoTag, Kontextmenüs) | [resources/lib/gui/](../resources/lib/gui/) |
| HTTP/Cache/TLS | [resources/lib/handler/requestHandler.py](../resources/lib/handler/requestHandler.py) |
| Utilities (Logging, Migration, Cache, Parser) | [resources/lib/tools.py](../resources/lib/tools.py) |
| TMDB-Metadaten | [resources/lib/tmdb.py](../resources/lib/tmdb.py), [resources/lib/tmdbinfo.py](../resources/lib/tmdbinfo.py) |
| Site-Plugins | [sites/](../sites/) |
| Lokalisierung | [resources/language/](../resources/language/) |
| Sicherheitsfunde & Status | [BEFUNDE.md](BEFUNDE.md) |
| Ziel-Repo-Struktur / Update-Verdrahtung | [REPO-SPEC.md](REPO-SPEC.md) |
