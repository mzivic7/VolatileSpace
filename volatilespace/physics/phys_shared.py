from ast import literal_eval as leval
import math
import numpy as np
try:   # to allow building without numba
    from numba import njit, int32, float64, bool_
    numba_avail = True
except ImportError:
    numba_avail = False
from volatilespace import fileops


###### --Constants-- ######
c = 299792458   # speed of light in vacuum
k = 1.381 * 10**-23   # boltzman constant
m_h = 1.674 * 10**-27    # hydrogen atom mass in kg
m_he = 6.646 * 10**-27   # helium atom mass in kg
mp = (m_h * 99 + m_he * 1) / 100   # average particle mass   # depends on star age


###### --Functions-- ######
def dot_2d(v1, v2):
    """Fastest 2D dot product. It is slightly faster than built in: v1 @ v2."""
    return v1[0]*v2[0] + v1[1]*v2[1]


def mag(vector):
    """Vector magnitude"""
    return math.sqrt(dot_2d(vector, vector))


def cross_2d(v1, v2):
    """Faster than numpy's"""
    return np.array([v1[0]*v2[1] - v1[1]*v2[0]])


def orbit_time_to(source_angle, target_angle, period, dr):
    """Time to point on orbit"""
    time_to = period - (source_angle - target_angle) * (period / (2 * np.pi))
    if source_angle < target_angle:
        time_to = time_to - period
    if dr < 0:
        time_to = period - time_to
    return time_to


def newton_root(function, derivative, root_guess, variables={}):
    """General case newton root solver"""
    root = root_guess   # take guessed root input
    for _ in range(50):
        delta_x = function(root, variables) / derivative(root, variables)   # guess correction
        root -= delta_x   # better guess
        if abs(delta_x) < 1e-10:   # if correction is small enough:
            return root   # return root
    return root   # if it is not returned above (it has too high deviation) return it anyway


def newton_root_kepler_ell(ecc, ma, ea_guess):
    """Newton root solver for elliptic Keplers equation"""
    ea = ea_guess
    for _ in range(50):
        delta_x = (ea - ecc * np.sin(ea) - ma) / (1.0 - ecc * np.cos(ea))
        ea -= delta_x
        if abs(delta_x) < 1e-10:
            return ea
    return ea


def newton_root_kepler_hyp(ecc, ma, ea_guess):
    """Newton root solver for hyperbolic Keplers equation"""
    ea = ea_guess
    for _ in range(50):
        delta_x = (ea - ecc * np.sinh(ea) - ma) / (1.0 - ecc * np.cosh(ea))
        ea -= delta_x
        if abs(delta_x) < 1e-10:
            return ea
    return ea


def get_angle(a, b, c):
    """Angle between 3 points in 2D or 3D"""
    ba = a - b   # get 2 vectors from 3 points
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))   # angle between 2 vectors
    return np.arccos(cosine_angle)


def rot_ellipse_by_y(x, a, b, p):
    """Rotatted ellipse by y, but only positive half"""
    y = (a*b*math.sqrt(-x**2 * (math.cos(p)**4 + math.sin(p)**4) - 2 * x**2 * math.cos(p)**2 * math.sin(p)**2 + b**2 * math.sin(p)**2 + a**2 * math.cos(p)**2) + a**2 * x * math.sin(p) * math.cos(p) - b**2 * x * math.sin(p) * math.cos(p)) / (a**2 * math.cos(p)**2 + b**2 * math.sin(p)**2)
    return y


def rot_hyperbola_by_y(x, a, b, p):
    """Rotatted hyperbola by y, but only positive half"""
    y = -((a*b*math.sqrt(-x**2 * (math.cos(p)**4 + math.sin(p)**4) + 2 * x**2 * math.cos(p)**2 * math.sin(p)**2 + b**2 * math.sin(p)**2 - a**2 * math.cos(p)**2) + a**2 * x * math.sin(p) * math.cos(p) + b**2 * x * math.sin(p) * math.cos(p)) / (-a**2 * math.cos(p)**2 + b**2 * math.sin(p)**2))
    return y


def culling(curve, sim_screen, ref_coi, curve_points, cull):
    """Decides wether provided body/vessel should be drawn on screen"""
    sim_screen_size = np.absolute(sim_screen[1] - sim_screen[0])
    x_max = np.amax(curve[:, 0])   # numba does not support axis argument, yet
    y_max = np.amax(curve[:, 1])   # https://github.com/numba/numba/issues/1269
    x_min = np.amin(curve[:, 0])
    y_min = np.amin(curve[:, 1])
    diff = np.array([max(x_max - x_min, 1), max(y_max - y_min, 1)])
    screen_diff = sim_screen_size / diff
    if ref_coi != 0:
        if diff[0] + diff[1] > ref_coi * 3:
            screen_diff = sim_screen_size / np.array([ref_coi * 1.5, ref_coi * 1.5])
    if screen_diff[0] + screen_diff[1] < 130:
        if cull:
            factor = max(int(curve_points / 25), 4)
            curve = curve[0::factor]
            frame = max(sim_screen_size) / 4
            sc_x_max = np.max(sim_screen[:, 0]) + frame
            sc_y_max = np.max(sim_screen[:, 1]) + frame
            sc_x_min = np.min(sim_screen[:, 0]) - frame
            sc_y_min = np.min(sim_screen[:, 1]) - frame
            a = (curve >= np.array([sc_x_min, sc_y_min])) & (curve <= np.array([sc_x_max, sc_y_max]))
            if np.any(np.logical_and(a[:, 0], a[:, 1])):
                return True
        else:
            return True
    return False


# if numba is enabled, compile functions ahead of time
use_numba = leval(fileops.load_settings("game", "numba"))
if numba_avail and use_numba:
    enable_fastmath = leval(fileops.load_settings("game", "fastmath"))
    jitkw = {"cache": True, "fastmath": enable_fastmath}   # numba JIT setings
    dot_2d = njit(float64(float64[:], float64[:]), **jitkw)(dot_2d)
    mag = njit(float64(float64[:]), **jitkw)(mag)
    cross_2d = njit(float64[:](float64[:], float64[:]), **jitkw)(cross_2d)
    orbit_time_to = njit(float64(float64, float64, float64, float64), **jitkw)(orbit_time_to)
    newton_root_kepler_ell = njit(float64(float64, float64, float64), **jitkw)(newton_root_kepler_ell)
    newton_root_kepler_hyp = njit(float64(float64, float64, float64), **jitkw)(newton_root_kepler_hyp)
    culling = njit(bool_(float64[:, :], float64[:, :], float64, int32, bool_), **jitkw)(culling)
