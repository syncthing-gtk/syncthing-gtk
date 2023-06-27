iconsdir = get_option('datadir') / 'icons' / 'hicolor'
pixmapsdir = get_option('datadir') / 'pixmaps'

run_target('generate-icons',
    command: find_program('generate_icons.py'),
)

foreach size : [16, 24, 32, 64, 128, 256]
    install_subdir(
        f'@size@x@size@',
        install_dir: iconsdir
    )
endforeach

install_data(
    'emblem-syncthing-active.png',
    'emblem-syncthing-error.png',
    'emblem-syncthing-offline.png',
    'emblem-syncthing.png',
    install_dir: iconsdir / '64x64' / 'emblems'
)

install_data(
    'add_node.svg',
    'add_repo.svg',
    'address.svg',
    'announce.svg',
    'clock.svg',
    'compress.svg',
    'cpu.svg',
    'dl_rate.svg',
    'eye.svg',
    'folder.svg',
    'global.svg',
    'home.svg',
    'ignore.svg',
    'lock.svg',
    'ram.svg',
    'rescan.svg',
    'restart.png',
    'settings.png',
    'shared.svg',
    'show_id.svg',
    'shutdown.png',
    'st-gtk-logo.png',
    'sync.svg',
    'thumb_up.svg',
    'up_rate.svg',
    'version.svg',
    install_dir: project_data_dir / 'icons'
)
