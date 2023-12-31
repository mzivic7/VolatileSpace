import os
import shutil
import sys

if sys.platform == "win32":
    if sys.argv[1].lower() == "nonumba":
        os.system('pipenv run python -m PyInstaller --noconfirm --upx-dir=upx --onedir --exclude-module numba --windowed --clean --contents-directory "libraries" --icon "img/icon.ico" --name "VolatileSpace" "main.py"')
    else:
        os.system('pipenv run python -m PyInstaller --noconfirm --upx-dir=upx --onedir --windowed --clean --contents-directory "libraries" --icon "img/icon.ico" --name "VolatileSpace" "main.py"')
elif sys.platform == "linux":
    if sys.argv[1].lower() == "nonumba":
        os.system('pipenv run python -m PyInstaller --noconfirm --onedir --exclude-module numba --windowed --clean --contents-directory "libraries" --name "VolatileSpace" "main.py"')
    else:
        os.system('pipenv run python -m PyInstaller --noconfirm --onedir --windowed --clean --contents-directory "libraries" --name "VolatileSpace" "main.py"')
else:
    print("This platform is not supported: " + sys.platform)
    sys.exit()

shutil.copytree('img/', 'dist/VolatileSpace/img/', dirs_exist_ok=True)
shutil.copytree('fonts/', 'dist/VolatileSpace/fonts/', dirs_exist_ok=True)
shutil.copytree('parts/', 'dist/VolatileSpace/parts/', dirs_exist_ok=True)
