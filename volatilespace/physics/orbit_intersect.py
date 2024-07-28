from ast import literal_eval as leval
import numpy as np
try:
    from numba import njit, float64
    from numba.types import UniTuple
    from numba.types.misc import Omitted
    numba_avail = True
except ImportError:
    numba_avail = False
from volatilespace import fileops
from volatilespace.physics.phys_shared import orbit_time_to, \
    newton_root_kepler_ell, newton_root_kepler_hyp, point_between
from volatilespace.physics.quartic_solver import solve_quartic


def ell_hyp_intersect(a, b, ecc, c_x, c_y, r):
    """Calculate eccentric anomalies of intersecting points
    on non-rotated ellipse/hyperbola in origin, and translated circle"""
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
        else:
            return np.array([np.nan])
    else:   # hyperbola
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
            # ea is in (-pi, pi) range because curve calculations got messed up if it is not
            ea = np.where(real_roots < 0, -ea, ea)
            return ea
        else:
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
    else:
        return np.array([np.nan, np.nan])


def sort_intersect_indices(ea_vessel, ea_points, direction):
    """Sorts points on orbit by their angular (ea) distance from vessel in specified direction"""
    if not np.all(np.isnan(ea_points)):
        angle = np.where(np.isnan(ea_points), np.nan, np.abs(ea_vessel - ea_points))
        # where ea_vessel is larger: invert
        angle = np.where(ea_vessel > ea_points, 2*np.pi - angle, angle)
        if direction < 0:   # if direction is clockwise: invert
            angle = np.pi*2 - angle
        ea_points_sorted = np.argsort(angle)
        # returning -1 instead np.nan because np.nan is special float
        ea_points_sorted = np.where(np.isnan(ea_points[ea_points_sorted]), -1, ea_points_sorted)
        return ea_points_sorted
    else:
        return np.array([np.nan])


def gen_probe_points_ell(t1, t2, num):
    """Generates specified number of probe points from specified range with wrapping at 2pi.
    Returned points are in reverse order, those closer to t2 are first."""
    if t1 < t2 or t2 == 0:
        probe_points = np.linspace(t1, t2, int(num))
    else:
        ratio = (2*np.pi - t1) / t2
        num_1 = int(num * ratio)
        num_2 = int(num - num_1)
        probe_points_1 = np.linspace(t1, 2*np.pi, num_1)
        probe_points_2 = np.linspace(0, t2, num_2)
        probe_points = np.concatenate((probe_points_1, probe_points_2))
    return probe_points


default_probe_points_ravel = True
probe_points_num = 16
extra_optimize_iterations = 10


# generate default probe points
if probe_points_num % 2:
    probe_points_num -= 1
default_probe_points_ell_all = np.linspace(0, 2*np.pi, probe_points_num)
default_probe_points_ell_1 = default_probe_points_ell_all[:int(np.ceil(probe_points_num/2))][::-1]
default_probe_points_ell_2 = default_probe_points_ell_all[int(np.ceil(probe_points_num/2)):]
if default_probe_points_ravel:
    default_probe_points_ell = np.vstack([default_probe_points_ell_1, default_probe_points_ell_2]).T.ravel()
    default_probe_points_ell = np.concatenate(([np.pi], default_probe_points_ell))
else:
    default_probe_points_ell = np.concatenate(([np.pi], default_probe_points_ell_1, default_probe_points_ell_2))
default_probe_points_ell = np.round(default_probe_points_ell, 6)


def predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma=np.nan):
    """Given body and vessel orbital parameters, that orbit same reference,
    searches for entering COI in one next full orbit.
    Returns vessel Ea, body Ea, vessel Ma, body Ma and time when that will happen.
    Vessel mean anomaly of enter COI point can be hinted."""
    ecc, ma, ea, pea, _, a, b, f, per, ref_coi, dr = vessel_data
    b_ecc, b_ma, _, b_pea, b_n, b_a, b_b, b_f, _, b_dr, coi = body_data
    center_x, center_y = vessel_orbit_center

    f = a * ecc
    ap = a * (1 + ecc)
    b_ap = b_a * (1 + b_ecc)
    b_pe = b_a * (1 - b_ecc)

    # check if vessel can't enter body COI
    if ecc < 1 and ap < b_pe - coi:
        return np.array([np.nan] * 5)

    # generate and select probe poins
    if ecc < 1 and ap < b_ap + coi:
        probe_points = default_probe_points_ell
    else:
        intersections = ell_hyp_intersect(a, b, ecc, f, 0, b_ap + coi)
        if np.all(np.isnan(intersections)):
            return np.array([np.nan] * 5)
        if ecc < 1:
            if ap < ref_coi:   # using both sides of ellipse
                range_point_1 = next_point(ea, intersections, dr)[0]
                range_point_2 = next_point(ea, intersections, dr)[-1]
                range_point_1_ma = (range_point_1 - ecc * np.sin(range_point_1)) % (2 * np.pi)
                range_point_2_ma = (range_point_2 - ecc * np.sin(range_point_2)) % (2 * np.pi)
                probe_points_1 = gen_probe_points_ell(ma, range_point_1_ma, probe_points_num/2)
                probe_points_2 = gen_probe_points_ell(range_point_2_ma, ma, probe_points_num/2)
                probe_points = np.concatenate((probe_points_1, probe_points_2))[:-1]
            else:   # using only "first" side of ellipse
                range_point = next_point(ea, intersections, dr)[0]
                range_point_ma = (range_point - ecc * np.sin(range_point)) % (2 * np.pi)
                probe_points = gen_probe_points_ell(ma, range_point_ma, probe_points_num)
        else:
            # for hyperbola, points are always custom generated
            # TODO
            probe_points = np.array([1, 1/2, 3/2, 3/4, 5/4, 1/4, 7/4, 7/8, 9/8,
                                     1/8, 15/8, 5/8, 11/8, 3/8, 13/8, 0]) * np.pi
            return np.array([np.nan] * 5)
    probe_points = np.round(probe_points, 6)

    # inject hint_ma at start of probe points, so it is checked first
    if not np.isnan(hint_ma):
        probe_points = np.concatenate((np.array([hint_ma]), probe_points))

    corr = 0
    search = True
    lost = False
    new_b_ea = 0
    actual_corr = 1000
    actual_corr_old = actual_corr
    corr_invert = False
    furthest_once = True
    last_iteration_inverted = False

    for i in range(len(probe_points) + extra_optimize_iterations):

        # search for initial intersection
        if search:
            if i == len(probe_points):
                break
            new_ma = probe_points[i]
        else:
            new_ma += corr

        # time when vessel is at specified Ma
        time_to_new_ma = orbit_time_to(ma, new_ma, per, dr, corr_invert)

        # body Ma at that time
        if b_ecc < 1:
            new_b_ma = b_ma + b_dr * b_n * time_to_new_ma
            if new_b_ma > 2 * np.pi:
                new_b_ma -= 2 * np.pi
            elif new_b_ma < 0:
                new_b_ma += 2 * np.pi
        else:
            new_b_ma -= b_dr * b_n * time_to_new_ma

        # body position at that Ma relative to parent body
        if b_ecc < 1:
            new_b_ea = newton_root_kepler_ell(b_ecc, new_b_ma, new_b_ea)
            b_x_n = b_a * np.cos(new_b_ea) - b_f
            b_y_n = b_b * np.sin(new_b_ea)
        else:
            new_b_ea = newton_root_kepler_hyp(b_ecc, new_b_ma, new_b_ea)
            b_x_n = b_a * np.cosh(new_b_ea) - b_f
            b_y_n = b_b * np.sinh(new_b_ea)

        # body position rotated by body pea
        b_x = b_x_n * np.cos(b_pea - np.pi) - b_y_n * np.sin(b_pea - np.pi)
        b_y = b_x_n * np.sin(b_pea - np.pi) + b_y_n * np.cos(b_pea - np.pi)

        # body position relative to ell/hyp center, rotated by vessel pea
        b_x_r = -(np.cos(-pea) * (b_x - center_x) - np.sin(-pea) * (b_y - center_y))
        b_y_r = -(np.sin(-pea) * (b_x - center_x) + np.cos(-pea) * (b_y - center_y))

        # intersections of ellipse and coi at body_pos
        intersections = ell_hyp_intersect(a, b, ecc, b_x_r, b_y_r, coi)

        # if there are intersections
        if not np.all(np.isnan(intersections)):
            if search:
                search = False
                intersect_ea = next_point(ea, intersections, dr)[0]
                if ecc < 1:
                    intersect_ma = (intersect_ea - ecc * np.sin(intersect_ea)) % (2 * np.pi)
                else:
                    intersect_ma = ecc * np.sinh(intersect_ea) - intersect_ea
                corr = intersect_ma - new_ma
                actual_corr = corr   # correction without backing when there are no intersection
                new_ea = np.nan   # in case correction is small enough
            else:
                lost = False
                if ecc < 1:
                    new_ea = newton_root_kepler_ell(ecc, new_ma, new_ma)
                else:
                    new_ea = newton_root_kepler_hyp(ecc, new_ma, new_ma)
                # check if vessel is inside COI
                sorted_intersections = next_point(ea, intersections, dr)
                if corr_invert:
                    sorted_intersections = sorted_intersections[::-1]
                inside_coi = point_between(new_ea, sorted_intersections[0], sorted_intersections[1], 1)
                # pick target
                if corr_invert and not inside_coi and furthest_once:
                    # selecting furthest because it will bring vessel closer to first point of intersect
                    # when both points are on same side of COI
                    # this should be allowed only once, to prevent distancing from intersection
                    # in case this is wrong, backing will repair damage
                    target = np.argmax(np.abs(intersections - new_ea))   # furthest intersection
                    furthest_once = False
                else:
                    target = np.argmin(np.abs(intersections - new_ea))   # closest intersection
                intersect_ea = intersections[target]
                # get correction
                if ecc < 1:
                    intersect_ma = (intersect_ea - ecc * np.sin(intersect_ea)) % (2 * np.pi)
                else:
                    intersect_ma = ecc * np.sinh(intersect_ea) - intersect_ea
                corr = -abs(intersect_ma - new_ma)
                # if outside COI and in front of it
                if not inside_coi and not corr_invert:
                    dist = np.abs(new_ea - sorted_intersections)
                    dist = np.where(dist > np.pi, 2*np.pi - dist, dist)
                    if np.argmin(dist) == 1:
                        corr = -corr
                actual_corr = corr   # correction without backing when there are no intersection

            if not last_iteration_inverted:
                if np.sign(actual_corr) == np.sign(actual_corr_old):
                    if abs(actual_corr) - abs(actual_corr_old) > 0:
                        corr_invert = not corr_invert
                        last_iteration_inverted = True
                actual_corr_old = actual_corr
            else:
                last_iteration_inverted = False
            if corr_invert:
                corr = -corr
                actual_corr_old = actual_corr


        # if there are no intersections
        else:
            if search:
                corr = 1
            else:
                if not lost:
                    # keep going back by half if intersection is not found at first
                    if corr > 0:
                        back = -1
                    else:
                        back = 1
                    lost = True
                corr = back * abs(corr) / 2   # go back by half

        # break when correction gets too small
        if abs(actual_corr) < 1e-4 and not np.isnan(new_ea):
            return np.array([new_ea, new_b_ea, new_ma, new_b_ma, time_to_new_ma])

    if search:
        return np.array([np.nan] * 5)
    else:
        if abs(actual_corr) < 1e-3:
            return np.array([new_ea, new_b_ea, new_ma, new_b_ma, time_to_new_ma])
        else:
            return np.array([np.nan] * 5)


# if numba is enabled, compile functions ahead of time
use_numba = leval(fileops.load_settings("game", "numba"))
if numba_avail and use_numba:
    enable_fastmath = leval(fileops.load_settings("game", "fastmath"))
    jitkw = {"cache": True, "fastmath": enable_fastmath}   # numba JIT setings
    # disabling fastmath for some functions with np.isnan()
    jitkw_nofast = {"cache": True, "fastmath": False}
    ell_hyp_intersect = njit(float64[:](float64, float64, float64, float64, float64, float64), **jitkw)(ell_hyp_intersect)
    next_point = njit(float64[:](float64, float64[:], float64), **jitkw_nofast)(next_point)
    gen_probe_points_ell = njit(float64[:](float64, float64, float64), **jitkw)(gen_probe_points_ell)
    predict_enter_coi = njit([
        float64[:](UniTuple(float64, 11), UniTuple(float64, 11), UniTuple(float64, 2), Omitted(np.nan)),
        float64[:](UniTuple(float64, 11), UniTuple(float64, 11), UniTuple(float64, 2), float64)],
        **jitkw_nofast)(predict_enter_coi)
