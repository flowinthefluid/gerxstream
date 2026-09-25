#!/usr/bin/env bash
# Build the public Kodi repository consumed by GitLab Pages.
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pages_url="${1:?Usage: build-gitlab-pages.sh <GitLab-Pages-URL>}"
pages_url="${pages_url%/}"
public_dir="$project_dir/public"
repository_id="repository.gerxstream"
repository_version="1.0.5"
resolver_id="script.module.resolveurl"
resolver_version="5.1.209"
resolver_archive="$project_dir/release-inputs/$resolver_id-$resolver_version.zip"

if [[ -e "$public_dir" ]]; then
    printf 'Ausgabeverzeichnis existiert bereits: %s\n' "$public_dir" >&2
    exit 1
fi

addon_id="$(xmllint --xpath 'string(/addon/@id)' "$project_dir/addon.xml")"
addon_version="$(xmllint --xpath 'string(/addon/@version)' "$project_dir/addon.xml")"
if [[ "$addon_id" != "plugin.video.gerxstream" || "$addon_version" != "1.0.26" ]]; then
    printf 'Erwartet wird plugin.video.gerxstream 1.0.26, gefunden: %s %s\n' \
        "$addon_id" "$addon_version" >&2
    exit 1
fi
if [[ ! -f "$resolver_archive" ]]; then
    printf 'ResolveURL-Release fehlt: %s\n' "$resolver_archive" >&2
    exit 1
fi
unzip -tqq "$resolver_archive"

build_dir="$(mktemp -d -t gerx-pages.XXXXXX)"
cleanup() {
    rm -rf "$build_dir"
}
trap cleanup EXIT

mkdir -p "$public_dir/zips/$addon_id"

# The plug-in archive contains only Kodi runtime files, no development or release material.
plugin_payload="$build_dir/$addon_id"
mkdir -p "$plugin_payload"
for entry in addon.xml default.py gerxstream.py service.py changelog.txt license.txt resources sites; do
    cp -a "$project_dir/$entry" "$plugin_payload/"
done
(
    cd "$build_dir"
    zip -X -q -r "$public_dir/zips/$addon_id/$addon_id-$addon_version.zip" "$addon_id"
)

# Sidecar metadata and every asset advertised from addon.xml are available before installation.
install -m 0644 "$project_dir/addon.xml" "$public_dir/zips/$addon_id/addon.xml"
install -m 0644 "$project_dir/changelog.txt" "$public_dir/zips/$addon_id/changelog.txt"
for asset in icon.png fanart.jpg banner.png clearlogo.png; do
    install -D -m 0644 "$project_dir/resources/$asset" \
        "$public_dir/zips/$addon_id/resources/$asset"
done

# ResolveURL is a non-optional dependency of GerXStream and is published here
# so a fresh Kodi installation can resolve it without a second source.
mkdir -p "$public_dir/zips/$resolver_id"
install -m 0644 "$resolver_archive" \
    "$public_dir/zips/$resolver_id/$resolver_id-$resolver_version.zip"
unzip -p "$resolver_archive" "$resolver_id/addon.xml" \
    > "$public_dir/zips/$resolver_id/addon.xml"
for asset in icon.png fanart.jpg; do
    unzip -p "$resolver_archive" "$resolver_id/$asset" \
        > "$public_dir/zips/$resolver_id/$asset"
done

# Build the repository pointer ZIP with the actual GitLab Pages URL supplied by CI.
repository_payload="$build_dir/$repository_id"
mkdir -p "$repository_payload"
sed "s|@PAGES_URL@|$pages_url|g" "$project_dir/$repository_id/addon.xml.in" \
    > "$repository_payload/addon.xml"
install -m 0644 "$project_dir/resources/icon.png" "$repository_payload/icon.png"
install -m 0644 "$project_dir/resources/fanart.jpg" "$repository_payload/fanart.jpg"
(
    cd "$build_dir"
    mkdir -p "$public_dir/zips/$repository_id"
    zip -X -q -r "$public_dir/zips/$repository_id/$repository_id-$repository_version.zip" "$repository_id"
)
install -m 0644 "$public_dir/zips/$repository_id/$repository_id-$repository_version.zip" \
    "$public_dir/$repository_id-$repository_version.zip"
install -m 0644 "$repository_payload/addon.xml" "$public_dir/zips/$repository_id/addon.xml"
install -m 0644 "$repository_payload/icon.png" "$public_dir/zips/$repository_id/icon.png"
install -m 0644 "$repository_payload/fanart.jpg" "$public_dir/zips/$repository_id/fanart.jpg"

# Kodi reads the add-on declarations from this catalogue and its checksum.
{
    printf '%s\n' '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    printf '%s\n' '<addons>'
    unzip -p "$resolver_archive" "$resolver_id/addon.xml" | sed '1{/^<?xml /d;}'
    sed '1{/^<?xml /d;}' "$project_dir/addon.xml"
    sed '1{/^<?xml /d;}' "$repository_payload/addon.xml"
    printf '%s\n' '</addons>'
} > "$public_dir/addons.xml"
printf '%s' "$(md5sum "$public_dir/addons.xml" | awk '{print $1}')" \
    > "$public_dir/addons.xml.md5"

# Kodi may cache the installation page as a directory containing only ZIPs.
# Keep the index and checksum in a separate path that is never browsed for ZIPs.
mkdir -p "$public_dir/catalog"
install -m 0644 "$public_dir/addons.xml" "$public_dir/catalog/addons.xml"
install -m 0644 "$public_dir/addons.xml.md5" "$public_dir/catalog/addons.xml.md5"

sed "s|@REPOSITORY_VERSION@|$repository_version|g" "$project_dir/pages/index.html.in" \
    > "$public_dir/index.html"

printf 'GitLab-Pages-Repository erstellt: %s/%s, %s/%s und %s/%s\n' \
    "$repository_id" "$repository_version" "$resolver_id" "$resolver_version" \
    "$addon_id" "$addon_version"
