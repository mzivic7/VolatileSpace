import os
import shutil
import sys

args = [x.lower() for x in sys.argv]
numba_flag = ""
upx_flag = "--upx-dir=upx "
if "nonumba" in args:
    numba_flag = "--exclude-module numba "
if "noupx" in args:
    upx_flag = ""

if os.path.exists("dist/VolatileSpace"):
    shutil.rmtree("dist/VolatileSpace/")

if sys.platform == "win32":
    command = f'pipenv run python -m PyInstaller --noconfirm --onedir {upx_flag}{numba_flag}--windowed --clean --contents-directory "libraries" --icon "img/icon.ico" --name "VolatileSpace" "main.py"'
    os.system(command)
    if not os.path.exists("dist/VolatileSpace"):
        command = f'python -m PyInstaller --noconfirm --onedir {upx_flag}{numba_flag}--windowed --clean --contents-directory "libraries" --icon "img/icon.ico" --name "VolatileSpace" "main.py"'
        os.system(command)

elif sys.platform == "linux":
    command = f'pipenv run python -m PyInstaller --noconfirm --onedir {numba_flag}--windowed --clean --contents-directory "libraries" --name "VolatileSpace" "main.py"'
    os.system(command)

else:
    print("This platform is not supported: " + sys.platform)
    sys.exit()

shutil.copytree('img/', 'dist/VolatileSpace/img/', dirs_exist_ok=True)
shutil.copytree('fonts/', 'dist/VolatileSpace/fonts/', dirs_exist_ok=True)
shutil.copytree('parts/', 'dist/VolatileSpace/parts/', dirs_exist_ok=True)
shutil.copytree('documentation/', 'dist/VolatileSpace/documentation/', dirs_exist_ok=True)
shutil.copytree('maps_builtin/', 'dist/VolatileSpace/Maps/', dirs_exist_ok=True)
