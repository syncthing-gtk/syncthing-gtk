#!/usr/bin/env python3
# pylint: disable=invalid-name
"""
Syncthing-Gtk top-level executable
"""

import os
import sys
from pathlib import Path
from typing import Optional

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Rsvg", "2.0")

# pylint: disable=wrong-import-position
from gi.repository import Gtk  # noqa: E402

from syncthing_gtk.app import App  # noqa: E402
from syncthing_gtk.tools import (  # noqa: E402
    init_locale,
    init_logging,
    IS_WINDOWS,
    get_install_path,
    make_portable,
)
from syncthing_gtk.configuration import Configuration  # noqa: E402

if IS_WINDOWS:
    from syncthing_gtk.windows import (  # noqa: E402
        enable_localization,
        fix_localized_system_error_messages,
        override_menu_borders,
    )
# pylint: disable=wrong-import-position


def check_if_source_directory():
    """
    Checks if this looks like we're running in a source directory.
    """
    source_path = Path(__file__).parent
    test_subpaths = ["LICENSE", "README.md", "syncthing_gtk", "setup.py", "po"]

    return all((source_path / subpath).exists() for subpath in test_subpaths)


def find_installation_directory() -> Optional[Path]:
    """
    Searches for the installation directory, and returns
    tuple(source_dir or None, locale_dir or None).
    """
    system_path = Path("/usr/share/syncthing-gtk")
    relative_path = Path(__file__).parent.parent / "share" / "syncthing-gtk"
    usrlocal_path = Path("/usr/local/share/syncthing-gtk")
    paths = (system_path, usrlocal_path, relative_path)

    install_path = next((path for path in paths if path.exists()), None)
    if install_path:
        return install_path

    return None


def windows_setup() -> None:
    """
    Expects PWD to be in the installation or source directory
    """
    config = Configuration()

    # Force dark theme if requested
    if config["force_dark_theme"]:
        os.environ["GTK_THEME"] = "Adwaita:dark"
    if config["language"] not in ("", "None", None):
        os.environ["LANGUAGE"] = config["language"]

    # Fix various windows-only problems
    enable_localization()
    fix_localized_system_error_messages()
    override_menu_borders()

    # Set icon directories
    icons_root = Path.cwd()
    Gtk.IconTheme.get_default().prepend_search_path(str(icons_root / "icons/32x32/apps"))
    Gtk.IconTheme.get_default().prepend_search_path(str(icons_root / "icons/32x32/status"))
    Gtk.IconTheme.get_default().prepend_search_path(str(icons_root))


if __name__ == "__main__":
    init_logging()

    data_path: Optional[Path]

    if "--portable" in sys.argv:
        sys.argv.remove("--portable")

        # Enable portable mode
        make_portable()

        # Running from current directory
        data_path = Path(__file__).parent

        storage_path = data_path / "data"
        if not storage_path.exists():
            print(f"creating {storage_path}")
            storage_path.mkdir(parents=True, exist_ok=True)

        os.environ["LOCALAPPDATA"] = str(storage_path)
        os.environ["APPDATA"] = str(storage_path)
        os.environ["XDG_CONFIG_HOME"] = str(storage_path)

        # Override syncthing_binary value in _Configuration class
        # FIXME: Should not be needed with latest refactoring
        # _Configuration.WINDOWS_OVERRIDE["syncthing_binary"] = (str, ".\\data\\syncthing.exe")

    elif check_if_source_directory():
        data_path = Path(__file__).parent

    elif data_path := find_installation_directory():
        pass

    elif IS_WINDOWS:
        # Running from C:/program files
        assert callable(get_install_path)  # Silent the mypy warning just after
        data_path = Path(get_install_path())

        os.environ["PATH"] = str(data_path)
        os.chdir(data_path)

    else:
        raise RuntimeError("Could not find installation directory, aborting!")

    if IS_WINDOWS:
        # It's not in the huge if..elif..elif because it should be run in all cases
        windows_setup()

    Gtk.IconTheme.get_default().prepend_search_path(str(data_path / "icons"))
    Gtk.IconTheme.get_default().prepend_search_path(str(data_path / "icons/32x32/status"))

    if "APPDIR" in os.environ:
        # Running as AppImage
        icon_subpaths = [
            "",
            "/usr/share/icons/hicolor/32x32/apps",
            "/usr/share/icons/hicolor/32x32/status",
        ]
        for subpath in icon_subpaths:
            Gtk.IconTheme.get_default().prepend_search_path(os.environ["APPDIR"] + subpath)

    init_locale(str(data_path / "locale"))
    App(str(data_path / "ui"), str(data_path / "icons")).run(sys.argv)
