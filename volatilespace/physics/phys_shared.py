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


def compare(a, b):
    """Compares 2 values and returns percentage difference"""
    if a == b:
        return 0.0
    elif 0 in (a, b):
        return 100.0
    elif a > 0 and b > 0:
        return abs(a - b) / max(a, b) * 100
    elif a < 0 and b < 0:
        a = abs(a)
        b = abs(b)
        return abs(a - b) / max(a, b) * 100
    else:   # skipping negative
        return 100


def compare_coord(a, b):
    """Compares 2 coordinates and returns percentage difference"""
    p = compare(a[0], b[0])
    q = compare(a[1], b[1])
    return (p + q) / 2


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
    """Newton root solver for elliptic Kepler's equation"""
    ea = ea_guess
    for _ in range(50):
        delta_x = (ea - ecc * np.sin(ea) - ma) / (1.0 - ecc * np.cos(ea))
        ea -= delta_x
        if abs(delta_x) < 1e-10:
            return ea
    return ea


def newton_root_kepler_hyp(ecc, ma, ea_guess):
    """Newton root solver for hyperbolic Kepler's equation"""
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
    sin_p = math.sin(p)
    cos_p = math.cos(p)
    a2 = a**2
    b2 = b**2
    x2 = x**2
    sin_p2 = sin_p**2
    cos_p2 = cos_p**2
    y = (a*b*math.sqrt(-x2 * (cos_p**4 + sin_p**4) - 2 * x2 * cos_p2 * sin_p2 + b2 * sin_p2 + a2 * cos_p2)
         + a2 * x * sin_p * cos_p - b2 * x * sin_p * cos_p) / (a2 * cos_p2 + b2 * sin_p2)
    return y


def rot_hyperbola_by_y(x, a, b, p):
    """Rotatted hyperbola by y, but only positive half"""
    sin_p = math.sin(p)
    cos_p = math.cos(p)
    a2 = a**2
    b2 = b**2
    x2 = x**2
    sin_p2 = sin_p**2
    cos_p2 = cos_p**2
    y = -((a*b*math.sqrt(-x2 * (cos_p**4 + sin_p**4) + 2 * x2 * cos_p2 * sin_p2 + b2 * sin_p2 - a2 * cos_p2)
           + a2 * x * sin_p * cos_p + b2 * x * sin_p * cos_p) / (-a2 * cos_p2 + b2 * sin_p2))
    return y


def impl_derivative_rot_ell(p_x, p_y, a, b, p):
    """Implicite derivative of rotated ellipse"""
    sin_p = math.sin(p)
    cos_p = math.cos(p)
    a2 = a**2
    b2 = b**2
    sin_cos_p = sin_p * cos_p
    sin_p2 = sin_p**2
    cos_p2 = cos_p**2
    derivative = np.arctan(
        - (b2 * p_x * cos_p2 + a2 * p_x * sin_p2 + b2 * p_y * sin_cos_p - a2 * p_y * sin_cos_p)
        / (a2 * p_y * cos_p2 + b2 * p_y * sin_p2 + b2 * p_x * sin_cos_p - a2 * p_x * sin_cos_p))
    return derivative


def impl_derivative_rot_hyp(p_x, p_y, a, b, p):
    """Implicite derivative of rotated hyperbola"""
    sin_p = math.sin(p)
    cos_p = math.cos(p)
    a2 = a**2
    b2 = b**2
    sin_cos_p = sin_p * cos_p
    sin_p2 = sin_p**2
    cos_p2 = cos_p**2
    derivative = np.arctan(
        - (+ b2 * p_x * cos_p2 - a2 * p_x * sin_p2 + b2 * p_y * sin_cos_p + a2 * p_y * sin_cos_p)
        / (- a2 * p_y * cos_p2 + b2 * p_y * sin_p2 + b2 * p_x * sin_cos_p + a2 * p_x * sin_cos_p))
    return derivative


def orb2xy(a, b, f, ecc, pea, pos, ea):
    """ Calculate relative x and y coordinates from orbital parameters"""
    if ea:
        if ecc < 1:
            x_n = a * np.cos(ea) - f
            y_n = b * np.sin(ea)
        else:
            x_n = a * np.cosh(ea) - f
            y_n = b * np.sinh(ea)
        x = (x_n * np.cos(pea - np.pi) - y_n * np.sin(pea - np.pi)) + pos[0]
        y = (x_n * np.sin(pea - np.pi) + y_n * np.cos(pea - np.pi)) + pos[1]
        return np.array(([x, y]))
    else:
        return np.array(([None, None]))


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
    compare = njit(float64(float64, float64), **jitkw)(compare)
    compare_coord = njit(float64(float64[:], float64[:]), **jitkw)(compare_coord)
    orbit_time_to = njit(float64(float64, float64, float64, float64), **jitkw)(orbit_time_to)
    newton_root_kepler_ell = njit(float64(float64, float64, float64), **jitkw)(newton_root_kepler_ell)
    newton_root_kepler_hyp = njit(float64(float64, float64, float64), **jitkw)(newton_root_kepler_hyp)
    rot_ellipse_by_y = njit(float64(float64, float64, float64, float64), **jitkw)(rot_ellipse_by_y)
    rot_hyperbola_by_y = njit(float64(float64, float64, float64, float64), **jitkw)(rot_hyperbola_by_y)
    impl_derivative_rot_ell = njit(float64(float64, float64, float64, float64, float64), **jitkw)(impl_derivative_rot_ell)
    impl_derivative_rot_hyp = njit(float64(float64, float64, float64, float64, float64), **jitkw)(impl_derivative_rot_hyp)
    culling = njit(bool_(float64[:, :], float64[:, :], float64, int32, bool_), **jitkw)(culling)
