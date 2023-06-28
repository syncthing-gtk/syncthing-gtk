#!/usr/bin/env python3
# pylint: disable=import-error,too-few-public-methods
"""
Nautilus plugin for Syncthing-GTK
See syncthing_gtk/nautilusplugin.py for more info
"""
# pylint: disable=invalid-name

from gi.repository import Nautilus  # pylint: disable=no-name-in-module

from syncthing_gtk.nautilusplugin import NautiluslikeExtension

NautiluslikeExtension.set_plugin_module(Nautilus)


class SyncthingNautilus(NautiluslikeExtension, Nautilus.InfoProvider, Nautilus.MenuProvider):
    """Browser extension wrapper"""
