#!/usr/bin/env bash
set -Eeuo pipefail

true """
This script is mainly here because Github Action build-appimage runs in a docker
container without the 'meson' command : we can't use the 'script' section of the
AppImageBuilder.yml. So here's a wrapper script (not used by the CI).
Should be called from the root of the repository.
"""

# remove any existent binaries
rm -rf AppDir | true
meson setup _build_appimage --prefix="$PWD/AppDir/usr" --buildtype=release
meson install -C _build_appimage

appimage-builder --recipe packaging/appimage/AppImageBuilder.yml
