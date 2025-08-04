# Volatile Space
2D physics-based universe and spaceflight simulator.  
Written in Python with pygame-ce.  
[Download](https://mzivic.itch.io/volatile-space) (itch.io)  
[Wiki](documentation/wiki.md)  


## Building
### Linux
1. Clone this repository: `git clone https://github.com/mzivic7/VolatileSpace.git`
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
3. `cd endcord`
4. Setup virtual environment: `uv sync --all-groups`
5. run build script: `uv run build.py`

#### Optional - Compiling pygame with llvm
Linux build can be optimized for performance by compiling pygame locally with llvm instead of gcc.  
After build step 4:
1. Uninstall already present pygame: `uv pip uninstall pygame-ce`
2. Change compiler to clang/llvm: `export CC=/usr/bin/clang`
3. Tell pip to build pygame from source: `export PIP_NO_BINARY=pygame-ce`
4. Install pygame: `uv add pygame-ce`
5. Now run build script: `uv run build.py`

### Windows
1. Install [Python](https://www.python.org/) 3.12 or later
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
3. Clone this repository, unzip it
4. Open terminal, cd to unzipped folder
5. Setup virtual environment: `uv sync --all-groups`
6. Run build script: `uv run  build.py`
> [!NOTE]  
> If built executable does not launch, try building with UPX disabled, see [UPX](#upx).

### numba
[Numba](https://numba.pydata.org/) will significantly optimize simulation physics and math.  
It is recommended to run this simulator with numba.  
Numa will add 30-60s to first launch, and 1-10s to every after (if numba is enabled in settings).  
build.py script by default builds with numba, to build without numba add this flag when running build.py: `--nonumba`  
Or just uninstall numba: `uv pip uninstall numba`  
This also disables 'Numba' and 'FastMath' options in settings.  

### UPX
[UPX](https://upx.github.io/) is an executable file compressor. It significantly reduces the total size of built executable.  
On Windows, UPX directory called "upx" should be placed inside project directory.  
on Linux, PyInstaller (used to build binary package) does not support UPX.  
If installeed, build.py script by default runs UPX. To build without UPX add this flag when running build.py: `--noupx`  

## How does it work?
Head to [wiki](documentation/wiki.md).
