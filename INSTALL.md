# Installation Hinweise (GerXstream)

Dieses Addon nutzt die ID `plugin.video.gerxstream`.

## Voraussetzungen

1. Kodi 22 (primaer) oder Kodi 21 (weicher Fallback)
2. `script.module.resolveurl` muss installiert sein
3. Das GerXStream Repository (`repository.gerxstream`) aus der ZIP-Datei der
   GitHub-Pages-Quelle installieren (`https://flowinthefluid.github.io/gerxstream/repo/`).
   Aktuelle Repository-ZIP: `repository.gerxstream-1.0.8.zip`.
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

## Wiedergabe ab 1.0.34

- **Naechste Folge automatisch abspielen** startet die Folgen des aktuellen
   Serien-/Staffelordners als Kodi-Videoplaylist, beginnend bei der gewaehlten Folge.
   Der native Befehl **Naechster Titel** kann damit auch den Abspann ueberspringen.
- Bei **Nachfragen** erscheint die Hoster-Auswahl fuer jede Folge. Bei
   **gleichen Hoster weiterverwenden** wird der erste gewaehlte Hoster fuer die
   folgenden Folgen bevorzugt; fehlt er, bleibt die Auswahl verfuegbar.
- Filme und Folgen mit bekannter Laufzeit werden ab **90 %** als gesehen markiert,
   auch wenn danach gestoppt oder zur naechsten Folge gesprungen wird.
   Die Wiedergabe endet nicht automatisch bei 90 %.
- Die Markierungen werden lokal in `watched_items.json` gespeichert, getrennt vom
   optionalen Verlauf und ohne Stream-URLs. Nach Installation dieser Aenderung
   Kodi neu starten, damit die dauerhafte Wiedergabeueberwachung laeuft.

## Sicherungen ab 1.0.38

Unter **Einstellungen -> Sichern und Wiederherstellen** stehen folgende Arten:

- **Ausgewaehlte Bereiche exportieren/importieren** fuer eine beliebige
   Kombination aus Einstellungen, Konten, Watchlist/Favorites, Historie und
   Gesehen-Status. Beim Export Konten bei Bedarf explizit anwaehlen und die
   Klartextwarnung bestaetigen. Auch die Gesamtsicherung inklusive Konten und
   einzelne Kontensicherungen koennen direkt in die private Cloud geschrieben
   werden. Beim Import bleiben nicht ausgewaehlte Bereiche unveraendert.
- **Einstellungsprofil ohne Konten** fuer Freunde/Familie: Schalter, Zahlen,
   feste Auswahlwerte, Hoster-Reihenfolge und Hauptmenue-Anordnung. Freie
   Texte, API-Schluessel, Konten, Cookies, Cloud-Zugangsdaten und Geraetepfade
   werden nicht uebernommen. Vorhandene Konten beim Empfaenger bleiben erhalten.
- **Geraetestand ohne Konten** fuer die eigenen Geraete: dasselbe portable
   Profil plus Favorites-Ordnerbaum, Watchlist-Statuslisten, Historie und
   Gesehen-Markierungen. Diese persoenlichen Listen nicht unbedacht teilen.
- **Gesamtsicherung** enthaelt auch Konten/Passwoerter aus den Add-on-Einstellungen
   und ist **nicht verschluesselt**. Nur privat speichern. Sitzungen anderer
   Add-ons oder beliebige Token-/Cookie-Dateien werden nicht kopiert.
- **Installierbare Add-on-ZIP** sichert die Add-on-Dateien getrennt von den
   Benutzerdaten. Auf dem Zielgeraet ueber Kodis **Aus ZIP-Datei installieren**
   installieren; danach die passende JSON-Sicherung importieren. Die ueblichen
   Kodi-Abhaengigkeiten muessen weiterhin verfuegbar sein.

Das Ziel direkt unter **Sichern und Wiederherstellen -> Sicherungsziel einrichten**
konfigurieren. Dieselben Werte sind auch in der Einstellungsrubrik **Sichern und
Wiederherstellen** verfuegbar. Abgebrochene Eingaben lassen die bisherigen Werte
unveraendert; nach einer Aktion erscheint wieder das Import-/Export-Menue.

- **Ordner / synchronisierter Cloud-Ordner**: einen beschreibbaren Kodi-Pfad
   oder einen echten lokalen Sync-Ordner der Google-Drive-, OneDrive- oder
   Nextcloud-App waehlen. Der externe Client uebernimmt den Upload/Download.
   Ein reines `plugin://`-Verzeichnis eines Cloud-Add-ons ist kein beschreibbarer
   Dateipfad. Auf Android TV ist gegebenenfalls ein separater Sync-Client oder
   ein ueber SMB erreichbarer Sync-Ordner auf einem anderen Geraet erforderlich.
- **HTTPS-WebDAV (z.B. Nextcloud)**: bestehenden Sicherungsordner erstellen,
   seine HTTPS-WebDAV-Adresse, Benutzername und ein eigenes App-Passwort aus
   den Nextcloud-Sicherheitseinstellungen eintragen. Beispieladresse:
   `https://cloud.example/remote.php/dav/files/USERNAME/GerXStream/`.
   Das App-Passwort ausschliesslich direkt in Kodi eingeben. Die Zugangsdaten
   werden in Kodis lokalen Einstellungen gespeichert, nicht verschluesselt.
   Selbstsignierte/ungueltige Zertifikate und HTTP werden nicht akzeptiert.

Zum Abgleichen auf Geraet A exportieren, den Cloud-Upload abschliessen lassen
und auf Geraet B dieselbe Sicherung importieren. Der Import ersetzt die
ausgewaehlten Listen nach Rueckfrage. Es gibt **keine automatische beidseitige
Synchronisierung, Zusammenfuehrung oder Konfliktaufloesung**. Eindeutige
Snapshot-Dateinamen verhindern ein gegenseitiges Ueberschreiben beim Export.
Alte Gesamtsicherungen ohne Historie/Gesehen-Status bleiben importierbar.

Google Drive und OneDrive haben **keine direkte OAuth-Anmeldung**;
dafuer waeren registrierte Client-Anwendungen und zusaetzliche Anmeldung noetig.
Ein interner FTP-Server ist nicht enthalten: Kodi bietet Dateizugriff als
Client, keinen durch dieses Add-on verwalteten FTP-Server. Fuer private
Sicherungen sind HTTPS-WebDAV oder ein vorhandener geschuetzter Dateiserver
vorzuziehen; unverschluesseltes FTP nicht fuer Kontensicherungen verwenden.

Die Sicherungsfunktionen werden erst beim Aufruf geladen und arbeiten nur
auf Anforderung. Sie fuegen dem Kodi-Start und der laufenden Wiedergabe
keinen Cloud-Polling-Job hinzu. Export/Import kann waehrend des jeweiligen
Aufrufs fuer Dateizugriff, ZIP-Kompression und Netzwerkuebertragung Zeit brauchen.

Geraetepruefung am 09.10.2026: Der lokale Teststand 1.0.37 ist auf Kodi4
installiert, nicht oeffentlich veroeffentlicht. Der vorhandene Carrie-Favorit
oeffnet direkt den Filmpalast-Serienordner; dessen Episodenordner zeigt acht
Folgen. Wiedergabe und Stop oberhalb von 90 Prozent wurden geprueft: identischer
Episodenordner, identische Auswahlposition und gespeicherte Gesehen-Markierung.
Das bestaetigt diesen Ablauf auf dem getesteten Geraet, nicht alle Quellen/Skins.
Cloud-Uebertragungen einschliesslich optionaler Konten wurden automatisiert mit
simuliertem Transport geprueft; ein echter Cloud-Kontotest steht noch aus.

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
