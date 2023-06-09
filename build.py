import os
import shutil
from sys import platform

if platform == "win32":
    os.system('pyinstaller --noconfirm --onedir --windowed --clean --add-data "fonts;fonts/" --add-data "system.ini;." --add-data "settings.ini;." --name "VolatileSpace" "main.py"')
else:
    os.system('python -m PyInstaller --noconfirm --onedir --windowed --clean --add-data "fonts:fonts/" --add-data "system.ini:." --add-data "settings.ini:." --name "VolatileSpace" "main.py"')

os.remove('VolatileSpace.spec')
shutil.rmtree('build')
shutil.copytree('dist/', './', dirs_exist_ok=True)
shutil.rmtree('dist')

