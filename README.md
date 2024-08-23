# Volatile Space
2D physics-based universe and spaceflight simulator.  
Written in Python with pygame-ce.  
[Download](https://mzivic.itch.io/volatile-space) (itch.io)  
[Wiki](documentation/wiki.md)  


## Building
### Linux
1. Clone this repository: `git clone https://github.com/mzivic7/VolatileSpace.git`
2. Install [pipenv](https://docs.pipenv.org/install/)
3. `cd VolatileSpace`
4. Install requirements: `pipenv install --dev`
5. run build script: `pipenv run python build.py`
#### Optional - Compiling pygame with llvm
Linux build can be optimized for performance by compiling pygame locally with llvm instead of gcc  
1. Uninstall already present pygame: `pipenv uninstall pygame-ce`
2. Change compiler to clang/llvm: `export CC=/usr/bin/clang`
3. Tell pip(env) to build pygame from source: `export PIP_NO_BINARY=pygame-ce`
4. Install pygame: `pipenv install pygame-ce`

### Windows
1. Install [Python](https://www.python.org/) 3.12 or later
2. Install [pipenv](https://docs.pipenv.org/install/) (optional)
3. Clone this repository, unzip it
4. Open terminal, cd to unzipped folder
5. Install requirements: `pipenv install`
6. additional dependency for windows: `pipenv install pywin32`
7. Run build script: `pipenv run python build.py`
#### Without pipenv:  
5. Open `Pipfile` with text editor and install all packages and dev-packages with pip.  
6. With addition of `pywin32`.
7. Then run build script: `python build.py`
> [!NOTE]  
> If built executable does not launch, try building with UPX disabled, see [UPX](#upx).

### numba
[Numba](https://numba.pydata.org/) will significantly optimize simulation physics and math and is recommended to run this simulator with it.
It will add 30-60s to first launch, and 1-10s to every after (if numba is enabled in settings).  
build.py script by default builds with numba, to build without numba use: `python build.py nonumba`  
Or just uninstall numba: `pipenv uninstall numba`  
This also disables 'Numba' and 'FastMath' options in settings.  

### UPX
[UPX](https://upx.github.io/) is an advanced executable file compressor. It significantly reduces the total size of built executable.  
On Windows, UPX directory called "upx" should be placed inside project directory.  
on Linux, PyInstaller (used to build binary package) does not support up.  
build.py script by default runs UPX, to build without UPX use: `python build.py noupx` (arguments can be stacked).  
Or just don't install it.  


## How it works?
Head to [wiki](documentation/wiki.md).
