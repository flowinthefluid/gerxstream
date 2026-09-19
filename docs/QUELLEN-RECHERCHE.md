# Quellen-Recherche: Nutzerwunschliste

Der Nutzer hat eine lange Liste gewuenschter Quellen genannt (deutsche
Streaming-Portale, Anime-Seiten, Archiv-Kategorien). Dieses Dokument haelt
fest, was daraus aufgenommen wurde, was bereits abgedeckt war und was aus
konkretem, belegtem Grund nicht aufgenommen wurde. Ziel: niemand muss diese
Recherche wiederholen.

## 1. Neu aufgenommen (9 Quellen)

| Quelle | Datei | Sprache | Besonderheit |
|---|---|---|---|
| media.ccc.de | `sites/mediaccc.py` | de | Offene API, direkte Streams |
| ARD Mediathek | `sites/ardmediathek.py` | de | Offene API, direkte Streams |
| Arte | `sites/arte.py` | de | Offene API, direkte Streams |
| KinoKing | `sites/kinoking.py` | de | HTML-Scraping, Hoster-Kette |
| Anime Toast | `sites/animetoast.py` | de | WordPress-REST-API |
| Anime-Loads | `sites/animeloads.py` | de | DDoS-Guard, teilweise verifiziert |
| Anime-Stream | `sites/animestream.py` | de | Cloudflare, teilweise verifiziert |
| KayoAnime | `sites/kayoanime.py` | en | Verlinkt Google-Drive-Ordner |
| 4anime | `sites/anime4.py` | en | Verschluesselter Player, serverseitig aufgeloest |

Zusaetzlich: `sites/internetarchive.py` um eine deutschsprachige Auswahl
(Filme, Anime, Dokumentationen, Stummfilme auf Deutsch) erweitert, statt eine
neue Quelle daraus zu machen - archive.org war bereits abgedeckt.

## 2. Bereits abgedeckt, nur die Standard-Domain repariert

27 der genannten Adressen sind keine neuen Quellen, sondern zusaetzliche
Domains fuer bereits vorhandene Plugins (z. B. `w11.kinox.to`,
`www21.kinox.to` fuer `sites/kinox.py`). Ein Erreichbarkeitstest ergab dabei,
dass 12 der 27 Standard-Domains selbst tot oder falsch waren - siehe den
Commit "Standard-Domains auf geprueft erreichbare Werte setzen". Details dort,
nicht hier wiederholt.

## 3. Login-gated, kein Scraping-Ziel

**proxer.me** — bestaetigt: die Anime-Liste liefert ohne Login ein
Anmeldeformular ("Eingeloggt bleiben?", "Registrieren", "Passwort
vergessen"), kein einziger Eintrag ist ohne Konto sichtbar. Das ist kein
Bot-Schutz, der sich umgehen liesse (siehe `protection.py`), sondern ein
echtes Zugangsschranken-Modell. Eine Anbindung braeuchte Nutzername/Passwort
pro Person und eine eigene Sitzungsverwaltung - deutlich groesserer Umfang
als die uebrigen Quellen und nicht mit den bestehenden Mitteln umsetzbar.

## 4. Technisch nicht ohne Browser-Automatisierung erreichbar

Diese Seiten rendern ihren gesamten Inhalt clientseitig (Single-Page-App);
der servergelieferte HTML-Code enthaelt keine Filme/Serien-Daten, nur ein
leeres Geruest plus ein JavaScript-Bundle. `cRequestHandler` fuehrt kein
JavaScript aus, kann diese Seiten also grundsaetzlich nicht lesen - das ist
kein Bot-Schutz-Problem, sondern eine Frage der Architektur. Eine Anbindung
braeuchte etwas wie eine eingebettete Browser-Engine oder einen externen
Rendering-Dienst; beides sprengt den Rahmen eines Kodi-Add-ons.

| Domain | Befund |
|---|---|
| ssflix.pro | React/Vue-SPA-Geruest, 0 Links im Server-HTML |
| xtubeflix.com | dieselbe SFlix-Vorlage wie ssflix.pro, dasselbe Ergebnis |
| webflixs.com | dieselbe SFlix-Vorlage, WordPress-Fingerprint traf nur auf eingebundene Bibliotheken zu, nicht auf die Katalogseiten selbst |
| getmoviez.cc | Laravel+Vue-App (erkennbar an `app-*.js`/`app-*.css`-Bundles), `?lang=de` vorhanden, aber kein Server-HTML mit Filmdaten; geratene API-Pfade (`/api/movies` etc.) lieferten 404 |
| movie-paradise.tv | Seite zeigt selbst "Sorry, you have Javascript Disabled!" auf jeder Unterseite, inkl. der vom Nutzer genannten `?page_id=1005`. Dort zudem Live-Sport-Streams (Bundesliga, Champions League) - lizenzierte Live-Uebertragungen, eine andere Kategorie als On-Demand-Portale |
| streamkiste.sx / streamkiste.bid | identisches SPA-Geruest wie ssflix.pro (6,3 KB, dieselbe Struktur) |
| anime.uniquestream.net | Nuxt.js-SPA (`window.__NUXT__` bestaetigt), Nuxt-Payload enthaelt nur Seiten-Metadaten, keine Katalogdaten; geratene API-Pfade ergebnislos |

**justmoviz.net** ist ein Sonderfall: technisch erreichbar (WordPress,
serverseitig gerendert), aber inhaltlich keine Streaming-Quelle. Die
Filmseiten sind "Rent/Buy"-Affiliate-Seiten ("Watch Full Movie Detail" ist
nur eine Ueberschrift) ohne Player oder Hoster-Verweis - gegengeprueft an
einem unveroeffentlichten (Spider-Man: Brand New Day) und einem bereits
veroeffentlichten Titel (The Odyssey), beide ohne jeden Streaming-Link.

## 5. Domain nicht sicher identifizierbar

**Flixi** und **XCineRU** standen ohne eindeutige Domain auf der Liste. Ein
Rateversuch (`flixi.cc`) traf auf eine themenfremde chinesische Seite -
falsch geraten haette einen Nutzer auf die falsche Adresse geschickt, deshalb
absichtlich nicht weiter geraten. XCineRU ist vermutlich ein weiterer Domain-
Alias des bereits vorhandenen `sites/xcine.py` (wie `burningseries.ac` und
`bs.cine.to` Aliase desselben Netzwerks sind), aber ohne bestaetigte Adresse
nicht sauber zuzuordnen.

**Ruecksprache noetig:** die genaue Adresse fuer beide.

## 6. Bewusst nicht aufgenommen: Erwachseneninhalte

Eine Gruppe von 14 genannten Seiten (hentai.tv, hanime.tv, haho.moe,
hentaibros.net, hentaimama.io, hentaiocean.com, hentaverse.com, hstream.moe,
muchohentai.com, oppai.stream, henvids.com, rule34video.com, sakuracircle.com,
underhentai.net) wurde nicht umgesetzt. Auf mehreren dieser Seiten - allen
voran rule34video.com - ist die Darstellung von Figuren, die minderjaehrig
wirken, in sexuellem Kontext Standardbestand. Eine Such- und
Streaming-Anbindung dorthin baue ich nicht.

## 7. Bot-Schutz: wie er jetzt gehandhabt wird

Zwei der neuen Quellen (Anime-Loads, Anime-Stream) stehen hinter DDoS-Guard
bzw. Cloudflare. Dafuer wurde `resources/lib/handler/protection.py`
geschaffen: eine im Browser bestaetigte Sitzung (Cookie + User-Agent) laesst
sich pro Quelle hinterlegen und wird automatisch wiederverwendet und bei
Bedarf ueber einen optionalen FlareSolverr-Dienst erneuert. Details und
Testergebnisse in den zugehoerigen Commits.
