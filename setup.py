#!/usr/bin/env python3

import glob
import os
import re
import subprocess
from distutils.core import setup
from pathlib import Path

APP_ICON_SIZES = (16, 24, 32, 64, 128, 256)
SI_ICON_SIZES = (16, 24, 32)


def get_version():
    """
    Returns current package version using git-describe or examining
    path. If both methods fails, returns 'unknown'.
    """
    try:
        version = subprocess.check_output(["git", "describe", "--tags"])
        version = version.decode("utf-8").strip("\n\r \t")
    except subprocess.CalledProcessError:
        # Git-describe method failed, try to guess from working directory name
        project_dir_name = Path(__file__).parent.name
        result = re.match(r"syncthing-gtk-(.*)", project_dir_name)
        if result:
            version = result.group(1)
        else:
            raise RuntimeError(f'Directory name "{project_dir_name}" does not match "syncthing-gtk-<version>".')

    # Adapt .post versions to PEP 440
    if "-" in version:
        semver, post, commit = version.split("-")
        commit = commit.lstrip("g")
        version = f"{semver}.post{post}+git.{commit}"

    return version


def find_mos(parent, lst=[]):
    for f in os.listdir(parent):
        fp = os.path.join(parent, f)
        if os.path.isdir(fp):
            find_mos(fp, lst)
        elif fp.endswith(".mo"):
            lst += [fp]
    return lst


if __name__ == "__main__":
    data_files = (
        [
            ("share/syncthing-gtk", glob.glob("ui/*.ui")),
            ("share/syncthing-gtk", glob.glob("scripts/syncthing-plugin-*.py")),
            (
                "share/syncthing-gtk/icons",
                [
                    "icons/%s.svg" % x
                    for x in (
                        "add_node",
                        "add_repo",
                        "address",
                        "announce",
                        "clock",
                        "compress",
                        "cpu",
                        "dl_rate",
                        "eye",
                        "folder",
                        "global",
                        "home",
                        "ignore",
                        "lock",
                        "ram",
                        "shared",
                        "show_id",
                        "show_id",
                        "sync",
                        "thumb_up",
                        "up_rate",
                        "version",
                        "rescan",
                    )
                ]
                + ["icons/%s.png" % x for x in ("restart", "settings", "shutdown", "st-gtk-logo")],
            ),
            ("share/man/man1", glob.glob("doc/*")),
            ("share/icons/hicolor/64x64/emblems", glob.glob("icons/emblem-*.png")),
            ("share/pixmaps", ["icons/syncthing-gtk.png"]),
            ("share/applications", ["syncthing-gtk.desktop"]),
            ("share/metainfo", ["me.kozec.syncthingtk.appdata.xml"]),
        ]
        + [
            ("share/icons/hicolor/%sx%s/apps" % (size, size), glob.glob("icons/%sx%s/apps/*" % (size, size)))
            for size in APP_ICON_SIZES
        ]
        + [
            ("share/icons/hicolor/%sx%s/status" % (size, size), glob.glob("icons/%sx%s/status/*" % (size, size)))
            for size in SI_ICON_SIZES
        ]
        + [("share/" + os.path.split(x)[0], (x,)) for x in find_mos("locale/")]
    )
    setup(
        name="syncthing-gtk",
        version=get_version(),
        description="GTK3 GUI for Syncthing",
        url="https://github.com/syncthing/syncthing-gtk",
        packages=["syncthing_gtk"],
        install_requires=(
            "python-dateutil",
            "bcrypt",
        ),
        data_files=data_files,
        scripts=["scripts/syncthing-gtk"],
    )
