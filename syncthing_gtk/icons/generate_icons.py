#!/usr/bin/env python3

from typing import List, Optional
from pathlib import Path
import subprocess
import multiprocessing
import multiprocessing.pool
import shutil

ICONSDIR = Path(__file__).parent
TMPDIR = ICONSDIR / "tmp"

SIZES = [16, 24, 32]
COLORS = [
    ["background", "rot", ""],
    ["background-black", "rot", "black"],
    ["background-white", "rotblack", "white"],
]
FRAMES = range(12)


def inkscape_export(size: int, export_id: str):
    subprocess.check_output([
        "inkscape",
        ICONSDIR / "si-syncthing.svg",
        "--export-id-only",
        "--export-area-page",
        f"--export-width={size}",
        f"--export-height={size}",
        "--export-type=png",
        f"--export-id={export_id}",
        "-o", TMPDIR / f"si-syncthing-{size}-{export_id}.png"
    ])


def merge_icons(
    size: int, bg_export_id: str, fg_export_id: str, name_postfix: str,
    custom_args: Optional[List[str]] = None
):
    subprocess.check_output([
        "convert",
        TMPDIR / f"si-syncthing-{size}-{bg_export_id}.png",
        TMPDIR / f"si-syncthing-{size}-{fg_export_id}.png",
        "-gravity", "center", "-compose", "over", "-composite",
        *(custom_args or []),
        ICONSDIR / f"{size}x{size}/status/si-syncthing-{name_postfix}.png"
    ])


def merge_icons_for_warning(size: int, color: str):
    subprocess.check_output([
        "convert",
        ICONSDIR / f"{size}x{size}/status/si-syncthing-{color}idle.png",
        TMPDIR / f"si-syncthing-{size}-warning.png",
        "-gravity", "center", "-compose", "over", "-composite",
        ICONSDIR / f"{size}x{size}/status/si-syncthing-{color}warning.png",
    ])


def main():
    TMPDIR.mkdir(exist_ok=True)

    # First export the intermediate PNGs…
    inkscape_exports = []
    def add_inkscape_export(size, export_id):
        nonlocal inkscape_exports
        inkscape_exports.append((size, export_id))

    for size in SIZES:
        add_inkscape_export(size, "rot0")
        add_inkscape_export(size, "warning")

        for background, rotcolor, color in COLORS:
            add_inkscape_export(size, background)
            if color == "":
                continue
            add_inkscape_export(size, f"{rotcolor}-unknown")
            for frame in FRAMES:
                add_inkscape_export(size, f"{rotcolor}{frame}")

    threadpool = multiprocessing.pool.ThreadPool(multiprocessing.cpu_count() * 3 // 4)
    threadpool.starmap(inkscape_export, inkscape_exports)
    threadpool.close()
    threadpool.join()

    # Now generate the final PNGs
    for size in SIZES:
        for background, rotcolor, color in COLORS:
            if color != "":
                color += "-"
            merge_icons(size, background, f"{rotcolor}0", f"{color}0")
            merge_icons(size, background, f"{rotcolor}0", f"{color}idle")
            merge_icons(size, background, f"{rotcolor}0", f"{color}unknown", ["-colorspace", "Gray"])
            merge_icons_for_warning(size, color)
            for frame in FRAMES:
                merge_icons(size, background, f"{rotcolor}{frame}", f"{color}{frame}")

    shutil.rmtree(TMPDIR)


if __name__ == "__main__":
    main()
