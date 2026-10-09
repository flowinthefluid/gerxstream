# PR-Idee: Add-on-Aktionen im nativen Kodi-Player

Status: Vorschlag fuer Kodi-Core und Estuary, keine implementierte Kodi-API.
Es wurde kein Issue und kein Pull Request bei Kodi eroeffnet.

Vorgeschlagener Upstream-Titel:
**Add playback-scoped add-on actions to the native player OSD**

## Ausgangspunkt

Video-Add-ons sollen den nativen Kodi-Player verwenden und fuer ihre eigene
Wiedergabe passende Aktionen anbieten koennen, ohne Skin-Dateien zu ersetzen
oder globale Tastenzuordnungen zu aendern. Beispiele sind "Naechste Episode",
"Vorherige Episode", "Intro ueberspringen" oder eine Quellenwahl.

Der konkrete Wunsch: Bei Serien soll eine klar bezeichnete Aktion
"Naechste Episode" unmittelbar im Player erreichbar sein. Das Symbol fuer
Vorspulen darf nicht irrefuehrend als Episodenwechsel bezeichnet werden.

## Was Kodi bereits kann

- Die Player-Oberflaeche ist skinbasiert und kann durch einen Skin angepasst
  werden. Ein angepasstes Video-OSD kann andere Knoepfe und Aktionen anbieten.
- `PlayerControl(Forward)` spult vor; `PlayerControl(Next)` ist eine separate
  Kodi-Aktion fuer den naechsten Eintrag beziehungsweise die native Navigation.
- Estuary hat getrennte Forward- und Next-Knoepfe. Im untersuchten
  Upstream-Stand sind das die Controls 606 und 607.
- Der Next-Knopf wird unter anderem bei `Playlist.Length(video) > 1`
  sichtbar. Weitere Bedingungen sind Kapitel, Szenenmarker und Timeshift;
  seine Sichtbarkeit beweist deshalb allein keine Episoden-Playlist.
- Video-Add-ons koennen eine native Playlist mit abspielbaren Provider-Routen
  aufbauen. Fuer den normalen Episodenwechsel ist keine neue Player-API noetig.

Die Luecke ist die generische, pro Wiedergabe gueltige Registrierung und
Darstellung eigener Aktionen im nativen OSD. Die normale Player-API bietet
keinen Vertrag, mit dem ein Video-Plugin den Forward-Knopf fuer seine Sitzung
in einen frei definierten Episoden-Knopf umwandeln kann.

## Vorschlag

1. Kodi bietet eine dokumentierte Registrierung von Player-Aktionen durch
   das Add-on, dem die aktuelle Wiedergabe gehoert. Die Registrierung wird an
   eine Wiedergabe-Sitzung gebunden, nicht an globale Window-Properties allein.
2. Eine Aktion beschreibt eine stabile Kennung, eine lokalisierte Beschriftung,
   ein semantisches Icon, Sichtbarkeit, Verfuegbarkeit und ihre Ausfuehrung.
   Fuer Standardfaelle werden native Aktionen wiederverwendet.
3. Fuer "Naechste Episode" mit vorhandener Playlist wird der native
   Playlist-Wechsel genutzt. Andere Aktionen duerfen eine validierte Route
   des registrierenden Add-ons aufrufen; Stream-Aufloesung bleibt bedarfsweise.
4. Estuary stellt diese Aktionen in einem definierten OSD-Bereich dar.
   Andere Skins erhalten dieselben Metadaten und entscheiden ueber das Layout.
5. Optional kann der Nutzer fuer Serien einen kompakten Steuerungsmodus
   waehlen, der den Episodenwechsel gegenueber schnellem Vorlauf priorisiert.
   Ohne diese ausdrueckliche Wahl bleiben die gewohnten Controls unveraendert.

API-Namen, Datenformat und Callback-Mechanismus muessen mit Kodi abgestimmt
werden. Dieser Vorschlag setzt keine heute vorhandene Python-Methode voraus.

## Grenzen und Lebenszyklus

- Play/Pause und Stop bleiben erreichbar. Ein Add-on darf sie nicht entfernen
  oder ihre grundlegende Bedeutung ersetzen.
- Das Add-on bestimmt Aktionen und ihren Zustand, nicht beliebiges Skin-XML.
  Skins und Nutzer behalten die Kontrolle ueber Darstellung und Bedienung.
- Die Registrierung erlischt bei Stop, Ende, Wiedergabefehler, Add-on-Abbruch
  oder Wechsel zu einer fremden Wiedergabe. Verspaetete Callbacks einer alten
  Sitzung duerfen die neue Sitzung weder steuern noch ihre Aktionen entfernen.
- Kodi validiert Besitzer, Sitzungskennung, Callback-Ziel und Icon-Ressourcen.
  Keine beliebigen Shell-Befehle oder unbeschraenkte Built-in-Ausfuehrung.
- Langsame Add-on-Aufrufe blockieren den Player-UI-Thread nicht. Mehrfachklicks,
  Abbruch und nicht mehr verfuegbare Aktionen werden definiert behandelt.
- Bestehende Add-ons und Skins funktionieren ohne Anpassung weiter. Bei einem
  Skin ohne Unterstuetzung bleibt das native OSD benutzbar; die neuen Aktionen
  brauchen einen zugaenglichen Standard-Fallback, etwa ein Player-Aktionsmenue.
- Beschriftungen, Fokusreihenfolge und Bedienung mit Fernbedienung, Tastatur,
  Maus und Touch gehoeren zum Vertrag.

## Abnahmekriterien

- Ein beliebiges Video-Add-on kann eine Aktion anbieten, ohne den Skin zu
  patchen. Estuary zeigt Label und Icon mit nachvollziehbarem Fokusverhalten.
- "Naechste Episode" startet genau die folgende Folge, nicht schnellen Vorlauf
  oder ein Kapitel. Ohne folgende Folge ist diese Aktion nicht aktiv.
- Filme, lokale Dateien und fremde Add-ons behalten ihre Standard-Steuerung.
- Stop stellt die vorherige Navigation wieder her; eine OSD-Aktion erzeugt
  keinen leeren Verzeichnisaufruf und keinen globalen Container-Refresh.
- Sitzungswechsel, Resolver-Fehler, Add-on-Abbruch und nicht unterstuetzende
  Skins werden automatisiert sowie auf Desktop und Android getestet.

## Quellen

- [Estuary VideoOSD.xml](https://github.com/xbmc/xbmc/blob/master/addons/skin.estuary/xml/VideoOSD.xml)
- [Kodi Player-Built-ins](https://kodi.wiki/view/List_of_built-in_functions#Player_built-in.27s)
- [Kodi PluginDirectory.cpp](https://github.com/xbmc/xbmc/blob/master/xbmc/filesystem/PluginDirectory.cpp)

Die verlinkten Upstream-Dateien zeigen einen beweglichen Stand. Ein konkreter
PR muss die dann verwendete Kodi-Version und die betroffenen Skin-Contracts
festhalten.
