#!/usr/bin/env python3
import os
import sys

import gi

def _main():
    """Main function. Callable from entrypoint in ``setup.py``."""

    path = os.path.dirname(os.path.realpath(__file__))
    localedir = os.path.join(path, "locale")

    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('Rsvg', '2.0')

    from syncthing_gtk.tools import init_locale, init_logging
    init_locale(localedir)
    init_logging()

    if "APPDIR" in os.environ:
        # Running as AppImage
        from gi.repository import Gtk
        Gtk.IconTheme.get_default().prepend_search_path(os.environ["APPDIR"])
        Gtk.IconTheme.get_default().prepend_search_path(os.environ["APPDIR"] + "/usr/share/icons/hicolor/32x32/apps")
        Gtk.IconTheme.get_default().prepend_search_path(os.environ["APPDIR"] + "/usr/share/icons/hicolor/32x32/status")

    from syncthing_gtk.app import App
    App(os.path.join(path, "glade"), os.path.join(path, "icons")).run(sys.argv)
