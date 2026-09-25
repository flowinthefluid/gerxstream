
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
ausführlich in [INSTALL.md](INSTALL.md). Die veröffentlichte Kodi-Quelle wird über
GitLab Pages bereitgestellt; die aktuelle Adresse steht im GitLab-Projekt unter
**Deploy > Pages**. Wer noch eine ältere xStream-Installation nutzt, kann direkt zu
GerXStream wechseln: Einstellungen und Favoriten werden beim ersten Start automatisch
übernommen, sofern xStream noch installiert ist.

## Wie es funktioniert

Jede angebundene Webseite steckt in einem eigenen Site-Plugin unter [sites/](sites/).
Diese Plugins liefern nur die Verknüpfung zur jeweiligen Quelle — der Inhalt der
Webseiten selbst steht in keinerlei Bezug zu GerXStream oder den Entwickler:innen.
Umfang und Angebot werden laufend erweitert und gepflegt.

## Mitentwickeln

GerXStream läuft ausschließlich unter Python 3. Quellcode, Tickets und Releases
liegen im [GitLab-Projekt](https://gitlab.com/gerxstream/gerxstream).

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
