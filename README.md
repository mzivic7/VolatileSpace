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
5. run build script: `python build.py`

### Windows
1. Install [Python](https://www.python.org/) 3.10 or later
2. Install [pipenv](https://docs.pipenv.org/install/)
3. Clone this repository, unzip it
4. Open terminal, cd to unzipped folder
5. Install requirements: `pipenv install`
6. Run build script: `python build.py`

### About numba
Numba will add ~3-60s to first launch, and ~5-10s to every after (if numba is enabled in settings).  
build.py script by default builds with numba, to build without numba use: `python build.py nonumba`  
Or just uninstall numba: `pipenv uninstall numba`  
This also disables 'Numba' and 'FastMath' options in settings.  

## How it works?
Head to [wiki](documentation/wiki.md).
