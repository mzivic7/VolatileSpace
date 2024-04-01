import numpy as np
import time

from volatilespace.physics.phys_shared import orbit_time_to, \
    newton_root_kepler_ell, newton_root_kepler_hyp
from volatilespace.physics.orbit_intersect import \
    ell_hyp_intersect, next_point


# evenly distributed probe points (ma) on orbit
# optimized so area around apoapsis is probed first and is more dense
probe_points_ell = np.array([np.pi, np.pi/2, 3*np.pi/2,
                             3*np.pi/4, 5*np.pi/4, np.pi/4, 7*np.pi/4,
                             7*np.pi/8, 9*np.pi/8, np.pi/8, 15*np.pi/8,
                             5*np.pi/8, 11*np.pi/8, 3*np.pi/8, 13*np.pi/8, 0])
probe_points_hyp = np.array([np.pi, np.pi/2, 3*np.pi/2,
                             3*np.pi/4, 5*np.pi/4, np.pi/4, 7*np.pi/4,
                             7*np.pi/8, 9*np.pi/8, np.pi/8, 15*np.pi/8,
                             5*np.pi/8, 11*np.pi/8, 3*np.pi/8, 13*np.pi/8, 0])
probe_points_ell = np.round(probe_points_ell, 6)
probe_points_hyp = np.round(probe_points_ell, 6)


def predict_enter_coi(vessel_data, body_data, vessel_orbit_center):
    """Given body and vessel orbital parameters, that orbit same reference,
    searches for entering COI in one next full orbit.
    Returns vessel Ea, body Ea, vessel Ma, body Ma and time when that will happen."""
    total_start_time = time.perf_counter()
    ecc, ma, ea, pea, _, a, b, f, per, dr = vessel_data
    b_ecc, b_ma, _, b_pea, b_n, b_a, b_b, b_f, _, b_dr, coi = body_data
    center_x, center_y = vessel_orbit_center

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
                actual_corr = corr   # correction without backing
                print(f"new_ma = {new_ma}; OK")
                print()
                print("-----------------INTERSECTION FOUND------------------")
                print(f"in {i+1} iterations")
                print(f"total search time = {(time.perf_counter() - total_start_time)*1000} ms")
            else:
                lost = False
                if ecc < 1:
                    new_ea = newton_root_kepler_ell(ecc, new_ma, new_ma)
                else:
                    new_ea = newton_root_kepler_hyp(ecc, new_ma, new_ma)
                intersect_ea = intersections[np.argmin(abs(intersections - new_ea))]
                if ecc < 1:
                    intersect_ma = (intersect_ea - ecc * np.sin(intersect_ea)) % (2 * np.pi)
                else:
                    intersect_ma = ecc * np.sinh(intersect_ea) - intersect_ea
                corr = -abs(intersect_ma - new_ma)
                actual_corr = corr   # correction without backing
                print(f"--------------------ITERATION {i}--------------------")

            print(f"new_ma = {new_ma} rad, {new_ma * 180/np.pi} deg")
            print(f"new_ea = {newton_root_kepler_ell(ecc, new_ma, new_ma)}")
            print(f"new_b_ma = {new_b_ma} rad, {new_b_ma * 180/np.pi} deg")
            print(f"new_b_ea = {new_b_ea} rad")
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
        else:  # there are no intersection
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
        if actual_corr < 1e-3:
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
            return np.array([new_ea, new_b_ea, new_ma, new_b_ma, time_to_new_ma])
