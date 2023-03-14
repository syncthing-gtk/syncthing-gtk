#!/usr/bin/env bash
set -Eeuo pipefail
set -x

BUILDDIR="$PWD/_build_msi"
DESTDIR="$BUILDDIR/installdir"

meson setup "$BUILDDIR" \
    --backend=ninja \
    --buildtype=release

DESTDIR="$DESTDIR" ninja -C "$BUILDDIR" install

# List installed files
find "$DESTDIR" | wixl-heat -p "$DESTDIR/usr/local/" \
    --component-group CG.syncthing-gtk \
    --directory-ref INSTALLDIR \
    --var var.SourceDir \
    > "$BUILDDIR/packaging/windows/msi_files.wxs"


# Generate the MSI file
wixl -v --ext ui --arch x64 \
    -D SourceDir="$DESTDIR/usr/local" \
    -D ProductIcon="$PWD/icons/st-logo-128.ico" \
    "$BUILDDIR/packaging/windows/syncthing-gtk.wxs" \
    "$BUILDDIR/packaging/windows/msi_files.wxs" \
    -o "$PWD/syncthing-gtk.msi"
