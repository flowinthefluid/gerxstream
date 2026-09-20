# Quellenstatus und Nicht-Einbaugruende

Stand: 2026-09-20

Diese Datei ist die getrennte Liste fuer Domains aus der Nutzerwunschliste, die
nicht als neues Site-Plugin aufgenommen werden. Sie ergaenzt die detaillierten
Funde in `QUELLEN-RECHERCHE.md` und `LIVE-UND-BACKLOG.md`.

## Bereits vorhanden oder im aktuellen Arbeitsstand

| Angebot | Status |
|---|---|
| ARD, ZDF, 3sat, arte, phoenix, ORF, RBB, WDR und weitere oeffentlich-rechtliche Sender | Bereits ueber `mediathekviewweb.py`; ARD und Arte zusaetzlich ueber eigene APIs. Kein Doppel-Plugin erforderlich. |
| media.ccc.de, archive.org, anime-stream.to, anime-loads.org, proxer.me | Bereits als Site-Plugin vorhanden. Proxer verwendet nur eigene, vom Nutzer eingegebene Zugangsdaten. |
| doku-streams.com, dokustreams.de, videogold.de | Bereits als getrennte Unterquellen in `dokus4me.py` vorhanden. |
| flash-moviez.ucoz.org, flixitv-stream.eu | Als neue Site-Plugins im Arbeitsbaum und in den Einstellungen registriert. Vor einem Release muessen die unversionierten Dateien, ihre Bilder und die Parser gegen Kodi getestet werden. |
| burningseries.ac/.cx/bs.cine.to, w11.kinox.to/kinoz.to, hdfilme.to/.cafe/.bid, streamcloud.download/.watch | Echte Domain-Aliase bestehender Quellen; Auswahl erfolgt als Domainwechsel, nicht als Doppel-Plugin. |

## Technisch derzeit nicht als Kodi-Quelle nutzbar

| Domain | Exakte Ursache |
|---|---|
| dailyme.de | Der Katalog ist im Server-HTML sichtbar, die Wiedergabe aber nicht: Der oeffentliche Player laedt eine JavaScript-Anwendung, registriert eine Sitzung und holt pro Clip einen Zugriffsschluessel. Es gibt keine dokumentierte, direkt an Kodi uebergabefaehige Stream-API. Einen kommerziellen Webplayer nachzubauen oder dessen Sitzungsmechanik zu umgehen ist kein Site-Plugin. |
| mediathekdirekt.de | `good.json` liefert direkte URLs, ist aber nur als ungefilterte Gesamtliste verfuegbar und war bei der Gegenpruefung 69.630.551 Byte gross. Ohne serverseitige Suche oder paginierte API muesste Kodi fuer jede Anzeige bzw. Suche rund 70 MB laden und parsen. Zudem ist der Inhalt bereits durch MediathekViewWeb abgedeckt. |
| getmoviez.cc, ssflix.pro, xtubeflix.com, webflixs.com, streamkiste.sx, streamkiste.bid, anime.uniquestream.net | Single-Page-Anwendungen: Das servergelieferte HTML enthaelt keinen Katalog. Kodi-Python fuehrt kein JavaScript aus; ohne oeffentliche Daten-API oder Betreiber-Export gibt es keinen belastbaren Parser. |
| movie-paradise.tv | Abhaengig von JavaScript und laut eigener Seite ohne JavaScript nicht nutzbar; ausserdem Live-Angebot, kein reines VoD-Portal. |
| filmfans.org, hd-area.tv, serienfans.org, moviefans.to | Interaktive Cloudflare-Challenge. HTTP 403 beweist nicht, dass die Seite tot ist, liefert aber keinen automatisierbar lesbaren Katalog. Es wird kein Challenge-Bypass eingebaut. |
| filmfrei24.com | Verbindungs-Timeout bei der Gegenpruefung; kein erreichbarer Ausgangspunkt fuer einen Parser. |
| dokus4.me | Zertifikats-/SNI-Fehler; selbst mit ignoriertem Zertifikat kam nur eine generische Statusseite statt eines Katalogs. TLS wird dafuer nicht abgeschaltet. |
| flixi | Keine eindeutige Domain. Der getestete Kandidat `flixi.cc` war themenfremd; ohne korrekte Adresse wird keine Rate-Domain eingebaut. |
| tierwelt-live.de | Private, werbefinanzierte API mit VAST-Werbeablauf und nicht dokumentierten UUID-Endpunkten. Das waere Reverse Engineering einer kommerziellen Plattform, kein HTML-Scraper. |
| k-tv.org | Die Mediathek bindet Drittanbieter-Videos, insbesondere YouTube und Vimeo, ein. Ohne eigenes oeffentliches Katalog-/Wiedergabe-API waere ein Plugin lediglich ein zweiter, fragiler YouTube/Vimeo-Wrapper. |
| filmfriend.ch | Bibliotheks- bzw. Institutionslogin ist zwingend. Eine sichere Anbindung braucht eine offiziell dokumentierte Nutzer-Authentifizierung pro Bibliothek; es werden keine fremden oder geteilten Zugangsdaten verwendet. |

## Keine echte oder keine eigenstaendige Streaming-Quelle

| Domains | Exakte Ursache |
|---|---|
| megakino.org, kkiste.eu, kinokiste.club, kinokiste.eu, movie2k.ag, movie4k.sx, streamkiste.sx, streamkiste.life, hdfilme.me, movie2k.ch | Domain-Squatting-Netzwerk: gleicher JavaScript-Rahmen ohne eigenen Katalog. HTTP 200 oder ein bekannter Name reichen nicht als Quelle. |
| streamcloud.my | Heute Gluecksspielseite, keine Videoquelle. |
| streamcloud.world, streamcloud.mom, kinokistetv.cv, streamkiste.autos, diverse `*.bitbucket.io` | SEO-/Markenkoeder ohne eigenen Film- oder Serienkatalog. |
| watchhub.work/watchserieshd, flixnet.to, filmpalast-to.net | Weiterleitung auf Werbung, Tracking oder SEO-Inhalte statt auf einen Videoanbieter. |
| doksite.de, filmportal.de, moviepilot.de, heftfilme.com | Metadaten-, Kritiken- oder Affiliate-Angebote; kein abspielbarer Vollvideo-Katalog. |
| welt.de, n-tv.de, bpb.de, andererseits.org, alexanderstreet.com | Nachrichten-, Text- oder institutionelle Lizenzangebote; kein frei nutzbarer VoD-Katalog fuer ein Site-Plugin. |
| alliance4creativity.com | Anti-Piraterie-Koalition, keine Streaming-Quelle. |
| x-oo.com | Vorwiegend Flash-/Browserspiele; die wenigen Videos sind Fremdeinbettungen. |
| rumble.com, odysee.com | Allgemeine Videoplattformen ohne den geforderten kuratierten deutschsprachigen VoD-Katalog. |

## Aliase und Klone: kein zusaetzliches Plugin

Die folgenden Domainpaare wurden als ein Betreiber bzw. als Weiterleitung
identifiziert und duerfen nicht doppelt im Hauptmenue erscheinen:

- `burningseries.ac`, `burningseries.cx`, `bs.cine.to`
- `w11.kinox.to`, `kinoz.to`, `www21.kinox.to`
- `hdfilme.to`, `hdfilme.cafe`, `hdfilme.bid`
- `xcine.hair`, `xcine.online`
- `streamcloud.download`, `streamcloud.watch`
- `kinokiste.eu` -> `kinokiste.club`
- `streamkiste.taxi` -> `streamkiste.bid`
- `kkiste-io.skin` -> `kkiste-io.ink`
- `megakino19.com` -> `megakino20.com`
- `7megakino.lol` -> `8megakino.com`
- `streamworld.to`, `streamworld.co`

Gleichnamige, aber technisch unterschiedliche Betreiber werden nur dann als
separate Quelle aufgenommen, wenn ein eigener serverseitiger Katalog und ein
direkter, rechtlich unbedenklicher Wiedergabepfad nachgewiesen sind.

## Bewusst nicht eingebaut

| Gruppe | Grund |
|---|---|
| Alle unter den Ueberschriften **Hentai** und **XXX** der Nutzerliste genannten Domains | Auf einem erheblichen Teil dieser Angebote ist sexualisierte Darstellung von Figuren, die minderjaehrig wirken koennen, regulaerer Bestandteil. Deshalb keine Suche, keine Wiedergabe und auch keine Warteliste dafuer. |
| bugmenot.com | Geteilte, fremde Zugangsdaten werden weder gesucht noch automatisiert eingesetzt. Bestehende Login-Felder sind ausschliesslich fuer eigene Zugangsdaten. |
| 4everproxy.com, hide.me, proxfree.com, proxysite.com, anonymouse.org, unblockvideos.com, stopcensoring.me sowie oeffentliche SOCKS-/VPN-Listen | Kein Proxy- oder DNS-Sperren-Umgehungsdienst im Addon. Oeffentliche Proxies koennen Verkehr und Zugangsdaten manipulieren; Zugriffsbeschraenkungen werden nicht umgangen. |
| thepiratebay.org, xrel.to, PreDB-/Scene-Datenbanken, Torrent-, FTP- und Release-Suchen | Kein Torrent-, Release- oder Filesharing-Client im Addon. Das ist weder ein VoD-Katalog noch ein sicherer Wiedergabeweg. |

## Live-Angebote: separat, nicht als VoD eingebaut

Die Domains aus den Abschnitten **Sport**, **Live-TV** und **Live Kino** der
Nutzerliste werden nicht stillschweigend als VoD-Scraper behandelt. Sport-
Aggregatoren sind zeitkritische Einbettungsketten; viele enthalten
offensichtlich lizenzpflichtige Live-Uebertragungen. Fuer Live-TV ist
`www.online-tv.de` der einzige bisher dokumentierte Kandidat mit direkten
HLS-Adressen; seine Umsetzung braucht eine eigene, opt-in Live-TV-/M3U-/XMLTV-
Funktion. Details stehen in `LIVE-UND-BACKLOG.md`.

## Vollstaendiger Abgleich der zuletzt gesendeten Domainliste

Die Tabelle ist absichtlich domaingenau. `Vorhanden` bedeutet, dass kein
zweites Plugin angelegt wird; es ist keine Aussage ueber die dauerhafte
Erreichbarkeit oder die Lizenz eines Drittangebots. `Nicht aufgenommen`
benennt den konkreten Grund.

| Domain | Ergebnis |
|---|---|
| filmpalast.to | Vorhanden: `sites/filmpalast.py`; keine DNS-, Proxy- oder Sperrenumgehung. |
| cine.to | Vorhanden: `sites/xcine.py`. |
| getmoviez.cc | Nicht aufgenommen: SPA ohne serverseitigen Katalog. |
| huhu.to | Vorhanden: `sites/huhu.py`. |
| kinokiste.eu | Nicht aufgenommen: Weiterleitung auf den 6.326-Byte-Squat `kinokiste.club`. |
| megakino.org | Nicht aufgenommen: 6.326-Byte-Squat, kein eigener Katalog. |
| bs.cine.to | Alias von `burningseries`; kein Doppel-Plugin. |
| burningseries.ac | Alias von `burningseries`; kein Doppel-Plugin. |
| burningseries.cx | Alias von `burningseries`; kein Doppel-Plugin. |
| hdfilme.me | Nicht aufgenommen: Squat ohne Katalog. |
| hdfilme.cafe | Alias der vorhandenen Quelle `hdfilme_1`. |
| hdfilme.to | Alias der vorhandenen Quelle `hdfilme_1`. |
| kinoger.com | Vorhanden: `sites/kinoger.py`. |
| kinoger.to | Alias von `kinoger.com`; kein Doppel-Plugin. |
| kinokiste.club | Nicht aufgenommen: 6.326-Byte-Squat ohne Katalog. |
| streamkiste.sx | Nicht aufgenommen: SPA-Geruest ohne Server-Katalog. |
| kkiste.eu | Nicht aufgenommen: Squat ohne Katalog. |
| kinoking.cc | Vorhanden: `sites/kinoking.py`. |
| streamcloud.download | Vorhanden: `sites/streamcloud.py`. |
| 8megakino.com | Vorhanden: `sites/megakino.py`. |
| filmo.to | Nicht aufgenommen: englischsprachige Aggregatoroberflaeche ohne Deutschland-Fokus. |
| hd-filme.lol | Vorhanden: eigenstaendige `hdfilme.py`-Quelle. |
| kinoz.to | Alias von `kinox`; kein Doppel-Plugin. |
| w11.kinox.to | Alias von `kinox`; kein Doppel-Plugin. |
| kkiste-io.ink | Nicht aufgenommen: Cloudflare-Challenge, kein automatisierbarer Katalog. |
| megakino.foo | Nicht aufgenommen: abweichender Betreiber; kein belastbarer, direkt uebergabefaehiger Wiedergabepfad verifiziert. |
| megakino.vip | Nicht aufgenommen: kein stabiler, pruefbarer Betreiberbezug. |
| megakino20.com | Alias von `megakino19.com`; kein zweites Plugin. |
| movie2k.cx | Vorhandenes `sites/movie2k.py` ist die einzige passende Quelle; der alte `.ch`-API-Pfad ist nicht als neue Quelle zu duplizieren. |
| movie4k.sx | Nicht aufgenommen: Squat ohne Katalog. |
| streamkiste.bid | Nicht aufgenommen: SPA-Geruest ohne Server-Katalog. |
| streamkiste.taxi | Alias von `streamkiste.bid`. |
| movie2k.ag | Nicht aufgenommen: TLS-Zertifikat/SNI passt nicht zum Host und kein Katalog verifiziert. |
| filmpalast-to.net | Nicht aufgenommen: SEO-/Werbeweiterleitung, nicht filmpalast.to. |
| flixnet.to | Nicht aufgenommen: Tracking-Weiterleitung. |
| watchhub.work/watchserieshd | Nicht aufgenommen: Werbe-/Schadweiterleitung. |
| vumoo.live | Nicht aufgenommen: englischsprachig, kurzlebige Mirror-Marke ohne Deutschland-Fokus. |
| mediathekviewweb.de | Vorhanden: `sites/mediathekviewweb.py`. |
| mediathekdirekt.de | Nicht aufgenommen: 70-MB-Gesamt-JSON ohne Pagination/Suche; Inhalt bereits abgedeckt. |
| streamworld.to | Nicht aufgenommen: gleicher Betreiber wie `.co`; kein zweites Plugin. |
| streamworld.co | Nicht aufgenommen: gleicher Betreiber wie `.to`; kein zweites Plugin. |
| couchtuner.fashion | Nicht aufgenommen: englischsprachige FMovies-Vorlage ohne Deutschland-Fokus. |
| ww2.fmovies.cab | Nicht aufgenommen: englischsprachige FMovies-Vorlage ohne Deutschland-Fokus. |
| hdfilme.bid | Alias der vorhandenen Quelle `hdfilme_1`. |
| kkiste-io.skin | Alias von `kkiste-io.ink`. |
| videogold.de | Vorhanden als Unterquelle in `sites/dokus4me.py`. |
| heftfilme.com | Nicht aufgenommen: Kritik-/Affiliate-Seite, kein Vollvideo-Katalog. |
| schoener-fernsehen.com | Nicht aufgenommen: Live-TV; separater Live-Umfang. |
| moviefans.to | Nicht aufgenommen: interaktive Cloudflare-Challenge. |
| flash-moviez.ucoz.org | Im Arbeitsbaum als `sites/flashmoviez.py`; fuer Release noch versionieren und in Kodi testen. |
| hd-area.tv | Nicht aufgenommen: interaktive Cloudflare-Challenge. |
| kellerkino.com | Nicht aufgenommen: eigener Katalog, aber nur anonyme Drittanbieter-Hoster; Nutzungs-/Rechtebasis nicht verifizierbar. |
| streamkiste.al | Nicht aufgenommen: englischsprachige Template-Seite ohne Deutschland-Fokus. |
| streamkiste.city | Nicht aufgenommen: abweichender WordPress-Betreiber, kein belastbarer Wiedergabepfad verifiziert. |
| stream-kiste.tv | Nicht aufgenommen: englischsprachige Template-Seite ohne Deutschland-Fokus. |
| x1337x.ws | Nicht aufgenommen: Torrent-/Release-Suche. |
| streamkinos.lat | Nicht aufgenommen: eigener Katalog, aber nur anonyme Drittanbieter-Hoster; Nutzungs-/Rechtebasis nicht verifizierbar. |
| streamkiste.life | Nicht aufgenommen: Squat ohne Katalog. |
| filmportal.de | Nicht aufgenommen: Filmdatenbank ohne abspielbaren Katalog. |
| serienfans.org | Nicht aufgenommen: interaktive Cloudflare-Challenge. |
| vumoo.gd | Nicht aufgenommen: kurzlebige, englischsprachige Mirror-Marke. |
| filmfriend.ch | Nicht aufgenommen: institutionsgebundener Bibliothekslogin. |
| moviepilot.de | Nicht aufgenommen: Metadaten-/Verfuegbarkeitsseite. |
| rbb-online.de | Vorhanden ueber MediathekViewWeb. |
| k-tv.org | Nicht aufgenommen: nur Fremdeinbettungen, kein eigener API-Katalog. |
| tv.orf.at | Vorhanden ueber MediathekViewWeb; kein Doppel-Plugin. |
| joyn.de/mediatheken | Nicht aufgenommen: kommerzieller DRM-Dienst. |
| zdf.de | Vorhanden ueber MediathekViewWeb und `ardmediathek.py`/`arte.py`-OER-Struktur; kein Doppel-Plugin. |
| flixitv-stream.eu | Im Arbeitsbaum als `sites/flixitvstream.py`; fuer Release noch versionieren und in Kodi testen. |
| filmfrei24.com | Nicht aufgenommen: Verbindungstimeout bei der Gegenpruefung. |
| filmfans.org | Nicht aufgenommen: interaktive Cloudflare-Challenge. |
| wdr.de/fernsehen/rockpalast | Vorhanden ueber MediathekViewWeb. |
| xcine.online | Alias der vorhandenen Quelle `xcine`. |
| x-oo.com | Nicht aufgenommen: Spieleportal; Videos sind Fremdeinbettungen. |
| anime-stream.to | Vorhanden: `sites/animestream.py`. |
| dokustreams.de | Vorhanden als Unterquelle in `sites/dokus4me.py`. |
| doksite.de | Nicht aufgenommen: Metadaten/Trailer, keine Vollvideos. |
| doku-streams.com | Neu eingebaut als Unterquelle `_4` in `sites/dokus4me.py`. |
| ardmediathek.de/ndr/ndr_dokus | Vorhanden ueber ARD-/MediathekViewWeb-Anbindung. |
| video.alexanderstreet.com | Nicht aufgenommen: institutioneller Lizenzdienst. |
| campus.arte.tv | Nicht aufgenommen: Campus-/Institutionszugang; reguläres Arte ist bereits vorhanden. |
| edu.medici.tv | Nicht aufgenommen: kostenpflichtiger Bildungszugang. |
| streaming-guide.spiegel.de | Nicht aufgenommen: Verfuegbarkeits-/Guide-Seite, kein Player-Katalog. |
| 3sat.de | Vorhanden ueber MediathekViewWeb. |
| andererseits.org/doku | Nicht aufgenommen: Journalismus-/Textangebot, kein Video-Katalog. |
| dokus4.me | Nicht aufgenommen: TLS/SNI-Fehler und kein Katalog. |
| welt.de/mediathek | Nicht aufgenommen: Nachrichtenportal, kein Doku-Katalog. |
| dailyme.de | Nicht aufgenommen: Webplayer-Sitzung plus Zugriffsschluessel, keine Kodi-API. |
| bpb.de/mediathek | Nicht aufgenommen: Bildungs-/Nachrichtenbeiträge, kein Doku-Katalog. |
| web.archive.org/.../dokuh.de | Vorhanden als historische Unterquelle `dokuh` in `dokus4me.py`; Archivseite ist kein aktueller Streamdienst. |
| odysee.com | Nicht aufgenommen: allgemeine Videoplattform ohne kuratierten Doku-Katalog. |
| phoenix.de | Vorhanden ueber MediathekViewWeb. |
| primewire.pw | Nicht aufgenommen: wechselnde Mirror-Marke ohne stabilen Betreiber. |
| primewire.zip | Nicht aufgenommen: wechselnde Mirror-Marke ohne stabilen Betreiber. |
| primewire.mov | Nicht aufgenommen: wechselnde Mirror-Marke ohne stabilen Betreiber. |
| rumble.com | Nicht aufgenommen: allgemeine Videoplattform ohne kuratierten Doku-Katalog. |
| tierwelt-live.de | Nicht aufgenommen: private Werbe-/UUID-API, kein oeffentlicher Kodi-Pfad. |
| n-tv.de | Nicht aufgenommen: Nachrichtenportal, kein Doku-Katalog. |

## Voraussetzungen fuer einen neuen Einbau

1. Betreiber und Domain sind eindeutig und kein Alias, Squat oder SEO-Koeder.
2. Katalogdaten sind ohne Login- oder JavaScript-Umgehung abrufbar.
3. Die Wiedergabeadresse ist oeffentlich, direkt an Kodi uebergabefaehig und
   nicht nur eine Browser-Sitzung oder Werbe-/DRM-Kette.
4. Code, Settings, Uebersetzungen und ein Icon sind versioniert und mit
   `compileall` sowie einem Kodi-Lauf getestet.
