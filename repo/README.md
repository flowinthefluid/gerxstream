# GerXStream Kodi-Repository

Dieser Ordner ist die auslieferbare Kodi-Quelle. Nach der Veroeffentlichung
ueber GitHub Pages lautet die Quellen-URL:

```
https://flowinthefluid.github.io/gerxstream/repo/
```

## Einmalig veroeffentlichen

1. Das Projekt als **oeffentliches** Repository
   `flowinthefluid/gerxstream` auf GitHub anlegen und den Branch `main`
   pushen.
2. In GitHub unter **Settings -> Pages** "Deploy from a branch", Branch
   `main` und Ordner `/(root)` auswaehlen.
3. Warten, bis GitHub die oben genannte Pages-URL als erfolgreich deployed
   anzeigt. Die Zip-Datei und `addons.xml` muessen dort mit HTTP 200 erreichbar
   sein.

## Kodi-Installation

1. Im Dateimanager die Quellen-URL eintragen, beispielsweise als
   `GerXStream`.
2. **Add-ons -> Aus ZIP-Datei installieren** und
   `repository.gerxstream-1.0.0.zip` auswaehlen.
3. Anschliessend **Aus Repository installieren -> GerXStream Repository**.

`addons.xml` ist der Katalog, `addons.xml.md5` dessen Pruefsumme und `zips/`
enthaelt die installierbaren Add-on-Pakete. Der Katalog und beide Zip-Dateien
werden durch `../tools/build-repo.sh` aus dem aktuellen Add-on erzeugt.

Die aktuelle Add-on-ID ist noch `plugin.video.xstream`. Deshalb liegt die
Auslieferung absichtlich unter `zips/plugin.video.xstream/`; erst mit einer
vollstaendigen ID-Migration darf sie nach `plugin.video.gerxstream/` umziehen.
Das Add-on benoetigt weiterhin ResolveURL aus dessen eigener Repository-Quelle.
