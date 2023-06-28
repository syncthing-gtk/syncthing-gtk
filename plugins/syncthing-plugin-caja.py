#!/usr/bin/env python2
# pylint: disable=import-error,too-few-public-methods
"""
Caja plugin for Syncthing-GTK
See syncthing_gtk/nautilusplugin.py for more info
"""
# pylint: disable=invalid-name
import os
from gi.repository import Caja  # pylint: disable=no-name-in-module

from syncthing_gtk.nautilusplugin import NautiluslikeExtension

NautiluslikeExtension.set_plugin_module(Caja)


class CajaNautilus(NautiluslikeExtension, Caja.InfoProvider, Caja.MenuProvider):
    """Browser extension wrapper"""


# Setting this environment variable will prevent __init__ in
# syncthing_gtk package from loading stuff that depends on GTK3-only
# features. It probably breaks other modules in most horrible ways,
# but they are not going to be used anyway

os.environ["GTK2APP"] = "1"
