#!/usr/bin/env python2
# pylint: disable=import-error,too-few-public-methods
"""
Nemo plugin for Syncthing-GTK
See syncthing_gtk/nautilusplugin.py for more info
"""
# pylint: disable=invalid-name

from gi.repository import Nemo

from syncthing_gtk.nautilusplugin import NautiluslikeExtension

NautiluslikeExtension.set_plugin_module(Nemo)


class SyncthingNemo(NautiluslikeExtension, Nemo.InfoProvider, Nemo.MenuProvider):
    """Browser extension wrapper"""
