
<p align="center">
  <img src="resources/clearlogo.png" alt="GerXStream" width="420">
</p>

<h1 align="center">GerXStream für Kodi</h1>
<p align="center"><b>Eine Suchmaschine. Alle Quellen. Ein Klick.</b></p>

***

## Warum GerXStream?

Kein Wischen durch zehn Apps, kein Tab-Chaos im Browser. GerXStream durchsucht
alle angebundenen Webseiten gleichzeitig — oder gezielt einzeln — und liefert
Filme, Serien und Streams direkt in die gewohnte Kodi-Oberfläche.

- 🔎 **Eine Suche, alle Quellen** – die globale Suche fragt alle Site-Plugins parallel ab
- 🎬 **Filme & Serien** – vollständige Metadaten (Cover, Beschreibung, Bewertung, Cast, Erstausstrahlung, Serienstatus)
- ⭐ **Favoriten mit Ordnern** – eigene Ordner und Unterordner zum Sortieren der Favoriten (in Arbeit, kommt mit einer der nächsten Versionen)
- 🧩 **Site-Plugins** – jede Quelle ist ein eigenständiges, austauschbares Modul
- 🛡️ **Sicherheit eingebaut** – striktes URL-Routing, TLS-Prüfung aktiv, kein `eval()` auf Fremddaten
- 🇩🇪 **Deutsch zuerst** – Oberfläche und Fehlermeldungen auf Deutsch, Englisch als Fallback
- ⚡ **Kodi 22 „Piers"** als Zielplattform, Kodi 21 „Omega" läuft als Fallback mit

## Los geht's

Installationsschritte, Voraussetzungen und Hinweise zur Datenübernahme stehen
ausführlich in [INSTALL.md](INSTALL.md). Die Kodi-Quelle wird nach erfolgreicher
GitHub-Actions-Auslieferung ueber GitHub Pages bereitgestellt:
`https://flowinthefluid.github.io/gerxstream/repo/`.
Die Repository-ZIP heisst `repository.gerxstream-1.0.8.zip`; GerXStream selbst
hat die Version **1.0.32**. Updates erfolgen ueber Kodis Add-on-Verwaltung.
Wer noch eine ältere xStream-Installation nutzt, kann direkt zu
GerXStream wechseln: Einstellungen und Favoriten werden beim ersten Start automatisch
übernommen, sofern xStream noch installiert ist.

## Zufallsfilme und Kategorien

**Zufaellige Filme** oeffnet zuerst die Auswahl **Random**, **Nach Genre** oder
**Nach Filmproduktion** (zum Beispiel Walt Disney Pictures oder Pixar).
Unter **Einstellungen > Zufaellige Filme** stehen erlaubte Genres fuer Random,
die Anzahl (Standard 250) und eine IMDb-Mindestwertung. Bei mehreren Genres wird
ein Film ausgeschlossen, sobald er einem abgewahlten Genre angehoert. Die
gezielte Genre-/Firmenauswahl ignoriert diese Genre-Ausschluesse.

Die Zufallsauswahl nutzt den datierten, erschienenen TMDB-Filmkatalog ohne
Erwachsenenmarkierung seit 1800, nicht nur die populaersten 10.000 Titel.
Datumsbereiche werden aufgeteilt, um das TMDB-Limit von 500 Seiten einzuhalten.
Filme ohne bekanntes Erscheinungsdatum fehlen; Streaming-Verfuegbarkeit wird
erst beim Klick ueber die aktivierten Quellen gesucht.

Unter **Einstellungen > Kategorien** gibt es getrennte Mindestwerte fuer IMDb,
TMDB und TMDB-Stimmen. **IMDb** verwendet echte OMDb-Wertungen und erfordert
einen eigenen OMDb-API-Schluessel unter **TMDB**. Fehlende Wertungen werden bei
aktivem IMDb-Filter ausgeschlossen. Erste Abfragen koennen dauern und das
Tageskontingent verbrauchen. Random prueft maximal 1000 Kandidaten; kleine
Kataloge oder starke Filter koennen weniger als die gewuenschte Anzahl liefern.
Kategorien filtern seitenweise und behalten die naechste Seite bei.

Der fruehere Punkt **Alle** heisst jetzt **Aktuelle Trends (Filme und Serien)**:
Er kombiniert die woechentlichen TMDB-Trends, nicht den gesamten Katalog.
**Charts** trennt Filme und Serien. Die bisherigen **Sammlungen** stehen unter
**Themen**. Themen beruhen auf TMDB-Schlagwoertern, nicht auf redaktionell
kuratierten Titellisten: **Wildnis als Schauplatz** kann auch Horror und Dramen
enthalten; **Natur- und Tierdokumentationen** verlangt zusaetzlich das Genre
Dokumentarfilm. Ohne exakt passendes Schlagwort gibt es keine allgemeine
Popularitaetsliste als Ersatz.

**Mediatheken** bietet direkte Verknuepfungen zu ARD, ZDF, 3sat, arte, phoenix,
den Dritten, KiKA, funk und weiteren oeffentlich-rechtlichen Angeboten ueber
MediathekViewWeb sowie die eigenen ARD-/arte-Quellen. Diese Verknuepfungen sind
standardmaessig unabhaengig von den Suchquellenschaltern sichtbar; in den
Kategorie-Einstellungen laesst sich das abschalten. Globale Suche und
Quellenmenues behalten ihre bisherigen Schalter. Bewertungsfilter gelten nur
fuer den TMDB-Katalog, nicht fuer die Mediatheken oder Personenlisten.

### Strukturierte Mediatheken

ARD oeffnet redaktionelle Bereiche und Serien-/Sendungsordner; ARTE zeigt auch
Kollektionen und deren Themenbereiche. Bei MediathekViewWeb fuehren Sender zu
neuen Videos, Themenfiltern und einer auf den Sender begrenzten Suche. Die
Themenfilter sind Suchbegriffe, keine vom Sender vergebenen Genres.

Netzkino und **Rocket Beans TV** stehen ebenfalls unter Mediatheken.
Rocket Beans bietet neue Folgen sowie Sendungen A-Z mit Staffeln und
Seitennavigation. Freie Videos starten ueber das offizielle Kodi-Add-on
**YouTube**; fehlt es, wird dessen Installation angeboten.

Unter **Einstellungen > Konten > Rocket Beans TV** koennen E-Mail-Adresse
und Passwort eingegeben und die Anmeldung gestartet werden. Ein optionaler
Zwei-Faktor-Code wird direkt in Kodi abgefragt. Nach erfolgreicher Anmeldung
erscheint **Meine Abos**. Das Passwort wird dann entfernt, der Sitzungstoken
bleibt lokal bis zur Abmeldung oder bis zum Ablauf gespeichert. Kodi verschluesselt
diese Einstellungen nicht. Bei abgelaufener Sitzung ist erneutes Anmelden noetig.
Die echte Konto-Anmeldung ist noch nicht mit einem Testkonto bestaetigt;
ein erforderliches Browser-Captcha kann die Anmeldung verhindern.

Supporter-Videos ohne freien YouTube-Stream sind noch nicht abspielbar.
Red Bull TV ist noch nicht eingebunden; ein funktionierender Katalog samt
Wiedergabe muss vor der Aufnahme bestaetigt werden. DRM-, Konto- und
Regionalsperren werden nicht umgangen.

## Wie es funktioniert

Jede angebundene Webseite steckt in einem eigenen Site-Plugin unter [sites/](sites/).
Diese Plugins liefern nur die Verknüpfung zur jeweiligen Quelle — der Inhalt der
Webseiten selbst steht in keinerlei Bezug zu GerXStream oder den Entwickler:innen.
Umfang und Angebot werden laufend erweitert und gepflegt.

## Mitentwickeln

GerXStream läuft ausschließlich unter Python 3. Quellcode, Tickets und Releases
liegen im [GitLab-Repository](https://gitlab.com/gerxstream/gerxstream).

***

Lizenz: GPL-3.0-only, siehe [license.txt](license.txt).

***

## Livestreams (neu)

Ein eigener, verschiebbarer Hauptmenüpunkt **Livestreams** mit fünf Bereichen:

- **Fernsehen** — Sender nach Ländern und nach Genre; M3U-/XMLTV-Export für den
  PVR IPTV Simple Client, in-Addon EPG „jetzt/danach".
- **Sport & E-Sport**, **Social Media** (YouTube/Twitch über deren offizielle
  Kodi-Addons), **Wetter** (Open-Meteo keyless / optional OpenWeatherMap),
  **Webcams** (öffentliche, rechtlich belegte Kameras; Länder→Städte + Themen
  wie Berge, Tiere, Vögel, Strände, Piers, Parks, Verkehr).
- **Rabbithole** — zufällige Webcam ohne Wiederholung; „Zufällig (250)".

### Konfiguration (Einstellungen)

- **Menü anpassen**: sichtbare Bereiche, Länder-Whitelist/Blacklist, Genres,
  Rabbithole-Kategorien.
- **Erwachsene Inhalte (NSFW)**: ein einziger, expliziter Schalter (`showAdult`).
  NSFW erscheint ausschließlich hierüber — nie implizit über eine Genre-/
  Kategoriewahl. Fehlt einem Inhalt die Markierung, bleibt er bei ausgeschaltetem
  Schalter unsichtbar (fail-closed).
- **EPG**: XMLTV-Quellen (URLs, gzip/xz), Vorschaufenster.
- **Wetter**: Stadt/Städte, Einheiten, optionaler OpenWeatherMap-Key.
- **Social Media**: YouTube/Twitch ein/aus, optionale eigene API-Keys, Buttons
  zu den Addon-Einstellungen (Konto/Login).
- **Daten & Export**: Aktualisierung, „IPTV-Simple-Einrichtung anzeigen",
  „Quellen prüfen".

### IPTV Simple + Fehlerbehebung

Der Service schreibt `playlist.m3u` und `guide.xml` nach
`special://profile/addon_data/plugin.video.gerxstream/livestreams/`; den Pfad
zeigt der Button „IPTV-Simple-Einrichtung anzeigen". Den IPTV Simple Client auf
diese lokalen Dateien konfigurieren.

### Rechterahmen

Es werden nur Inhalte mit belegter Rechtelage gezeigt (offizielle Quelle oder
`rights_evidence_url`); DRM/Login/Geo werden ehrlich markiert und nicht umgangen.
Kein Auffinden ungesicherter fremder Kameras, keine Grauzonen-Aggregation.
