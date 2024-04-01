from numba import njit
import numpy as np

def foo():
    intersections = np.array([np.nan, np.nan])
    print(intersections)
    print(np.isnan(intersections))

jitkw = {"cache": True, "fastmath": True}
foo = njit(**jitkw)(foo)
foo()
