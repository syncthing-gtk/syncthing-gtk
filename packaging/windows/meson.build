configure_file(
    input: 'syncthing-gtk.wxs.in',
    output: 'syncthing-gtk.wxs',
    configuration: {
        'PRETTY_NAME': 'Syncthing-GTK',
        'VERSION': '0.10.0',

    }
)

custom_target(
    input: license,
    output: 'License.rtf',
    command: ['sh', files('txt2rtf.sh'), '@INPUT@', '@OUTPUT@'],
    build_by_default: true,
)
