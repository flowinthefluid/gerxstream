#!/usr/bin/env bash
# Baut die versionierten Dateien fuer repo/ aus dem aktuellen Arbeitsbaum.
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_dir="$project_dir/repo"
repo_addon_id="repository.gerxstream"
repo_version="1.0.0"

addon_id="$(xmllint --xpath 'string(/addon/@id)' "$project_dir/addon.xml")"
addon_version="$(xmllint --xpath 'string(/addon/@version)' "$project_dir/addon.xml")"

if [[ -z "$addon_id" || -z "$addon_version" ]]; then
    printf 'Die Add-on-ID oder Version in addon.xml fehlt.\n' >&2
    exit 1
fi

build_dir="$(mktemp -d)"
cleanup() {
    rm -rf "$build_dir"
}
trap cleanup EXIT

payload_dir="$build_dir/$addon_id"
while IFS= read -r -d '' relative_path; do
    case "$relative_path" in
        .github/*|.gitignore|README.md|ScraperInfo.txt|design/*|docs/*|repo/*|tools/*|*.zip)
            continue
            ;;
    esac

    source_path="$project_dir/$relative_path"
    if [[ -f "$source_path" ]]; then
        install -D -m 0644 "$source_path" "$payload_dir/$relative_path"
    fi
done < <(git -C "$project_dir" ls-files -z)

if [[ ! -f "$payload_dir/addon.xml" ]]; then
    printf 'addon.xml wurde nicht in das Paket uebernommen.\n' >&2
    exit 1
fi

plugin_release_dir="$repo_dir/zips/$addon_id"
mkdir -p "$plugin_release_dir" "$repo_dir/$repo_addon_id"

plugin_archive="$plugin_release_dir/$addon_id-$addon_version.zip"
rm -f "$plugin_archive"
(
    cd "$build_dir"
    zip -X -q -r "$plugin_archive" "$addon_id"
)

install -m 0644 "$project_dir/addon.xml" "$plugin_release_dir/addon.xml"
install -m 0644 "$project_dir/changelog.txt" "$plugin_release_dir/changelog.txt"
sed -i '${/^$/d;}' "$plugin_release_dir/changelog.txt"
install -m 0644 "$project_dir/resources/icon.png" "$plugin_release_dir/icon.png"
install -m 0644 "$project_dir/resources/fanart.jpg" "$plugin_release_dir/fanart.jpg"
install -m 0644 "$project_dir/resources/icon.png" "$repo_dir/$repo_addon_id/icon.png"
install -m 0644 "$project_dir/resources/fanart.jpg" "$repo_dir/$repo_addon_id/fanart.jpg"

repository_archive="$repo_dir/$repo_addon_id-$repo_version.zip"
rm -f "$repository_archive"
(
    cd "$repo_dir"
    zip -X -q -r "$repository_archive" "$repo_addon_id"
)

manifest_tmp="$build_dir/addons.xml"
{
    printf '%s\n' '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    printf '%s\n' '<addons>'
    sed '1{/^<?xml /d;}' "$project_dir/addon.xml"
    printf '%s\n' '</addons>'
} > "$manifest_tmp"
install -m 0644 "$manifest_tmp" "$repo_dir/addons.xml"
checksum="$(md5sum "$repo_dir/addons.xml" | awk '{print $1}')"
printf '%s' "$checksum" > "$repo_dir/addons.xml.md5"

printf 'Repository erstellt: %s (%s)\n' "$addon_id" "$addon_version"
