#!/usr/bin/env bash
set -euo pipefail
: "${GH_TOKEN:?No GitHub token}"
: "${GITHUB_REPOSITORY:?No repository}"
: "${EXPECTED_APPS_JSON:?Missing plan}"
: "${EXPECTED_TARGETS_JSON:?Missing app versions}"
: "${EXPECTED_PATCHES_TAG:?Missing patches tag}"
: "${EXPECTED_RELEASE_TAG:?Missing release tag}"
: "${RELEASE_MODE:?Missing mode}"

[[ "$RELEASE_MODE" == "new_release" || "$RELEASE_MODE" == "update_existing" ]] ||
  { echo "Invalid mode" >&2; exit 2; }
tag="morphe-${EXPECTED_PATCHES_TAG#v}"
[[ "$tag" == "$EXPECTED_RELEASE_TAG" ]] || { echo "Tag mismatch" >&2; exit 2; }
mapfile -t infos < <(find artifacts -type f -name build-info.env | sort)
num="$(jq -er 'length' <<< "$EXPECTED_APPS_JSON")"
(( num > 0 && ${#infos[@]} == num )) ||
  { echo "Expected $num artifacts, received ${#infos[@]}. Reject partial publication." >&2; exit 3; }
read_value() { sed -n "s/^${1}=//p" "$2" | head -n 1; }
declare -A seen=()
apks=()
for info in "${infos[@]}"; do
  app="$(read_value APP_KEY "$info")"
  version="$(read_value APP_VERSION "$info")"
  patches="$(read_value MORPHE_PATCHES_TAG "$info")"
  case "$app" in youtube|youtube-music) ;; *) echo "Unexpected app $app" >&2; exit 3 ;; esac
  jq -e --arg app "$app" 'index($app) != null' <<< "$EXPECTED_APPS_JSON" >/dev/null ||
    { echo "App $app was not planned" >&2; exit 3; }
  wanted="$(jq -er --arg app "$app" '.[$app]' <<< "$EXPECTED_TARGETS_JSON")"
  [[ "$version" == "$wanted" && "$patches" == "$EXPECTED_PATCHES_TAG" ]] ||
    { echo "Unexpected app/patch version for $app" >&2; exit 3; }
  [[ -z "${seen[$app]:-}" ]] || { echo "Duplicate $app" >&2; exit 3; }
  seen[$app]=1
  apk="$(dirname "$info")/$(read_value OUTPUT_APK "$info")"
  [[ -s "$apk" ]] || { echo "Missing APK $apk" >&2; exit 3; }
  checksum="$(read_value APK_SHA256 "$info")"
  echo "$checksum  $apk" | sha256sum -c - >/dev/null ||
    { echo "APK hash mismatch $apk" >&2; exit 3; }
  apks+=("$apk")
done
for app in $(jq -r '.[]' <<< "$EXPECTED_APPS_JSON"); do
  [[ -n "${seen[$app]:-}" ]] || { echo "Missing planned APK $app" >&2; exit 3; }
done

if [[ "$RELEASE_MODE" == "new_release" ]]; then
  (( num == 2 )) || { echo "New release requires both apps" >&2; exit 3; }
  if gh release view "$tag" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
    echo "Release already exists - refuse to overwrite" >&2
    exit 3
  fi
  gh release create "$tag" "${apks[@]}" \
    --repo "$GITHUB_REPOSITORY" --target main \
    --title "Morphe Patched $EXPECTED_PATCHES_TAG" \
    --notes "Supported Stable YouTube and YouTube Music, Morphe $EXPECTED_PATCHES_TAG"
else
  gh release view "$tag" --repo "$GITHUB_REPOSITORY" >/dev/null
  for info in "${infos[@]}"; do
    app="$(read_value APP_KEY "$info")"
    apk="$(dirname "$info")/$(read_value OUTPUT_APK "$info")"
    case "$app" in youtube) prefix=Youtube- ;; youtube-music) prefix=YoutubeMusic- ;; esac
    keep="$(basename "$apk")"
    gh release upload "$tag" "$apk" --repo "$GITHUB_REPOSITORY" --clobber
    mapfile -t names < <(gh release view "$tag" --repo "$GITHUB_REPOSITORY" \
      --json assets --jq '.assets[].name')
    for old in "${names[@]}"; do
      [[ "$old" != "$keep" && "$old" == "$prefix"* && "$old" == *.apk ]] || continue
      gh release delete-asset "$tag" "$old" --repo "$GITHUB_REPOSITORY" --yes
    done
  done
fi

notes="$(mktemp)"
{
  echo "- Morphe patches: **$EXPECTED_PATCHES_TAG**"
  echo "- Bundle: **YouTube + YouTube Music (Stable)**"
  echo
  echo "### APKs"
  gh release view "$tag" --repo "$GITHUB_REPOSITORY" --json assets \
    --jq '.assets[].name' | sort | sed 's/^/- /'
} > "$notes"
gh release edit "$tag" --repo "$GITHUB_REPOSITORY" \
  --title "Morphe Patched $EXPECTED_PATCHES_TAG" --notes-file "$notes"
rm -f "$notes"
echo "Published $num changed APK(s) to $tag; mode=$RELEASE_MODE"
{
 echo "## Published"
 echo "- Release: https://github.com/$GITHUB_REPOSITORY/releases/tag/$tag"
 echo "- Mode: $RELEASE_MODE"
 echo "- APKs: $num"
} >> "$GITHUB_STEP_SUMMARY"
