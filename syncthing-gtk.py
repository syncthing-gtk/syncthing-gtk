#!/usr/bin/env python3
import os
import sys

import gi


if __name__ == "__main__":
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('Rsvg', '2.0')

    from syncthing_gtk.tools import IS_WINDOWS, init_locale, init_logging
    init_logging()

    if IS_WINDOWS:
        from syncthing_gtk.configuration import Configuration
        from syncthing_gtk.windows import enable_localization, fix_localized_system_error_messages, override_menu_borders
        config = Configuration()
        if config["force_dark_theme"]:
            os.environ["GTK_THEME"] = "Adwaita:dark"
        if config["language"] not in ("", "None", None):
            os.environ["LANGUAGE"] = config["language"]

        enable_localization()

    init_locale("locale/")

    if IS_WINDOWS:
        from syncthing_gtk.windows import enable_localization
        fix_localized_system_error_messages()
        override_menu_borders()
        from gi.repository import Gtk
        Gtk.IconTheme.get_default().prepend_search_path(
            os.path.abspath(os.path.join(os.getcwd(), "icons", "32x32", "apps")))
        Gtk.IconTheme.get_default().prepend_search_path(
            os.path.abspath(os.path.join(os.getcwd(), "icons")))

    from gi.repository import Gtk
    Gtk.IconTheme.get_default().prepend_search_path(
        os.path.join(os.getcwd(), "icons"))
    Gtk.IconTheme.get_default().prepend_search_path(
        os.path.join(os.getcwd(), "icons/32x32/status"))

    from syncthing_gtk.app import App
    App("./glade", "./icons").run(sys.argv)
