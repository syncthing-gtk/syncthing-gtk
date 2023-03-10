#!/usr/bin/env python2
"""
Caja plugin for Syncthing-GTK
See syncthing_gtk/nautilusplugin.py for more info
"""

import os

from gi.repository import Caja

# Setting this environment variable will prevent __init__ in
# syncthing_gtk package from loading stuff that depends on GTK3-only
# features. It probably breaks other modules in most horrible ways,
# but they are not going to be used anyway
from syncthing_gtk.nautilusplugin import NautiluslikeExtension

os.environ["GTK2APP"] = "1"


NautiluslikeExtension.set_plugin_module(Caja)


class CajaNautilus(NautiluslikeExtension, Caja.InfoProvider, Caja.MenuProvider):
    pass
