import numpy as np
import time
from volatilespace.physics.phys_shared import orbit_time_to, \
    newton_root_kepler_ell, newton_root_kepler_hyp
from volatilespace.physics.quartic_solver import solve_quartic


# evenly distributed probe points (ma) on orbit
# optimized so area around apoapsis is probed first and is more dense
probe_points_ell = np.array([1, 1/2, 3/2, 3/4, 5/4, 1/4, 7/4, 7/8, 9/8,
                             1/8, 15/8, 5/8, 11/8, 3/8, 13/8, 0]) * np.pi
probe_points_hyp = np.array([1, 1/2, 3/2, 3/4, 5/4, 1/4, 7/4, 7/8, 9/8,
                             1/8, 15/8, 5/8, 11/8, 3/8, 13/8, 0]) * np.pi
probe_points_ell = np.round(probe_points_ell, 6)
probe_points_hyp = np.round(probe_points_ell, 6)


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
            return np.array([np.NaN])
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
            return np.array([np.NaN])


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
        return np.array([np.NaN, np.NaN])


def sort_intersect_indices(ea_vessel, ea_points, direction):
    """Sorts points on orbit by their angular (ea) distance from vessel in specified direction"""
    if not np.all(np.isnan(ea_points)):
        angle = np.where(np.isnan(ea_points), np.NaN, np.abs(ea_vessel - ea_points))
        # where ea_vessel is larger: invert
        angle = np.where(ea_vessel > ea_points, 2*np.pi - angle, angle)
        if direction < 0:   # if direction is clockwise: invert
            angle = np.pi*2 - angle
        ea_points_sorted = np.argsort(angle)
        # returning -1 instead np.NaN because np.NaN is special float
        ea_points_sorted = np.where(np.isnan(ea_points[ea_points_sorted]), -1, ea_points_sorted)
        return ea_points_sorted
    else:
        return np.array([np.NaN])


def point_between(p1, p2, p3):
    """Returns True if angle p1 is between angles p2 and p3 on circle"""
    p1_p2 = np.fmod(p2 - p1 + np.pi, np.pi)
    p1_p3 = np.fmod(p3 - p1 + np.pi, np.pi)
    return (p1_p2 <= np.pi) != (p1_p3 > p1_p2)


def predict_enter_coi(vessel_data, body_data, vessel_orbit_center):
    """Given body and vessel orbital parameters, that orbit same reference,
    searches for entering COI in one next full orbit.
    Returns vessel Ea, body Ea, vessel Ma, body Ma and time when that will happen."""
    total_start_time = time.perf_counter()
    ecc, ma, ea, pea, _, a, b, f, per, dr = vessel_data
    b_ecc, b_ma, _, b_pea, b_n, b_a, b_b, b_f, _, b_dr, coi = body_data
    center_x, center_y = vessel_orbit_center

    print("------------------------DATA-------------------------")
    print(f"a = {a}")
    print(f"b = {b}")
    print(f"r = {coi}")

    # check if vessel cant enter body COI
    if ecc < 1 and a * (1 + ecc) < b_a * (1 - b_ecc) - coi:
        print("-------------------------END-------------------------")
        print("vessel will never enter body COI, skipping all calculations")
        print(f"total time = {time.perf_counter() - total_start_time} s")
        return np.array([np.NaN] * 5)

    corr = 0
    search = True
    lost = False
    new_b_ea = 0
    actual_corr = 1000

    # select probe points
    if ecc < 1:
        probe_points = probe_points_ell
    else:
        probe_points = probe_points_hyp

    print("-----------SEARCHING FOR INIT INTERSECTION-----------")
    for i in range(len(probe_points) + 5):

        start_time = time.perf_counter()
        # search for initial intersection
        if search:
            if i == len(probe_points):
                break
            new_ma = probe_points[i]
        else:
            new_ma += corr

        # time when vessel is at specified Ma
        time_to_new_ma = orbit_time_to(ma, new_ma, per, dr)

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
                actual_corr = corr   # correction without backing when there are no itersection
                print(f"new_ma = {new_ma}; OK")
                print()
                print("-----------------INTERSECTION FOUND------------------")
                print(f"Search iterations: {i+1}")
                print(f"total search time = {(time.perf_counter() - total_start_time)*1000} ms")
            else:
                lost = False
                if ecc < 1:
                    new_ea = newton_root_kepler_ell(ecc, new_ma, new_ma)
                else:
                    new_ea = newton_root_kepler_hyp(ecc, new_ma, new_ma)
                closest = np.argmin(abs(intersections - new_ea))
                intersect_ea = intersections[closest]   # select closest intersection
                if ecc < 1:
                    intersect_ma = (intersect_ea - ecc * np.sin(intersect_ea)) % (2 * np.pi)
                else:
                    intersect_ma = ecc * np.sinh(intersect_ea) - intersect_ea
                corr = -abs(intersect_ma - new_ma)   # move backward
                # check if vessel is ouside COI and in front of body
                sorted_intersections = next_point(ea, intersections, dr)
                if not point_between(new_ea, sorted_intersections[0], sorted_intersections[1]):
                    dist = np.abs(new_ea - sorted_intersections)
                    dist = np.where(dist > np.pi, 2*np.pi - dist, dist)
                    if np.argmin(dist) == 1:
                        corr = -corr
                actual_corr = corr   # correction without backing when there are no itersection
                print(f"--------------------ITERATION {i}--------------------")

            print(f"new_ma = {new_ma} rad, {new_ma * 180/np.pi} deg")
            print(f"new_ea = {newton_root_kepler_ell(ecc, new_ma, new_ma)}")
            print(f"new_b_ma = {new_b_ma} rad, {new_b_ma * 180/np.pi} deg")
            print(f"new_b_ea = {new_b_ea} rad")
            if ecc < 1:
                new_ea = newton_root_kepler_ell(ecc, new_ma, new_ma)
            else:
                new_ea = newton_root_kepler_hyp(ecc, new_ma, new_ma)
            sorted_intersections = next_point(ea, intersections, dr)
            print(f"new_pos is in COI: {point_between(new_ea, sorted_intersections[0], sorted_intersections[1])}")
            print(f"time_to_new_ma = {time_to_new_ma / 60} s")
            print(f"b_pos = {[b_x, b_y]}")
            print(f"b_pos_rel = {[b_x_r, b_y_r]}")
            print(f"intersections_ea: {intersections} rad")
            print(f"intersections_ma: {(intersections - ecc * np.sin(intersections)) % (2*np.pi)} rad")
            print(f"selected_ma = {intersect_ma} rad, {intersect_ma * 180/np.pi} deg")
            print(f"correction = {corr} rad")
            print(f"iteration time = {(time.perf_counter() - start_time)*1000} ms")
            print()

        # if there are no intersections
        else:
            if search:
                corr = 1
                print(f"new_ma = {new_ma}; FAILED")
            else:
                if not lost:
                    # keep going back by half if intersection is not found at first
                    if corr > 0:
                        back = -1
                    else:
                        back = 1
                    lost = True
                corr = back * abs(corr) / 2   # go back by half

                print(f"--------------------ITERATION {i}--------------------")
                print("intersection lost, searching for it")
                print(f"new_ma = {new_ma} rad, {new_ma * 180/np.pi} deg")
                print(f"new_ea = {newton_root_kepler_ell(ecc, new_ma, new_ma)}")
                print(f"new_b_ma = {new_b_ma} rad, {new_b_ma * 180/np.pi} deg")
                print(f"new_b_ea = {new_b_ea} rad")
                print(f"time_to_new_ma = {time_to_new_ma / 60} s")
                if ecc < 1:
                    new_ea = newton_root_kepler_ell(ecc, new_ma, new_ma)
                else:
                    new_ea = newton_root_kepler_hyp(ecc, new_ma, new_ma)
                sorted_intersections = next_point(ea, intersections, dr)
                print(f"new_pos is in COI: {point_between(new_ea, sorted_intersections[0], sorted_intersections[1])}")
                print(f"b_pos = {[b_x, b_y]}")
                print(f"b_pos_rel = {[b_x_r, b_y_r]}")
                print(f"correction = {corr} rad")
                print(f"iteration time = {(time.perf_counter() - start_time)*1000} ms")
                print()

        # break when correction gets too small
        if abs(actual_corr) < 1e-4:
            print("-------------------------END-------------------------")
            print(f"finished in {i+1} iterations")
            print(f"correction = {actual_corr} rad")
            print(f"total time = {(time.perf_counter() - total_start_time)*1000} ms")
            print(f"new_ma = {new_ma} rad, {new_ma * 180/np.pi} deg")
            print(f"new_ea = {new_ea} rad, {new_ea * 180/np.pi} deg")
            print(f"new_b_ma = {new_b_ma} rad, {new_b_ma * 180/np.pi} deg")
            print(f"new_b_ea = {new_b_ea} rad, {new_b_ea * 180/np.pi} deg")
            print(f"time_to_new_ma = {time_to_new_ma / 60} s")
            return np.array([new_ea, new_b_ea, new_ma, new_b_ma, time_to_new_ma])

    if search:
        print(f"no intersections found in one full orbit ({i+1} iterations)")
        print(f"total time = {time.perf_counter() - total_start_time} s")
        return np.array([np.NaN] * 5)
    else:
        if abs(actual_corr) < 1e-3:
            print("-------------------------END-------------------------")
            print("reached maximum number of iterations but correction is too large, yet acceptable")
            print(f"correction = {actual_corr} rad")
            print(f"total time = {(time.perf_counter() - total_start_time)*1000} ms")
            print(f"new_ma = {new_ma} rad, {new_ma * 180/np.pi} deg")
            print(f"new_ea = {new_ea} rad, {new_ea * 180/np.pi} deg")
            print(f"new_b_ma = {new_b_ma} rad, {new_b_ma * 180/np.pi} deg")
            print(f"new_b_ea = {new_b_ea} rad, {new_b_ea * 180/np.pi} deg")
            print(f"time_to_new_ma = {time_to_new_ma / 60} s")
            return np.array([new_ea, new_b_ea, new_ma, new_b_ma, time_to_new_ma])
        else:
            print("-------------------------END-------------------------")
            print("reached maximum number of iterations but correction is too large")
            print(f"correction = {actual_corr} rad")
            print(f"total time = {(time.perf_counter() - total_start_time)*1000} ms")
            return np.array([np.NaN] * 5)
