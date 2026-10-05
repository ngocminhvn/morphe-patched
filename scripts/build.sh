#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT_DIR/config/defaults.env"

: "${SOURCE_FILE:?Set SOURCE_FILE to an original YouTube .apk/.apkm/.apks/.xapk file}"

MORPHE_DESKTOP_VERSION="${MORPHE_DESKTOP_VERSION:-v1.18.0}"
MORPHE_PATCHES_VERSION="${MORPHE_PATCHES_VERSION:-v1.45.0}"
KEEP_ARCHS="${KEEP_ARCHS:-arm64-v8a}"
JAVA_XMX="${JAVA_XMX:-6g}"
EXTRA_DISABLE="${EXTRA_DISABLE:-}"
EXTRA_ENABLE="${EXTRA_ENABLE:-}"
EXPECTED_SHA256="${EXPECTED_SHA256:-}"
OUTPUT_BASENAME="${OUTPUT_BASENAME:-}"

PROTECTED_PATCHES=(
  "GmsCore support"
  "Spoof signature"
  "Custom branding"
)

for cmd in java curl jq python3 sha256sum; do
  command -v "$cmd" >/dev/null || {
    echo "Missing required command: $cmd" >&2
    exit 2
  }
done

SOURCE_FILE="$(realpath "$SOURCE_FILE")"
[[ -f "$SOURCE_FILE" ]] || {
  echo "Source not found: $SOURCE_FILE" >&2
  exit 2
}

case "${SOURCE_FILE,,}" in
  *.apk|*.apkm|*.apks|*.xapk) ;;
  *)
    echo "Unsupported source format. Use .apk, .apkm, .apks, or .xapk" >&2
    exit 2
    ;;
esac

if [[ -n "$EXPECTED_SHA256" ]]; then
  echo "$EXPECTED_SHA256  $SOURCE_FILE" | sha256sum -c -
fi

contains_csv_item_ci() {
  local csv="$1" wanted="$2" item
  IFS=',' read -ra items <<< "$csv"
  for item in "${items[@]}"; do
    item="${item#${item%%[![:space:]]*}}"
    item="${item%${item##*[![:space:]]}}"
    if [[ "${item,,}" == "${wanted,,}" ]]; then
      return 0
    fi
  done
  return 1
}

for patch in "${PROTECTED_PATCHES[@]}"; do
  if contains_csv_item_ci "$EXTRA_ENABLE" "$patch"; then
    echo "Protected patch cannot be enabled: $patch" >&2
    exit 2
  fi
done

WORK_DIR="${WORK_DIR:-$ROOT_DIR/work}"
DIST_DIR="${DIST_DIR:-$ROOT_DIR/dist}"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR/tools" "$WORK_DIR/tmp"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

api_get() {
  local url="$1"
  if [[ -n "${GH_TOKEN:-}" ]]; then
    curl -fsSL       -H "Authorization: Bearer $GH_TOKEN"       -H "Accept: application/vnd.github+json"       "$url"
  else
    curl -fsSL -H "Accept: application/vnd.github+json" "$url"
  fi
}

normalize_tag() {
  local repo="$1" requested="$2"
  if [[ "$requested" == "latest" ]]; then
    api_get "https://api.github.com/repos/$repo/releases/latest" | jq -r '.tag_name'
  elif [[ "$requested" == v* ]]; then
    printf '%s\n' "$requested"
  else
    printf 'v%s\n' "$requested"
  fi
}

asset_url() {
  local repo="$1" tag="$2" regex="$3"
  api_get "https://api.github.com/repos/$repo/releases/tags/$tag"     | jq -r --arg re "$regex" '.assets[] | select(.name | test($re)) | .browser_download_url'     | head -n1
}

DESKTOP_TAG="$(normalize_tag MorpheApp/morphe-desktop "$MORPHE_DESKTOP_VERSION")"
PATCHES_TAG="$(normalize_tag MorpheApp/morphe-patches "$MORPHE_PATCHES_VERSION")"

DESKTOP_URL="$(asset_url MorpheApp/morphe-desktop "$DESKTOP_TAG" 'morphe-desktop-.*-all\\.jar$')"
PATCHES_URL="$(asset_url MorpheApp/morphe-patches "$PATCHES_TAG" 'patches-.*\\.mpp$')"

[[ -n "$DESKTOP_URL" && "$DESKTOP_URL" != null ]] || {
  echo "Morphe Desktop asset not found for $DESKTOP_TAG" >&2
  exit 3
}
[[ -n "$PATCHES_URL" && "$PATCHES_URL" != null ]] || {
  echo "Morphe patches asset not found for $PATCHES_TAG" >&2
  exit 3
}

MORPHE_JAR="$WORK_DIR/tools/morphe-desktop.jar"
PATCHES_MPP="$WORK_DIR/tools/patches.mpp"

echo "Downloading Morphe Desktop $DESKTOP_TAG"
curl -fL --retry 5 --retry-delay 2 -o "$MORPHE_JAR" "$DESKTOP_URL"

echo "Downloading Morphe patches $PATCHES_TAG"
curl -fL --retry 5 --retry-delay 2 -o "$PATCHES_MPP" "$PATCHES_URL"

sha256sum "$MORPHE_JAR" "$PATCHES_MPP"

if [[ "$DESKTOP_TAG" == "v1.18.0" && -n "${MORPHE_DESKTOP_SHA256:-}" ]]; then
  echo "$MORPHE_DESKTOP_SHA256  $MORPHE_JAR" | sha256sum -c -
fi
if [[ "$PATCHES_TAG" == "v1.45.0" && -n "${MORPHE_PATCHES_SHA256:-}" ]]; then
  echo "$MORPHE_PATCHES_SHA256  $PATCHES_MPP" | sha256sum -c -
fi

TEMP_OUTPUT="$WORK_DIR/patched-corepatch.apk"
REPORT="$WORK_DIR/report.json"

ARGS=(
  java "-Xmx$JAVA_XMX" -jar "$MORPHE_JAR" patch
  -p "$PATCHES_MPP"
  --unsigned
  --disable-purge
  -t "$WORK_DIR/tmp"
  --striplibs "$KEEP_ARCHS"
  -r "$REPORT"
  -o "$TEMP_OUTPUT"
)

append_patch_names() {
  local mode="$1" value="$2" item
  [[ -z "$value" ]] && return 0
  IFS=',' read -ra items <<< "$value"
  for item in "${items[@]}"; do
    item="${item#${item%%[![:space:]]*}}"
    item="${item%${item##*[![:space:]]}}"
    [[ -z "$item" ]] || ARGS+=("$mode" "$item")
  done
}

# User selections first.
append_patch_names -d "$EXTRA_DISABLE"
append_patch_names -e "$EXTRA_ENABLE"

# Protected selections last so they cannot be overridden.
for patch in "${PROTECTED_PATCHES[@]}"; do
  ARGS+=(-d "$patch")
done

ARGS+=("$SOURCE_FILE")

printf 'Running:'
printf ' %q' "${ARGS[@]}"
printf '\n'

"${ARGS[@]}" 2>&1 | tee "$WORK_DIR/patch.log"

[[ -s "$TEMP_OUTPUT" ]] || {
  echo "No output APK produced" >&2
  exit 4
}
[[ -s "$REPORT" ]] || {
  echo "No Morphe report produced" >&2
  exit 4
}

jq -e '
  .packageName == "com.google.android.youtube"
  and (.failedPatches | length == 0)
  and (.patchingSteps | length >= 2)
  and ([.patchingSteps[].success] | all)
  and ([.patchingSteps[].step] | index("SIGNING") == null)
  and ([.appliedPatches[].name] | index("GmsCore support") == null)
  and ([.appliedPatches[].name] | index("Spoof signature") == null)
  and ([.appliedPatches[].name] | index("Custom branding") == null)
' "$REPORT" >/dev/null || {
  echo "Morphe report validation failed" >&2
  cat "$REPORT" >&2
  exit 5
}

python3 "$ROOT_DIR/scripts/apk_sigblock.py" "$SOURCE_FILE" "$TEMP_OUTPUT"

VERSION="$(jq -r '.packageVersion' "$REPORT")"
[[ -n "$VERSION" && "$VERSION" != null ]] || {
  echo "Could not determine YouTube version from report" >&2
  exit 5
}

if [[ -z "$OUTPUT_BASENAME" ]]; then
  OUTPUT_BASENAME="YouTube-${VERSION}-Morphe-${PATCHES_TAG#v}-CorePatch-GoogleCert"
fi

FINAL_APK="$DIST_DIR/$OUTPUT_BASENAME.apk"
FINAL_REPORT="$DIST_DIR/$OUTPUT_BASENAME-report.json"
FINAL_LOG="$DIST_DIR/$OUTPUT_BASENAME-build.log"

cp "$TEMP_OUTPUT" "$FINAL_APK"
cp "$REPORT" "$FINAL_REPORT"
cp "$WORK_DIR/patch.log" "$FINAL_LOG"
sha256sum "$FINAL_APK" | tee "$DIST_DIR/$OUTPUT_BASENAME.sha256"

cat > "$DIST_DIR/build-info.txt" <<EOF
package=com.google.android.youtube
version=$VERSION
morphe_desktop=$DESKTOP_TAG
morphe_patches=$PATCHES_TAG
keep_archs=$KEEP_ARCHS
gmscore_support=false
spoof_signature=false
custom_branding=false
app_icon=original_youtube
signing=morphe_unsigned_google_certificate_identity_preserved
corepatch_required=true
EOF

echo "Built: $FINAL_APK"
