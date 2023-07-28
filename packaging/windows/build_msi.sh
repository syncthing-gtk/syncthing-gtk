#!/usr/bin/env bash
set -Eeuo pipefail
# set -x

BUILDDIR="$PWD/_build_msi"
DESTDIR="$BUILDDIR/installdir"

meson setup "$BUILDDIR" \
    --backend=ninja \
    --buildtype=release

DESTDIR="$DESTDIR" ninja -C "$BUILDDIR" install

PREFIX=$(meson introspect --buildoptions "$BUILDDIR" | jq -r '.[] | select(.name=="prefix") | .value')

INSTPREFIX="$DESTDIR/${PREFIX//C:\//}/"

# List installed files
readarray -t FILES < <(find "$INSTPREFIX")

# Convert to windows paths if necessary
if [ "$MSYSTEM" == "MINGW64" ]; then
    INSTPREFIX="$(cygpath -w "$INSTPREFIX")"
    readarray -t FILES < <(cygpath -w "${FILES[@]}")
fi

# Generate the xml containing the list of files
printf '%s\n' "${FILES[@]}" | wixl-heat -p "$INSTPREFIX" \
    --component-group CG.syncthing-gtk \
    --directory-ref INSTALLDIR \
    --var var.SourceDir \
    > "$BUILDDIR/packaging/windows/msi_files.wxs"


# Generate the MSI file
wixl -v --ext ui --arch x64 \
    --extdir /mingw64/share/wixl-0.102/ext \
    -D SourceDir="$INSTPREFIX" \
    -D ProductIcon="$PWD/icons/st-logo-128.ico" \
    "$BUILDDIR/packaging/windows/syncthing-gtk.wxs" \
    "$BUILDDIR/packaging/windows/msi_files.wxs" \
    -o "$PWD/syncthing-gtk.msi"
