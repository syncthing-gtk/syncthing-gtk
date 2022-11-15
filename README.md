# Syncthing-GTK

Syncthing-GTK is a GTK-based user interface for [Syncthing](https://github.com/syncthing/syncthing).

It was originally developed by [Kozec](https://github.com/kozec), then maintained in <https://github.com/syncthing-gtk/syncthing-gtk>.

[![screenshot1](http://i.imgur.com/N36wmBM.png)](http://i.imgur.com/eX250tQ.png) [![screenshot2](http://i.imgur.com/43mmnC7.png)](http://i.imgur.com/RTRgRdC.png) [![screenshot3](http://i.imgur.com/KDBYekd.png)](http://i.imgur.com/OZ4xEeH.jpg)

## Supported Syncthing features

- Everything what WebUI can display
- Adding / editing / deleting nodes
- Adding / editing / deleting repositories
- Restart / shutdown server
- Editing daemon settings

## Additional features

- First run wizard for initial configuration
- Running Syncthing daemon in background
- Half-automatic setup for new nodes and repositories
- Nautilus (a.k.a. Files), Nemo and Caja integration
- Desktop notifications

## How to install

### On most Linux distributions

Packages are available on most linux distributions as `syncthing-gtk` or `syncthing-gtk-python3`.

### On Windows

Get the installer [here](https://github.com/syncthing-gtk/syncthing-gtk/releases/latest).

## Dependencies

- Syncthing >= 0.13
- Python3 >= 3.7
  - [setuptools](https://pypi.python.org/pypi/setuptools)
- GTK+3 >= 3.12
- [PyGObject](https://live.gnome.org/PyGObject)
  - [python-gi-cairo](https://packages.debian.org/sid/python-gi-cairo),
  - [gir1.2-notify](https://packages.debian.org/sid/gir1.2-notify-0.7)
  - [gir1.2-rsvg](https://packages.debian.org/sid/gir1.2-rsvg-2.0) on debian based distros (included in PyGObject elsewhere)
- [python-dateutil](http://labix.org/python-dateutil)
- [python-bcrypt](https://pypi.python.org/pypi/bcrypt/2.0.0)
- [psmisc](http://psmisc.sourceforge.net) (for the `killall` command)

### Optional Dependencies

- libnotify for desktop notifications.
- nautilus-python, nemo-python or caja-python for filemanager integration
- [this Gnome Shell extension](https://extensions.gnome.org/extension/615/appindicator-support/), if running Gnome Shell
- [gir1.2-appindicator3](https://packages.debian.org/sid/gir1.2-appindicator3-0.1) (part of [libappindicator](https://launchpad.net/libappindicator)), if running Gnome Shell or Unity

### Windows builder dependencies

- [PyGObject for Windows](http://sourceforge.net/projects/pygobjectwin32/) with GTK3 enabled (tested with version 3.14.0)
- [Python for Windows Extensions](http://sourceforge.net/projects/pywin32/)
- [WMI](http://timgolden.me.uk/python/wmi/index.html)
- [NSIS2](http://nsis.sourceforge.net/NSIS_2) with NSISdl, [ZipDLL](http://nsis.sourceforge.net/ZipDLL_plug-in) and [FindProcDLL](http://forums.winamp.com/showpost.php?p=2777729&postcount=8) plugins (optional, for building installer)

## How to build

TODO:

## Related links

- <https://syncthing.net>
- <https://forum.syncthing.net/t/syncthing-gtk-gui-for-syncthing-now-with-inotify-support/709>
- <https://forum.syncthing.net/t/lxle-a-respin-of-lubuntu-now-has-syncthing-included-by-default/1392>
