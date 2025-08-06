import math

import numpy as np

try:
    from numba import float64, int32, njit
    from numba.types import UniTuple
    numba_avail = True
except ImportError:
    numba_avail = False
from volatilespace import peripherals
from volatilespace.physics.enhanced_kepler_solver import solve_kepler_ell
from volatilespace.physics.phys_shared import newton_root_kepler_hyp
from volatilespace.physics.quartic_solver import solve_quartic


def ell_hyp_intersect_circle(a, b, ecc, c_x, c_y, r):
    """
    Calculate eccentric anomalies of intersecting points
    on non-rotated ellipse/hyperbola in origin, and translated circle
    """
    # quartic equation coefficients
    if ecc < 1:    # ellipse
        a_0 = a**2 - 2*a*c_x + c_x**2 + c_y**2 - r**2
        a_1 = -4*b*c_y
        a_2 = -2*a**2 + 4*b**2 + 2*c_x**2 + 2*c_y**2 - 2*r**2
        a_3 = -4*b*c_y
        a_4 = a**2 + 2*a*c_x + c_x**2 + c_y**2 - r**2
        # quartic equation roots
        roots = solve_quartic(a_4, a_3, a_2, a_1, a_0)
        # take only non-complex roots
        real_roots = np.array([x.real for x in roots if not x.imag])
        if np.any(real_roots):
            ea = np.arctan2(2 * real_roots, 1.0 - real_roots**2)
            return ea % (2*np.pi)
        return np.array([np.nan])
    # hyperbola
    a_0 = -a**2 * (c_y**2 + b**2) + b**2 * (c_x + r)**2
    a_1 = -4 * a**2 * r * c_y
    a_2 = -2 * (a**2 * (c_y**2 + b**2 + 2*r**2) + b**2 * (r**2 - c_x**2))
    a_3 = -4 * a**2 * r * c_y
    a_4 = -a**2 * (c_y**2 + b**2) + b**2 * (c_x - r)**2
    roots = solve_quartic(a_4, a_3, a_2, a_1, a_0)
    real_roots = np.array([x.real for x in roots if not x.imag])
    if np.any(real_roots):
        x = c_x + r * (1-real_roots**2) / (1 + real_roots**2)   # point coordinates
        y = c_y + r * 2 * real_roots / (1 + real_roots**2)
        ta = np.arctan2(y, x - (a * ecc))   # ta from coordinates
        ea = np.arccosh((ecc + np.cos(ta))/(1 + (ecc * np.cos(ta))))   # ea from ta
        # ea is in (-pi, pi) range because curve calculations get messed up if it is not
        return np.where(real_roots < 0, -ea, ea)
    return np.array([np.nan])


def next_point(ea_vessel, ea_points, direction):
    """Find next and previous point on orbit in ea_points, from ea_vessel, in orbit direction."""
    if not np.any(np.isnan(ea_points)):
        angle = np.abs(ea_vessel - ea_points)
        # where ea_vessel is larger: invert
        angle = np.where(ea_vessel > ea_points, 2*np.pi - angle, angle)
        if direction < 0:   # if direction is clockwise: invert
            angle = np.pi*2 - angle
        ea_points_sorted = ea_points[np.argsort(angle)]
        return np.array([ea_points_sorted[0], ea_points_sorted[-1]])
    return np.array([np.nan, np.nan])


def sort_intersect_indices(ea_vessel, ea_points, direction):
    """Sort points on orbit by their angular (ea) distance from vessel in specified direction"""
    if not np.all(np.isnan(ea_points)):
        angle = np.where(np.isnan(ea_points), np.nan, np.abs(ea_vessel - ea_points))
        # where ea_vessel is larger: invert
        angle = np.where(ea_vessel > ea_points, 2*np.pi - angle, angle)
        if direction < 0:   # if direction is clockwise: invert
            angle = np.pi*2 - angle
        ea_points_sorted = np.argsort(angle)
        # returning -1 instead np.nan because np.nan is special float
        return np.where(np.isnan(ea_points[ea_points_sorted]), -1, ea_points_sorted)
    return np.array([np.nan])


def norm2d(dx, dy):
    """Replacement for np.linalg.norm without scipy"""
    return (dx * dx + dy * dy) ** 0.5


def wrap_angle(angle):
    """Keep angle in (0, 2pi) range"""
    if angle >= 2 * math.pi:
        return angle - 2 * math.pi
    if angle < 0:
        return angle + 2 * math.pi
    return angle


def orb2xy(a, b, f, ecc, pea, ea):
    """Calculate relative x and y coordinates from orbital parameters"""
    if ecc < 1:
        x_n = a * np.cos(ea) - f
        y_n = b * np.sin(ea)
    else:
        x_n = a * np.cosh(ea) - f
        y_n = b * np.sinh(ea)
    x = (x_n * np.cos(pea - np.pi) - y_n * np.sin(pea - np.pi))
    y = (x_n * np.sin(pea - np.pi) + y_n * np.cos(pea - np.pi))
    return (x, y)


def move(ma, ecc, dr, n, prev_ea, dt):
    """Move vessel or body"""
    if ecc < 1:
        ma += dr * n * dt
        if ma > 2*np.pi:
            ma - 2*np.pi
        elif ma < 0:
            ma + 2*np.pi
        ea = solve_kepler_ell(ecc, ma, 1e-10)
    else:
        ma += dr * n * -1 * dt
        ea = newton_root_kepler_hyp(ecc, ma, prev_ea)
        prev_ea = ea
    return ma, ea, prev_ea


def predict_enter_coi(vessel_data, body_data, tol, steps_limit):
    """Search for first enter COI point for given vessel and body, which are orbiting same reference"""
    a, b, f, ecc, ma, ea, pea, period, n, dr = vessel_data
    b_a, b_b, b_f, b_ecc, b_ma, b_ea, b_pea, b_n, b_dr, b_coi = body_data
    prev_ea = ea
    b_prev_ea = b_ea

    if not period or not b_coi:
        return np.nan, np.nan, np.nan, np.nan, np.nan

    t = 0
    # fit planet COI radius in vessel orbit * 5 to compensate for eccentricity and make it easier to refine
    steps = int(max(min(period / b_coi * 5, period / 2), period / 30))
    steps = max(steps, steps_limit)
    dt = period / steps   # larger the period - larger the step
    t_end = period   # only one full orbit
    while t < t_end:

        # move vessel and body
        ma, ea, prev_ea = move(ma, ecc, dr, n, prev_ea, dt)
        b_ma, b_ea, b_prev_ea = move(b_ma, b_ecc, b_dr, b_n, b_prev_ea, dt)

        # calculate positions
        rvx, rvy = orb2xy(a, b, f, ecc, pea, ea)
        rbx, rby = orb2xy(b_a, b_b, b_f, b_ecc, b_pea, b_ea)
        d = norm2d(rvx - rbx, rvy - rby)

        # refine results
        if d < b_coi:
            for _ in range(30):
                # go in the direction of intersection
                dt = abs(dt) / 2 * (-1 if d < b_coi else 1)
                t += dt

                # move vessel and body back
                ma, ea, prev_ea = move(ma, ecc, dr, n, prev_ea, dt)
                b_ma, b_ea, b_prev_ea = move(b_ma, b_ecc, b_dr, b_n, b_prev_ea, dt)

                # calculate positions
                rvx, rvy = orb2xy(a, b, f, ecc, pea, ea)
                rbx, rby = orb2xy(b_a, b_b, b_f, b_ecc, b_pea, b_ea)
                d = norm2d(rvx - rbx, rvy - rby)

                # check if result is acceptable
                if abs(d - b_coi) < tol:
                    return wrap_angle(ea), wrap_angle(b_ea), wrap_angle(ma), wrap_angle(b_ma), t
            return wrap_angle(ea), wrap_angle(b_ea), wrap_angle(ma), wrap_angle(b_ma), t

        t += dt
    return np.nan, np.nan, np.nan, np.nan, np.nan


# if numba is enabled, compile functions ahead of time
use_numba = peripherals.load_settings("game", "numba")
if numba_avail and use_numba:
    enable_fastmath = peripherals.load_settings("game", "fastmath")
    jitkw = {"cache": True, "fastmath": enable_fastmath}   # numba JIT setings
    # disabling fastmath for some functions with np.isnan()
    jitkw_nofast = {"cache": True, "fastmath": False}
    ell_hyp_intersect_circle = njit(float64[:](float64, float64, float64, float64, float64, float64), **jitkw)(ell_hyp_intersect_circle)
    next_point = njit(float64[:](float64, float64[:], float64), **jitkw_nofast)(next_point)
    norm2d = njit(float64(float64, float64), **jitkw)(norm2d)
    wrap_angle = njit(float64(float64), **jitkw)(wrap_angle)
    orb2xy = njit(UniTuple(float64, 2)(float64, float64, float64, float64, float64, float64), **jitkw)(orb2xy)
    move = njit(UniTuple(float64, 3)(float64, float64, float64, float64, float64, float64), **jitkw)(move)
    predict_enter_coi = njit(UniTuple(float64, 5)(UniTuple(float64, 10), UniTuple(float64, 10), float64, int32), **jitkw)(predict_enter_coi)
