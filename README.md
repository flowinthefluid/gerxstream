
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
ausführlich in [INSTALL.md](INSTALL.md). Wer noch eine ältere xStream-Installation
nutzt, kann direkt zu GerXStream wechseln: Einstellungen und Favoriten werden beim
ersten Start automatisch übernommen, sofern xStream noch installiert ist.

## Wie es funktioniert

Jede angebundene Webseite steckt in einem eigenen Site-Plugin unter [sites/](sites/).
Diese Plugins liefern nur die Verknüpfung zur jeweiligen Quelle — der Inhalt der
Webseiten selbst steht in keinerlei Bezug zu GerXStream oder den Entwickler:innen.
Umfang und Angebot werden laufend erweitert und gepflegt.

## Mitentwickeln

GerXStream läuft ausschließlich unter Python 3. Wer eine neue Quelle anbinden
oder an der Oberfläche mitbauen möchte, findet den technischen Überblick in
[docs/CODING-PLAN.md](docs/CODING-PLAN.md).

***

Lizenz: GPL-3.0-only, siehe [license.txt](license.txt).

