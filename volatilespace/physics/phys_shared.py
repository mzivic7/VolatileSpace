from ast import literal_eval as leval
import math
import numpy as np
try:   # to allow building without numba
    from numba import njit, int64, float64, bool_
    from numba.types.misc import Omitted
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


def orbit_time_to(source_angle, target_angle, period, dr, neg_time=False):
    """Time to point on orbit"""
    time_to = period - (source_angle - target_angle) * (period / (2 * np.pi))
    if source_angle < target_angle:
        time_to = time_to - period
    if dr < 0:
        time_to = period - time_to
    if neg_time and time_to > period / 2:
        time_to -= period
    return time_to


def point_between(n, a, b, direction):
    """Returns True if angle n is between angles a and b in specified direction"""
    n = n % (2*np.pi)
    a = a % (2*np.pi)
    b = b % (2*np.pi)
    if direction < 0:
        a, b = b, a
    if a == b:
        if a == n:
            return True
        else:
            return False
    if a < b:
        return a <= n and n <= b
    else:
        return a <= n or n <= b


def newton_root(function, derivative, root_guess, variables={}):
    """General case newton root solver"""
    root = root_guess
    for _ in range(50):
        delta_x = function(root, variables) / derivative(root, variables)   # guess correction
        root -= delta_x   # better guess
        if abs(delta_x) < 1e-10:   # if correction is small enough:
            return root
    return root   # if it is not returned above (it has too high correction)


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


def curve_points(ecc, a, b, pea, t):
    """Calculates conic curve line points coordinates, rotated by periapsis argument."""
    sin_p = np.sin(pea)
    cos_p = np.cos(pea)
    if ecc < 1:   # ellipse
        x = a * np.cos(t)
        y = b * np.sin(t)
    else:   # hyperbola
        x = -a * np.cosh(t)
        y = b * np.sinh(t)
    # parametric equation for circle is same as for ellipse, just semi_major = semi_minor, thus it is not required
    # parabola is avoided, and made sure it won't happen. Very small number is added to ecc if ecc == 1.
    x_rot = x * cos_p - y * sin_p
    y_rot = y * cos_p + x * sin_p
    return np.stack((x_rot, y_rot), axis=1)


def curve_move_to(curves, body_pos, ref, f, pea):
    """Aligns focus of rotated curve points with its refernce body position. For multiple curves."""
    focus_x = f * np.cos(pea)
    focus_y = f * np.sin(pea)
    focus = np.column_stack((focus_x, focus_y))
    return curves + focus[:, np.newaxis, :] + body_pos[ref, np.newaxis, :]


def culling(coords, radius, screen_bounds, zoom):
    """Decides wether provided bodies should be drawn on screen,
    depending on their position and radius (if any)."""
    # swapping y axis because (0, 0) is in top left
    min_dim = (coords.T + radius).T + 2 / zoom > np.array([screen_bounds[0, 0], screen_bounds[1, 1]])
    max_dim = (coords.T - radius).T + 2 / zoom < np.array([screen_bounds[1, 0], screen_bounds[0, 1]])
    min_dim_xy = np.logical_and(min_dim[:, 0], min_dim[:, 1])   # numba does not support axis argument, yet
    max_dim_xy = np.logical_and(max_dim[:, 0], max_dim[:, 1])   # https://github.com/numba/numba/issues/1269
    return np.logical_and(min_dim_xy, max_dim_xy)


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
    orbit_time_to = njit([float64(float64, float64, float64, float64, Omitted(False)),
                          float64(float64, float64, float64, float64, bool_)],
                         **jitkw)(orbit_time_to)
    point_between = njit(bool_(float64, float64, float64, int64), **jitkw)(point_between)
    newton_root_kepler_ell = njit(float64(float64, float64, float64), **jitkw)(newton_root_kepler_ell)
    newton_root_kepler_hyp = njit(float64(float64, float64, float64), **jitkw)(newton_root_kepler_hyp)
    rot_ellipse_by_y = njit(float64(float64, float64, float64, float64), **jitkw)(rot_ellipse_by_y)
    rot_hyperbola_by_y = njit(float64(float64, float64, float64, float64), **jitkw)(rot_hyperbola_by_y)
    impl_derivative_rot_ell = njit(float64(float64, float64, float64, float64, float64), **jitkw)(impl_derivative_rot_ell)
    impl_derivative_rot_hyp = njit(float64(float64, float64, float64, float64, float64), **jitkw)(impl_derivative_rot_hyp)
    curve_points = njit(float64[:, :](float64, float64, float64, float64, float64[:]), **jitkw)(curve_points)
    curve_move_to = njit(float64[:, :, :](float64[:, :, :], float64[:, :], int64[:], float64[:], float64[:]), **jitkw)(curve_move_to)
    culling = njit(bool_[:](float64[:, :], float64[:], float64[:, :], float64), **jitkw)(culling)
