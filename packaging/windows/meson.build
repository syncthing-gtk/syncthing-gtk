configure_file(
    input: 'syncthing-gtk.wxs.in',
    output: 'syncthing-gtk.wxs',
    configuration: {
        'PRETTY_NAME': 'Syncthing-GTK',
        'VERSION': '0.9.4.5',

    }
)

custom_target(
    input: license,
    output: 'License.rtf',
    command: [find_program('txt2rtf.sh'), '@INPUT@', '@OUTPUT@'],
    build_by_default: true,
)
