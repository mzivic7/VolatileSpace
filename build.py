import argparse
import os
import shutil
import sys

APP_NAME = "VolatileSpace"


def build(nonumba, noupx):
    """Build"""
    if os.path.exists("dist/VolatileSpace/"):
        shutil.rmtree("dist/VolatileSpace/")
    hidden_imports = ""
    if nonumba:
        numba = "--exclude-module numba "
    else:
        numba = ""
    if noupx:
        upx = ""
    else:
        upx = "--upx-dir=upx "

    if sys.platform == "linux":
        command = f'uv run python -m PyInstaller {hidden_imports}--noconfirm {numba}--windowed --clean --contents-directory "libraries" --name {APP_NAME} "main.py"'
        os.system(command)
    elif sys.platform == "win32":
        command = f'uv run python -m PyInstaller {hidden_imports}--noconfirm {upx}{numba}--windowed --clean --contents-directory "libraries" --icon "images/icon.ico" --name {APP_NAME} "main.py"'
        os.system(command)
    elif sys.platform == "darwin":
        command = f'uv run python -m PyInstaller {hidden_imports}--noconfirm {numba}--windowed --clean --contents-directory "libraries" --icon "images/icon.ico" --name {APP_NAME} "main.py"'
        os.system(command)
    else:
        sys.exit(f"This platform is not supported: {sys.platform}")

    shutil.copytree("images/", "dist/VolatileSpace/images/", dirs_exist_ok=True)
    shutil.copytree("fonts/", "dist/VolatileSpace/fonts/", dirs_exist_ok=True)
    shutil.copytree("parts/", "dist/VolatileSpace/parts/", dirs_exist_ok=True)
    shutil.copytree("documentation/", "dist/VolatileSpace/documentation/", dirs_exist_ok=True)
    shutil.copytree("maps_builtin/", "dist/VolatileSpace/Maps/", dirs_exist_ok=True)

    # cleanup
    try:
        os.remove(f"{APP_NAME}.spec")
        shutil.rmtree("build")
    except FileNotFoundError:
        pass


def parser():
    """Setup argument parser for CLI"""
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="Setup and build script for endcord",
    )
    parser._positionals.title = "arguments"
    parser.add_argument(
        "--nonumba",
        action="store_true",
        help="Change environment to build or run without numba support",
    )
    parser.add_argument(
        "--noupx",
        action="store_true",
        help="Build without UPX, useful only on windows",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parser()
    build(args.nonumba, args.noupx)
