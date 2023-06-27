# See https://docs.fedoraproject.org/en-US/packaging-guidelines/Meson/#_example_rpm_spec_file
%global _vpath_srcdir sdk/%{name}/projects/meson

Name:           syncthing-gtk
Version:        0.9.4.5
Release:        1%{?dist}
Summary:        A GTK UI for Syncthing

License:        GPLv2.0
URL:            https://github.com/syncthing-gtk/syncthing-gtk
Source:         %{url}/archive/v%{version}/syncthing-gtk-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  meson

BuildRequires:  pyproject-rpm-macros
BuildRequires:  sed

Requires:       gtk3

%global _description %{expand:
GTK3 & Python based GUI and notification area icon for Syncthing.

Supported Syncthing features

* Everything what WebUI can display
* Adding / editing / deleting nodes
* Adding / editing / deleting repositories
* Restart / shutdown server
* Editing daemon settings

Additional features

* First run wizard for initial configuration
* Running Syncthing daemon in background
* Half-automatic setup for new nodes and repositories
* Nautilus (a.k.a. Files), Nemo and Caja integration
* Desktop notifications}

%description %_description

%prep
%autosetup -c

%build
%meson
%meson_build

%install
%meson_install

%check
%meson_test

%files
%{_bindir}/syncthing-gtk
%{_libdir}/python3*/site-packages/syncthing_gtk
%{_datadir}/applications/syncthing-gtk.desktop
%{_datadir}/icons/hicolor/*/*/*syncthing*
%{_datadir}/locale/*/LC_MESSAGES/syncthing-gtk.mo
%{_datadir}/man/man1/syncthing-gtk*
%{_datadir}/metainfo/org.syncthing-gtk.syncthing-gtk.appdata.xml
%{_datadir}/pixmaps/syncthing-gtk.png
%{_datadir}/syncthing-gtk

%doc README.md

%changelog
* Sat Jun 25 2022 Manuel Amador <rudd-o@rudd-o.com> 0.9.4.4.1
- First RPM packaging release
