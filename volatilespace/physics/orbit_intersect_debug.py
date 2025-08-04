import time

import numpy as np

from volatilespace.physics.enhanced_kepler_solver import solve_kepler_ell
from volatilespace.physics.phys_shared import (
    angle_diff,
    newton_root_kepler_hyp,
    orbit_time_to,
    point_between,
)
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
    """Find next and previous point on orbit in ea_point
    s, from ea_vessel, in orbit direction."""
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
    """Sorts points on orbit by their angular (ea) distance from vessel in specified direction"""
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


def gen_probe_points_ell(t1, t2, num):
    """Generates specified number of probe points from specified range with wrapping at 2pi.
    Returned points are in reverse order, those closer to t2 are first."""
    if t1 < t2 or t2 == 0:
        probe_points = np.linspace(t1, t2, int(num))
    else:
        probe_points = np.linspace(t1, t2+(2*np.pi), int(num)) % (2*np.pi)
    return probe_points


def predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma):
    """Given body and vessel orbital parameters, that orbit same reference,
    searches for entering COI in one next full orbit.
    Returns vessel Ea, body Ea, vessel Ma, body Ma and time when that will happen.
    Vessel mean anomaly of enter COI point can be hinted, use np.nan if unknown."""
    total_start_time = time.perf_counter()
    ecc, ma, ea, pea, _, a, b, f, per, ref_coi, dr = vessel_data
    b_ecc, b_ma, _, b_pea, b_n, b_a, b_b, b_f, _, b_dr, coi = body_data
    center_x, center_y = vessel_orbit_center

    extra_optimize_iterations = 10
    probe_points_num = 16
    min_search_corr_hi = 1
    min_search_corr_lo = 0.5

    min_search_corr_slope = (min_search_corr_lo - min_search_corr_hi) / np.pi
    ap = a * (1 + ecc)
    b_ap = b_a * (1 + b_ecc)
    b_pe = b_a * (1 - b_ecc)
    if probe_points_num % 2:
        probe_points_num -= 1

    if dr == b_dr:
        opposed = False
    else:
        opposed = True
        # opposed algorithm has 2 stages (iterations)
        extra_optimize_iterations = int(extra_optimize_iterations * 2)

    print()
    print()
    print("------------------------DATA------------------------")
    print(f"ecc = {ecc}")
    print(f"ma = {ma}")
    print(f"ea = {ea}")
    print(f"pea = {pea}")
    print(f"a = {a}")
    print(f"b = {b}")
    print(f"f = {f}")
    print(f"dr = {dr}")
    print(f"b_ecc = {b_ecc}")
    print(f"b_ea = {solve_kepler_ell(b_ecc, b_ma, 1e-10)}")
    print(f"b_pea = {b_pea}")
    print(f"b_a = {b_a}")
    print(f"b_b = {b_b}")
    print(f"b_f = {b_f}")
    print(f"b_coi = {coi}")
    print(f"b_dr = {b_dr}")
    print(f"ref_coi = {ref_coi}")
    print(f"hint_ma = {hint_ma}")
    print(f"using {"OPPOSED" if opposed else "NORMAL"} solver algorithm")

    # check if vessel can't enter body COI
    if ecc < 1 and ap < b_pe - coi:
        print()
        print("-------------------------END-------------------------")
        print("Vessel will never enter body COI, skipping all calculations")
        print(f"apoapsis = {ap}")
        print(f"body periapsis - coi = {b_pe - coi}")
        print(f"total time = {time.perf_counter() - total_start_time} s")
        return np.array([np.nan] * 5)

    # generate and select probe poins
    print()
    print("---------------GENERATING PROBE POINTS---------------")
    if ecc < 1 and ap < b_ap + coi:
        probe_points = gen_probe_points_ell(ma, ma, probe_points_num)
        print("Using default probe points")
        print(f"Range (ma): {ma} - {ma}")
        print(f"direction: {dr}")
    else:
        intersections = ell_hyp_intersect(a, b, ecc, f, 0, b_ap + coi)
        print("Using truncated probe points")
        if np.all(np.isnan(intersections)):
            print()
            print("-------------------------END-------------------------")
            print("Vessel can't enter body COI")
            return np.array([np.nan] * 5)
        if ecc < 1:
            if ap < ref_coi:   # using both sides of ellipse
                range_point_1 = next_point(ea, intersections, dr)[0]
                range_point_2 = next_point(ea, intersections, dr)[-1]
                range_point_1_ma = (range_point_1 - ecc * np.sin(range_point_1)) % (2 * np.pi)
                range_point_2_ma = (range_point_2 - ecc * np.sin(range_point_2)) % (2 * np.pi)
                probe_points_1 = gen_probe_points_ell(ma, range_point_1_ma, int(len(probe_points)/2))
                probe_points_2 = gen_probe_points_ell(range_point_2_ma, ma, int(len(probe_points)/2))
                probe_points = np.concatenate((probe_points_1, probe_points_2))[:-1]
                print("Using both sides of ellipse")
                print(f"Range (ma): {range_point_1_ma} - {range_point_2_ma}")
                print(f"Range (ea): {range_point_1} - {range_point_2}")
                print(f"direction: {dr}")
            else:   # using only "first" side of ellipse
                range_point = next_point(ea, intersections, dr)[0]
                range_point_ma = (range_point - ecc * np.sin(range_point)) % (2 * np.pi)
                probe_points = gen_probe_points_ell(ma, range_point_ma, probe_points_num)
                print("Using only first side of ellipse")
                print(f"Range (ma):{range_point_ma} - {ma}")
                print(f"Range (ea):{range_point} - {ea}")
                print(f"direction: {dr}")
        else:
            # for hyperbola, points are always custom generated
            # TODO   # noqa
            probe_points = np.array([
                1, 1/2, 3/2, 3/4, 5/4, 1/4, 7/4, 7/8, 9/8,
                1/8, 15/8, 5/8, 11/8, 3/8, 13/8, 0,
            ]) * np.pi
            print()
            print("-------------------------END-------------------------")
            print("Hyperbola not yet supported")
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
    opposed_second_stage = False


    print()
    print("-----------SEARCHING FOR INIT INTERSECTION-----------")
    for i in range(len(probe_points) + extra_optimize_iterations):

        start_time = time.perf_counter()
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
            new_b_ea = solve_kepler_ell(b_ecc, new_b_ma, 1e-10)
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
                intersect_ea = next_point(ea, intersections, dr)[0]
                if ecc < 1:
                    intersect_ma = (intersect_ea - ecc * np.sin(intersect_ea)) % (2 * np.pi)
                    new_ea = solve_kepler_ell(ecc, new_ma, 1e-10)
                else:
                    intersect_ma = ecc * np.sinh(intersect_ea) - intersect_ea
                    new_ea = newton_root_kepler_hyp(ecc, new_ma, new_ma)
                # get correction
                corr = -abs(intersect_ma - new_ma)
                # check if vessel is inside COI
                sorted_intersections = next_point(new_ea, intersections, dr)
                if corr_invert:
                    sorted_intersections = sorted_intersections[::-1]
                if dr > 0:
                    diff = (sorted_intersections[1] - sorted_intersections[0] + np.pi) % (2*np.pi) - np.pi
                else:
                    diff = (sorted_intersections[0] - sorted_intersections[1] + np.pi) % (2*np.pi) - np.pi
                if diff >= 0:
                    inside_coi = point_between(new_ea, sorted_intersections[0], sorted_intersections[1], dr)
                else:
                    inside_coi = point_between(new_ea, sorted_intersections[1], sorted_intersections[0], dr)
                # if outside COI
                if opposed and not inside_coi and not corr_invert:
                    corr = -corr
                corr = intersect_ma - new_ma
                actual_corr = corr   # correction without backing when there are no intersection
                new_ea = np.nan   # in case correction is small enough
                if not opposed:
                    min_search_corr = min_search_corr_slope * (abs(new_ma) % np.pi) + min_search_corr_hi
                else:
                    min_search_corr = min_search_corr_hi
                if abs(corr) < min_search_corr:
                    print(f"new_ma = {new_ma}; corr = |{round(corr, 6)}| < |{round(min_search_corr, 6)}|;  OK")
                    print(f"Search iterations: {i+1}")
                    print(f"Total search time = {(time.perf_counter() - total_start_time)*1000} ms")
                    print()
                    print("------------------SEARCH ITERATION-------------------")
                    if ecc < 1:
                        print(f"new_ea = {solve_kepler_ell(ecc, new_ma, 1e-10)} rad")
                    else:
                        print(f"new_ea = {newton_root_kepler_hyp(ecc, new_ma, new_ma)} rad")
                    print(f"time_to_new_ma = {time_to_new_ma / 60} s")
                    print(f"new_b_ma = {new_b_ma} rad, {round(new_b_ma * 180/np.pi, 3)} deg")
                    print(f"new_b_ea = {new_b_ea} rad")
                    print(f"new_pos is in COI: {inside_coi}")
                    print(f"b_pos = {np.array([b_x, b_y])}")
                    print(f"b_pos_rel = {np.array([b_x_r, b_y_r])}")
                    print(f"intersections_ma: {(intersections - ecc * np.sin(intersections)) % (2*np.pi)} rad")
                    print(f"intersections_ea: {intersections} rad")
                    print(f"selected_ma = {intersect_ma} rad, {round(intersect_ma * 180/np.pi, 3)} deg")
                    print(f"correction = {corr} rad")
                    print(f"iteration time = {(time.perf_counter() - start_time)*1000} ms")
                    search = False
                    if opposed:
                        if not opposed_second_stage:
                            prev_ma = new_ma
                        opposed_second_stage = not opposed_second_stage
                    else:
                        prev_ea = new_ea
                else:
                    print(f"new_ma = {new_ma}; corr = |{round(corr, 6)}| > |{round(min_search_corr, 6)}|; BAD")
            else:
                lost = False
                if ecc < 1:
                    new_ea = solve_kepler_ell(ecc, new_ma, 1e-10)
                else:
                    new_ea = newton_root_kepler_hyp(ecc, new_ma, new_ma)
                if opposed and not opposed_second_stage:
                    prev_ma = new_ma
                # check if vessel is inside COI
                sorted_intersections = next_point(new_ea, intersections, dr)
                if corr_invert:
                    sorted_intersections = sorted_intersections[::-1]
                if dr > 0:
                    diff = (sorted_intersections[1] - sorted_intersections[0] + np.pi) % (2*np.pi) - np.pi
                else:
                    diff = (sorted_intersections[0] - sorted_intersections[1] + np.pi) % (2*np.pi) - np.pi
                if diff >= 0:
                    inside_coi = point_between(new_ea, sorted_intersections[0], sorted_intersections[1], dr)
                else:
                    inside_coi = point_between(new_ea, sorted_intersections[1], sorted_intersections[0], dr)
                # pick target
                if not opposed:
                    if corr_invert and inside_coi and furthest_once:
                        # selecting furthest because it will bring vessel closer to first point of intersect
                        # when there are 2 points of intersection in 2 different times on same side of COI
                        # this should be allowed only once, to prevent distancing from intersection
                        # in case this is wrong, backing will repair damage
                        target = np.argmax(np.abs(intersections - new_ea))   # furthest intersection
                        furthest_once = False
                    elif inside_coi and prev_ea > new_ea and furthest_once:
                        # it is ok to pick furthest if vessel is returning back while its in COI
                        # it should be enought to do this only once to bring it to right side of COI
                        target = np.argmax(np.abs(intersections - new_ea))   # furthest intersection
                        furthest_once = False
                    else:
                        target = np.argmin(np.abs(intersections - new_ea))   # closest intersection
                    intersect_ea = intersections[target]
                # using first intersection in orbit direction, relative to point outside of COI
                # because that is the only point vessel can enter COI when opposed
                elif inside_coi:
                    # because intersections are sorted relative to vessel new_ea
                    intersect_ea = sorted_intersections[1]
                else:
                    intersect_ea = sorted_intersections[0]
                # get intersection ma
                if ecc < 1:
                    intersect_ma = (intersect_ea - ecc * np.sin(intersect_ea)) % (2 * np.pi)
                else:
                    intersect_ma = ecc * np.sinh(intersect_ea) - intersect_ea
                if not opposed_second_stage:
                    # get correction
                    corr = -abs(intersect_ma - new_ma)
                if opposed:
                    if not opposed_second_stage:
                        if dr < 0:
                            corr = -corr
                            # because direction is inverted, correction now must be positive
                        if not inside_coi and not corr_invert:
                            corr = -corr
                    else:
                        # prev_ma <- from previous iteration/search
                        # new_ma <- from this iteration
                        # intersect_ma <- intersection in this iteration
                        corr_dr = (1 if corr > 0 else -1)
                        p = angle_diff(prev_ma, new_ma, corr_dr)
                        q = angle_diff(intersect_ma, new_ma, corr_dr)
                        corr = (p**2)/q * corr_dr
                        new_ma_debug = new_ma   # only for debugging
                        new_ma = prev_ma   # undo correction from first stage
                        actual_corr = corr   # actual correction is taken only from second stage
                    opposed_second_stage = not opposed_second_stage
                else:
                    actual_corr = corr   # correction without backing when there are no intersections
                print()
                print(f"--------------------ITERATION {i}--------------------")

                if opposed:
                    if opposed_second_stage:
                        print("This is FIRST stage of OPPOSED algorithm")
                        debug_ma = new_ma
                    else:
                        print("This is SECOND stage of OPPOSED algorithm")
                        debug_ma = new_ma_debug
                else:
                    debug_ma = new_ma
                print(f"new_ma = {debug_ma} rad, {round(debug_ma * 180/np.pi, 3)} deg")
                if ecc < 1:
                    new_ea = solve_kepler_ell(ecc, debug_ma, 1e-10)
                else:
                    new_ea = newton_root_kepler_hyp(ecc, debug_ma, debug_ma)
                sorted_intersections = next_point(ea, intersections, dr)
                if corr_invert:
                    sorted_intersections = sorted_intersections[::-1]
                print(f"new_ea = {new_ea} rad")
                print(f"time_to_new_ma = {time_to_new_ma / 60} s")
                print(f"new_b_ma = {new_b_ma} rad, {round(new_b_ma * 180/np.pi, 3)} deg")
                print(f"new_b_ea = {new_b_ea} rad")
                print(f"new_pos is in COI: {inside_coi}")
                print(f"b_pos = {np.array([b_x, b_y])}")
                print(f"b_pos_rel = {np.array([b_x_r, b_y_r])}")
                print(f"intersections_ma: {(intersections - ecc * np.sin(intersections)) % (2*np.pi)} rad")
                print(f"intersections_ea: {intersections} rad")
                print(f"selected_ma = {intersect_ma} rad, {round(intersect_ma * 180/np.pi, 3)} deg")
                print(f"correction = {corr} rad")
                print(f"iteration time = {(time.perf_counter() - start_time)*1000} ms")
                print(f"correction is {"INVERTED" if corr_invert else "NORMAL"}")

                if not last_iteration_inverted and (not opposed or not opposed_second_stage):
                    print()
                    print("-----CORRECTION CHECK-----")
                    print(f"actual_corr_old = {actual_corr_old} rad")
                    print(f"actual_corr_cur = {actual_corr} rad")
                    if np.sign(actual_corr) == np.sign(actual_corr_old):
                        if abs(actual_corr) - abs(actual_corr_old) > 0:
                            print("BAD - correction is growing - inverting")
                            corr_invert = not corr_invert
                            last_iteration_inverted = True
                        else:
                            print("OK - correction is decreasing")
                    else:
                        print("Unknown - correction changed sign")
                    actual_corr_old = actual_corr
                else:
                    print("Correction check SKIPPED")
                    last_iteration_inverted = False
                if corr_invert:
                    corr = -corr
                    actual_corr_old = actual_corr
            prev_ea = new_ea

        # if there are no intersections
        elif search:
            corr = 1
            print(f"new_ma = {new_ma}; corr = nan; FAILED")
        else:
            # backing stays same for opposed case
            if not lost:
                # keep going back by half if intersection is not found at first
                if corr > 0:
                    back = -1
                else:
                    back = 1
                lost = True
            corr = back * abs(corr) / 2   # go back by half
            # for opposed, always return to first stage after blacking
            opposed_second_stage = False

            print()
            print(f"--------------------ITERATION {i}--------------------")
            print("intersection LOST, backing by half of last correction")
            print(f"new_ma = {new_ma} rad, {round(new_ma * 180/np.pi, 3)} deg")
            if ecc < 1:
                new_ea = solve_kepler_ell(ecc, new_ma, 1e-10)
            else:
                new_ea = newton_root_kepler_hyp(ecc, new_ma, new_ma)
            sorted_intersections = next_point(ea, intersections, dr)
            if corr_invert:
                sorted_intersections = sorted_intersections[::-1]
            print(f"new_ea = {new_ea} rad")
            print(f"time_to_new_ma = {time_to_new_ma / 60} s")
            print(f"new_b_ma = {new_b_ma} rad, {round(new_b_ma * 180/np.pi, 3)} deg")
            print(f"new_b_ea = {new_b_ea} rad")
            print(f"new_pos is in COI: {point_between(new_ea, sorted_intersections[0], sorted_intersections[1], dr)}")
            print(f"b_pos = {np.array([b_x, b_y])}")
            print(f"b_pos_rel = {np.array([b_x_r, b_y_r])}")
            print(f"correction = {corr} rad")
            print(f"iteration time = {(time.perf_counter() - start_time)*1000} ms")
            print(f"correction is {"INVERTED" if corr_invert else "NORMAL"}")

        # break when correction gets too small
        if abs(actual_corr) < 1e-4 and not np.isnan(new_ea):
            print()
            print("-------------------------END-------------------------")
            print(f"finished in {i+1} iterations")
            print(f"correction = {actual_corr} rad")
            print(f"total time = {(time.perf_counter() - total_start_time)*1000} ms")
            print(f"new_ma = {new_ma} rad, {round(new_ma * 180/np.pi, 3)} deg")
            print(f"new_ea = {new_ea} rad, {round(new_ea * 180/np.pi, 3)} deg")
            print(f"new_b_ma = {new_b_ma} rad, {round(new_b_ma * 180/np.pi, 3)} deg")
            print(f"new_b_ea = {new_b_ea} rad, {round(new_b_ea * 180/np.pi, 3)} deg")
            print(f"time_to_new_ma = {time_to_new_ma / 60} s")
            return np.array([new_ea, new_b_ea, new_ma, new_b_ma, time_to_new_ma])

    if search:
        print()
        print("-------------------------END-------------------------")
        print(f"no intersections found in one full orbit (tested {i+1} points)")
        print(f"total time = {time.perf_counter() - total_start_time} s")
        return np.array([np.nan] * 5)
    if abs(actual_corr) < 1e-3:
        print()
        print("-------------------------END-------------------------")
        print("reached maximum number of iterations but correction is too large, yet acceptable")
        print(f"correction = {actual_corr} rad")
        print(f"total time = {(time.perf_counter() - total_start_time)*1000} ms")
        print(f"new_ma = {new_ma} rad, {round(new_ma * 180/np.pi, 3)} deg")
        print(f"new_ea = {new_ea} rad, {round(new_ea * 180/np.pi, 3)} deg")
        print(f"new_b_ma = {new_b_ma} rad, {round(new_b_ma * 180/np.pi, 3)} deg")
        print(f"new_b_ea = {new_b_ea} rad, {round(new_b_ea * 180/np.pi, 3)} deg")
        print(f"time_to_new_ma = {time_to_new_ma} ticks")
        return np.array([new_ea, new_b_ea, new_ma, new_b_ma, time_to_new_ma])
    print()
    print("-------------------------END-------------------------")
    print("reached maximum number of iterations but correction is too large")
    print(f"correction = {actual_corr} rad")
    print(f"total time = {(time.perf_counter() - total_start_time)*1000} ms")
    return np.array([np.nan] * 5)
