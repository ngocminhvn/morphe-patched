#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT_DIR/config/defaults.env"

: "${SOURCE_FILE:?Set SOURCE_FILE to an original APK/APKM/APKS/XAPK file}"

APP="${APP:-youtube}"
KEEP_ARCHS="${KEEP_ARCHS:-arm64-v8a}"
JAVA_XMX="${JAVA_XMX:-6g}"
WORK_DIR="${WORK_DIR:-$ROOT_DIR/work}"
DIST_DIR="${DIST_DIR:-$ROOT_DIR/dist}"

case "$APP" in
  youtube)
    APP_NAME="YouTube"
    APP_SLUG="youtube"
    OUTPUT_NAME="Youtube"
    PACKAGE_NAME="com.google.android.youtube"
    ;;
  youtube-music)
    APP_NAME="YouTube Music"
    APP_SLUG="youtube-music"
    OUTPUT_NAME="YoutubeMusic"
    PACKAGE_NAME="com.google.android.apps.youtube.music"
    ;;
  reddit)
    APP_NAME="Reddit"
    APP_SLUG="reddit"
    OUTPUT_NAME="Reddit"
    PACKAGE_NAME="com.reddit.frontpage"
    ;;
  *)
    echo "Unsupported APP: $APP" >&2
    exit 2
    ;;
esac

# These patches can alter package/signature/icon identity or move Google apps
# away from stock Google Play Services. Keep them disabled for CorePatch ROMs.
PROTECTED_PATCHES=(
  "GmsCore support"
  "Clone app"
  "Spoof signature"
  "Custom branding"
  "App icon"
)

for cmd in java curl jq python3 sha256sum; do
  command -v "$cmd" >/dev/null || { echo "Missing command: $cmd" >&2; exit 2; }
done

SOURCE_FILE="$(realpath "$SOURCE_FILE")"
[[ -f "$SOURCE_FILE" ]] || { echo "Source not found: $SOURCE_FILE" >&2; exit 2; }

rm -rf "$WORK_DIR" "$DIST_DIR"
mkdir -p "$WORK_DIR/tools" "$WORK_DIR/tmp" "$DIST_DIR"

api_get() {
  local url="$1"
  if [[ -n "${GH_TOKEN:-}" ]]; then
    curl -fsSL -H "Authorization: Bearer $GH_TOKEN" -H "Accept: application/vnd.github+json" "$url"
  else
    curl -fsSL -H "Accept: application/vnd.github+json" "$url"
  fi
}

latest_release_asset() {
  local repo="$1" suffix="$2" json tag url digest
  json="$(api_get "https://api.github.com/repos/$repo/releases/latest")"

  tag="$(jq -r '.tag_name // empty' <<< "$json")"
  url="$(jq -r --arg suffix "$suffix" '
    [.assets[]? | select(.name | endswith($suffix)) | .browser_download_url][0] // empty
  ' <<< "$json")"
  digest="$(jq -r --arg suffix "$suffix" '
    [.assets[]? | select(.name | endswith($suffix)) | (.digest // "")][0] // ""
  ' <<< "$json")"

  [[ -n "$tag" ]] || {
    echo "Latest release tag not found for $repo" >&2
    return 1
  }
  [[ -n "$url" ]] || {
    echo "Latest release asset ending with '$suffix' not found for $repo ($tag)" >&2
    echo "Available assets:" >&2
    jq -r '.assets[]?.name' <<< "$json" >&2
    return 1
  }

  printf '%s\n%s\n%s\n' "$tag" "$url" "$digest"
}

mapfile -t desktop_info < <(latest_release_asset MorpheApp/morphe-desktop '-all.jar')
mapfile -t patches_info < <(latest_release_asset MorpheApp/morphe-patches '.mpp')

[[ "${#desktop_info[@]}" -ge 2 ]] || {
  echo "Could not resolve latest Morphe Desktop release asset" >&2
  exit 3
}
[[ "${#patches_info[@]}" -ge 2 ]] || {
  echo "Could not resolve latest Morphe patches release asset" >&2
  exit 3
}

DESKTOP_TAG="${desktop_info[0]}"
DESKTOP_URL="${desktop_info[1]}"
DESKTOP_DIGEST="${desktop_info[2]:-}"
PATCHES_TAG="${patches_info[0]}"
PATCHES_URL="${patches_info[1]}"
PATCHES_DIGEST="${patches_info[2]:-}"

echo "App: $APP_NAME ($PACKAGE_NAME)"
echo "Latest Morphe Desktop: $DESKTOP_TAG"
echo "Latest Morphe patches: $PATCHES_TAG"

MORPHE_JAR="$WORK_DIR/tools/morphe-desktop.jar"
PATCHES_MPP="$WORK_DIR/tools/patches.mpp"

curl -fL --retry 5 --retry-delay 2 -o "$MORPHE_JAR" "$DESKTOP_URL"
curl -fL --retry 5 --retry-delay 2 -o "$PATCHES_MPP" "$PATCHES_URL"

verify_digest() {
  local declared="$1" file="$2"
  [[ -z "$declared" || "$declared" == "null" ]] && return 0
  if [[ "$declared" == sha256:* ]]; then
    echo "${declared#sha256:}  $file" | sha256sum -c -
  fi
}
verify_digest "$DESKTOP_DIGEST" "$MORPHE_JAR"
verify_digest "$PATCHES_DIGEST" "$PATCHES_MPP"

python3 "$ROOT_DIR/scripts/update_supported.py" \
  --tag "$PATCHES_TAG" \
  --app "$APP" \
  --output "$DIST_DIR/SUPPORTED.md" \
  --json-output "$WORK_DIR/support.json"

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

for patch in "${PROTECTED_PATCHES[@]}"; do
  ARGS+=(-d "$patch")
done
ARGS+=("$SOURCE_FILE")

printf 'Running:'
printf ' %q' "${ARGS[@]}"
printf '\n'

"${ARGS[@]}" 2>&1 | tee "$WORK_DIR/patch.log"

[[ -s "$TEMP_OUTPUT" ]] || { echo "No output APK produced" >&2; exit 4; }
[[ -s "$REPORT" ]] || { echo "No Morphe report produced" >&2; exit 4; }

jq -e --arg pkg "$PACKAGE_NAME" '
  .packageName == $pkg
  and (.failedPatches | length == 0)
  and (.patchingSteps | length >= 2)
  and ([.patchingSteps[].success] | all)
  and ([.patchingSteps[].step] | index("SIGNING") == null)
  and ([.appliedPatches[].name] | index("GmsCore support") == null)
  and ([.appliedPatches[].name] | index("Clone app") == null)
  and ([.appliedPatches[].name] | index("Spoof signature") == null)
  and ([.appliedPatches[].name] | index("Custom branding") == null)
  and ([.appliedPatches[].name] | index("App icon") == null)
' "$REPORT" >/dev/null || {
  echo "Morphe report validation failed" >&2
  cat "$REPORT" >&2
  exit 5
}

VERSION="$(jq -r '.packageVersion' "$REPORT")"
SUPPORT_JSON="$(jq -c --arg v "$VERSION" '.versions[] | select(.version == $v)' "$WORK_DIR/support.json" | head -n1)"
if [[ -z "$SUPPORT_JSON" ]]; then
  echo "$APP_NAME $VERSION is not listed as supported by $PATCHES_TAG" >&2
  echo "See SUPPORTED.md for supported versions." >&2
  exit 6
fi

EXPERIMENTAL="$(jq -r '.experimental' <<< "$SUPPORT_JSON")"
MIN_SDK="$(jq -r '.minSdk' <<< "$SUPPORT_JSON")"

python3 "$ROOT_DIR/scripts/apk_sigblock.py" \
  --app "$APP" \
  --preserve-source-block \
  "$SOURCE_FILE" "$TEMP_OUTPUT"

PATCH_VERSION="${PATCHES_TAG#v}"
# Build date follows Vietnam local time: 09 October 2026 -> 091026.
# The check workflow compares app/version/patch independently of this date.
BUILD_DATE="$(TZ=Asia/Ho_Chi_Minh date +%d%m%y)"
OUTPUT_BASENAME="${OUTPUT_NAME}-${VERSION}-morphe-${PATCH_VERSION}-${BUILD_DATE}"

FINAL_APK="$DIST_DIR/$OUTPUT_BASENAME.apk"
FINAL_REPORT="$DIST_DIR/$OUTPUT_BASENAME-report.json"
FINAL_LOG="$DIST_DIR/$OUTPUT_BASENAME-build.log"

cp "$TEMP_OUTPUT" "$FINAL_APK"
cp "$REPORT" "$FINAL_REPORT"
cp "$WORK_DIR/patch.log" "$FINAL_LOG"

SOURCE_SHA256="$(sha256sum "$SOURCE_FILE" | awk '{print $1}')"
APK_SHA256="$(sha256sum "$FINAL_APK" | awk '{print $1}')"
printf '%s  %s\n' "$APK_SHA256" "$(basename "$FINAL_APK")" > "$DIST_DIR/$OUTPUT_BASENAME.sha256"

cat > "$DIST_DIR/build-info.txt" <<EOF
app_key=$APP
app_name=$APP_NAME
package=$PACKAGE_NAME
version=$VERSION
status=$([[ "$EXPERIMENTAL" == "true" ]] && echo experimental || echo stable)
min_sdk=$MIN_SDK
morphe_desktop=$DESKTOP_TAG
morphe_patches=$PATCHES_TAG
keep_archs=$KEEP_ARCHS
gmscore_support=false
clone_app=false
spoof_signature=false
custom_branding=false
app_icon_patch=false
app_icon=original
signing=morphe_unsigned_original_certificate_identity_preserved
corepatch_required=true
source_sha256=$SOURCE_SHA256
apk_sha256=$APK_SHA256
EOF

cat > "$DIST_DIR/build-info.env" <<EOF
APP_KEY=$APP
APP_NAME=$APP_NAME
APP_SLUG=$APP_SLUG
PACKAGE_NAME=$PACKAGE_NAME
APP_VERSION=$VERSION
EXPERIMENTAL=$EXPERIMENTAL
MIN_SDK=$MIN_SDK
MORPHE_DESKTOP_TAG=$DESKTOP_TAG
MORPHE_PATCHES_TAG=$PATCHES_TAG
OUTPUT_APK=$(basename "$FINAL_APK")
SOURCE_SHA256=$SOURCE_SHA256
APK_SHA256=$APK_SHA256
EOF

echo "Built: $FINAL_APK"
