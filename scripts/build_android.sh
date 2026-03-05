#!/usr/bin/env bash
set -euo pipefail

# Build Android binaries for this project.
# Default behavior builds arm64 (works without NDK/cgo in this repo).
# Optional arm32 build can be enabled with --with-arm32, but it may require NDK/cgo.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}"
BUILD_ARM32=false

usage() {
  cat <<'EOF'
Usage:
  ./scripts/build_android.sh [--with-arm32]

Options:
  --with-arm32   Attempt additional android/arm (32-bit) build.
                 This target can require cgo/NDK for this project.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-arm32)
      BUILD_ARM32=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

echo "[build] project root: ${ROOT_DIR}"
cd "${ROOT_DIR}"

echo "[build] android/arm64 -> webterm-android-arm64"
GOOS=android GOARCH=arm64 CGO_ENABLED=0 go build -v -o "${OUTPUT_DIR}/webterm-android-arm64" main.go

echo "[ok] built ${OUTPUT_DIR}/webterm-android-arm64"

if [[ "${BUILD_ARM32}" == true ]]; then
  echo "[build] android/arm -> webterm-android-arm"
  if GOOS=android GOARCH=arm GOARM=7 CGO_ENABLED=0 go build -v -o "${OUTPUT_DIR}/webterm-android-arm" main.go; then
    echo "[ok] built ${OUTPUT_DIR}/webterm-android-arm"
  else
    echo "[warn] android/arm build failed. This target may require Android NDK/cgo for this project." >&2
    echo "[warn] arm64 binary is still valid for most modern Android devices." >&2
  fi
fi

echo "[done] build completed"
