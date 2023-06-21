project('syncthing-gtk',
    meson_version: '>=0.58.0',
)

pymod = import('python')
python = pymod.find_installation('python3')

project_name = meson.project_name()
python_module_name = project_name.underscorify()
project_data_dir = get_option('datadir') / project_name

# For windows packaging
license = files('LICENSE')

subdir('doc')
subdir('glade')
subdir('icons')
subdir('locale')
# subdir('scripts')
subdir('syncthing_gtk')
subdir('packaging')

install_data('syncthing-gtk.desktop',
    install_dir: get_option('datadir') / 'applications'
)

install_data('org.syncthing-gtk.syncthing-gtk.appdata.xml',
    install_dir: get_option('datadir') / 'metainfo'
)

install_data('scripts/syncthing-gtk',
    install_dir: get_option('bindir'),
)
