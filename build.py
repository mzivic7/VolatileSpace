import os
import shutil
from sys import platform

if platform == "win32":
    os.system('pipenv run pyinstaller --noconfirm --upx-dir=upx --onedir --windowed --clean --contents-directory "libraries" --icon "img/icon.ico" --name "VolatileSpace" "main.py"')
else:
    os.system('pipenv run python -m PyInstaller --noconfirm --onedir --windowed --clean --contents-directory "libraries" --name "VolatileSpace" "main.py"')

shutil.copytree('img/', 'dist/VolatileSpace/img/', dirs_exist_ok=True)
shutil.copytree('fonts/', 'dist/VolatileSpace/fonts/', dirs_exist_ok=True)
