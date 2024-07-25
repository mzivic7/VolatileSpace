from ast import literal_eval as leval
import math
import pygame
from itertools import repeat
import numpy as np
try:   # to allow building without numba
    from numba import njit, int32, float64
    numba_avail = True
except ImportError:
    numba_avail = False

from volatilespace import fileops
from volatilespace import defaults
from volatilespace.physics.phys_shared import \
    newton_root_kepler_ell, newton_root_kepler_hyp, \
    curve_points, curve_move_to, \
    mag, orbit_time_to, orb2xy, culling
from volatilespace.physics.orbit_intersect_debug import \
    ell_hyp_intersect, next_point, sort_intersect_indices, \
    predict_enter_coi
from volatilespace.physics.convert import \
    kepler_to_velocity, velocity_to_kepler


def concat_wrap(array, point_start, range_start, range_end, point_end):
    """Concatenates [point_start, range_start, range_end, point_end] such that if range_start > range_end,
    range goes from range_end to array_end + array_start to range_start, and point_1 and point_2 swaps places."""
    # not using np.concatenate because it cannot be easily NJIT-ed with numba, and this is faster
    out = np.empty((array.shape[0], 2))
    out[:] = np.nan
    if range_start <= range_end:
        out[0, :] = point_start
        out[1:1+range_end-range_start, :] = array[range_start:range_end, :]
        out[1+range_end-range_start, :] = point_end
    else:
        out[0, :] = point_end
        range_first = array[range_start:, :]
        range_second = array[:range_end, :]
        out[1:1+range_first.shape[0], :] = range_first
        out[1+range_first.shape[0]:1+range_first.shape[0]+range_second.shape[0], :] = range_second
        out[range_first.shape[0]+range_second.shape[0], :] = point_start
    # if there are nans in input array they need to be cleaned from output:
    if np.any(np.isnan(array)):
        out_clean = out[~np.isnan(out[:, 0]), :]
        out[:] = np.nan
        out[: out_clean.shape[0], :] = out_clean
    return out


def calc_orb_one(vessel, ref, body_mass, gc, a, ecc):
    """Additional vessel orbital parameters."""
    u = gc * body_mass[ref]   # standard gravitational parameter
    f = a * ecc
    b = math.sqrt(abs(f**2 - a**2))

    if ecc != 0:   # if orbit is not circle
        pe_d = a * (1 - ecc)
        if ecc < 1:   # if orbit is ellipse
            period = 2 * np.pi * math.sqrt(a**3 / u)
            ap_d = a * (1 + ecc)
            n = 2*np.pi / period
        else:
            if ecc > 1:   # hyperbola
                pe_d = a * (1 - ecc)
            else:   # parabola
                pe_d = a
            period = 0   # period is undefined
            # there is no apoapsis
            ap_d = 0
            n = math.sqrt(u / abs(a)**3)
    else:   # circle
        period = (2 * np.pi * math.sqrt(a**3 / u)) / 10
        pe_d = a * (1 - ecc)
        # there is no apoapsis
        ap_d = 0
        n = 2*np.pi / period

    return b, f, pe_d, ap_d, period, n, u


# if numba is enabled, compile functions ahead of time
use_numba = leval(fileops.load_settings("game", "numba"))
if numba_avail and use_numba:
    enable_fastmath = leval(fileops.load_settings("game", "fastmath"))
    jitkw = {"cache": True, "fastmath": enable_fastmath}   # numba JIT setings
    concat_wrap = njit((float64[:, :], float64[:], int32, int32, float64[:]), **jitkw)(concat_wrap)



class Physics():
    def __init__(self):
        # vessel internal
        self.names = np.array([])
        self.rot_angle = np.array([])
        self.rot_speed = np.array([])
        self.rot_acc = np.array([])
        self.visible_orbits = []
        self.physical_hold = np.array([], dtype=int)
        # vessel orbit main
        self.a = np.array([])
        self.ecc = np.array([])
        self.pea = np.array([])
        self.ma = np.array([])
        self.ref = np.array([])
        self.dr = np.array([])
        # vessel orbit extra
        self.b = np.array([])
        self.f = np.array([])
        self.pe_d = np.array([])
        self.ap_d = np.array([])
        self.period = np.array([])
        self.n = np.array([])
        self.curves = np.array([])
        self.pos = np.array([])
        self.ea = np.array([])
        self.prev_ea = np.array([])
        self.u = np.array([])
        self.body_mass = np.array([])
        self.body_pos = np.array([])
        self.atmos = np.array([])
        self.gc = defaults.sim_config["gc"]
        self.rad_mult = defaults.sim_config["rad_mult"]
        self.coi_coef = defaults.sim_config["coi_coef"]
        self.vessl_scale = defaults.sim_config["vessel_scale"]
        self.reload_settings()


    def reload_settings(self):
        """Reload all settings, should be run every time game is entered, or settings have changed."""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
        self.curve_points = int(fileops.load_settings("graphics", "curve_points"))   # number of points from which curve is drawn
        self.curves = np.zeros((len(self.names), self.curve_points, 2))
        self.t = np.linspace(-np.pi, np.pi, self.curve_points)   # parameter
        for vessel, _ in enumerate(self.names):
            self.curve(vessel)


    def load_conf(self, conf):
        """Loads physics related config."""
        self.gc = conf["gc"]
        self.rad_mult = conf["rad_mult"]
        self.coi_coef = conf["coi_coef"]
        self.vessl_scale = conf["vessel_scale"]


    def load(self, conf, body_data, body_orb, vessel_data, vessel_orb_data):
        """Load vessels and bodies."""
        self.body_mass = body_data["mass"]
        self.body_size = body_data["size"]
        self.body_ref = body_orb["ref"]
        self.body_a = body_orb["a"]
        self.body_b = body_orb["b"]
        self.body_f = body_orb["f"]
        self.body_ecc = body_orb["ecc"]
        self.body_pea = body_orb["pea"]
        self.body_n = body_orb["n"]
        self.body_dr = body_orb["dir"]
        self.body_coi = body_orb["coi"]
        self.body_atm = body_data["atm_h"]
        self.load_conf(conf)
        self.physical_hold = np.array([], dtype=int)
        # vessel internal
        self.names = vessel_data["name"]
        self.mass = vessel_data["mass"]
        self.rot_angle = vessel_data["rot_angle"]
        self.rot_speed = np.zeros(len(self.names))
        self.rot_acc = vessel_data["rot_acc"]
        # vessel orbit
        self.a = vessel_orb_data["a"]
        self.ecc = vessel_orb_data["ecc"]
        self.pea = vessel_orb_data["pe_arg"]
        self.ma = vessel_orb_data["ma"]
        self.ref = vessel_orb_data["ref"]
        self.dr = vessel_orb_data["dir"]
        self.pos = np.zeros([len(self.names), 2])   # position will be updated later
        self.ea = np.zeros(len(self.names))
        self.curves = np.zeros((len(self.names), self.curve_points, 2))   # shape: (vessel, points, axes)
        self.curves_mov = np.zeros((len(self.names), self.curve_points, 2))
        # orbit points
        self.body_impact = np.zeros((len(self.names), 2)) * np.nan
        self.body_enter_atm = np.zeros((len(self.names), 2)) * np.nan
        self.coi_leave = np.zeros((len(self.names), 2)) * np.nan
        self.coi_enter = np.zeros((len(self.names), 6)) * np.nan
        self.entered_coi = None
        self.left_coi = None
        self.left_coi_prev_ref = None

        # those need to be cleared, in case game with less vessels is loaded
        self.n = np.array([])
        self.f = np.array([])


    def ea2coord(self, vessel, ea):
        """Return coordinates on vessel orbit from eccentric anomaly"""
        pea = self.pea[vessel]
        ecc = self.ecc[vessel]
        a = self.a[vessel]
        b = self.b[vessel]
        f = self.f[vessel]
        ref = self.body_pos[self.ref[vessel]]
        return orb2xy(a, b, f, ecc, pea, ref, ea)


    def culling(self, sim_screen, zoom, visible_coi):
        """Returns separate lists of:
        - Vessels that are visible on screen
        - Vessels whose orbits are inside COI that is visible on screen and COI is larger than N pixels"""
        visible_vessels_truth = culling(self.pos, np.array([10]*len(self.names)) / zoom, sim_screen, zoom)
        self.visible_vessels = np.arange(len(self.names))[visible_vessels_truth]
        visible_coi_truth = np.array([False]*len(self.body_dr))
        visible_coi_truth[visible_coi] = True
        visible_orbits_truth = np.logical_and(visible_coi_truth[self.ref], self.body_coi[self.ref] > 8 / zoom)
        visible_orbits_truth = np.logical_or(visible_orbits_truth, self.ref == 0)   # incl all orbits around main ref
        visible_orbits_truth = np.logical_and(visible_orbits_truth, self.pe_d * zoom < self.screen_x*15)
        self.visible_orbits = np.arange(len(self.names))[visible_orbits_truth]
        # not returning truth values so "for vessel in visible_vessels" can be used
        return self.visible_vessels, self.visible_orbits


    def initial(self, warp, body_pos, body_ma):
        # ORBIT DATA #
        if len(self.names):
            values = list(map(calc_orb_one, list(range(len(self.names))), self.ref, repeat(self.body_mass), repeat(self.gc), self.a, self.ecc))
            self.b, self.f, self.pe_d, self.ap_d, self.period, self.n, self.u = list(map(np.array, zip(*values)))
        vessel_orb = {"a": self.a,
                      "ref": np.array(self.ref),
                      "ecc": self.ecc,
                      "pe_d": self.pe_d,
                      "ap_d": self.ap_d,
                      "pea": self.pea,
                      "dir": self.dr,
                      "per": self.period}

        # MOVE #
        self.move(warp, body_pos, body_ma)
        for vessel, _ in enumerate(self.names):
            self.curve(vessel)
        self.curve_move()

        # POINTS #
        for vessel, _ in enumerate(self.names):
            self.points(vessel)
        return vessel_orb, self.pos, self.ma, self.curves_mov


    def change_vessel(self, vessel):
        """Do all vessel related physics to one vessel. This should be done only if something changed on vessel or it's orbit."""
        # output is list because reading from dict is slow

        # VESSEL DATA #
        vessel_data = [self.names[vessel]]

        # ORBIT DATA #
        a = self.a[vessel]
        ecc = self.ecc[vessel]
        self.u[vessel] = u = self.gc * self.body_mass[self.ref[vessel]]   # standard gravitational parameter
        self.f[vessel] = f = a * ecc
        self.b[vessel] = math.sqrt(abs(f**2 - a**2))

        if ecc != 0:   # if orbit is not circle
            self.pe_d[vessel] = a * (1 - ecc)
            if ecc < 1:   # if orbit is ellipse
                self.period[vessel] = 2 * np.pi * math.sqrt(a**3 / u)
                self.ap_d[vessel] = a * (1 + ecc)
                self.n[vessel] = 2*np.pi / self.period[vessel]
            else:
                if ecc > 1:   # hyperbola
                    self.pe_d[vessel] = a * (1 - ecc)
                else:   # parabola
                    self.pe_d[vessel] = a
                self.period[vessel] = 0   # period is undefined
                # there is no apoapsis
                self.ap_d[vessel] = 0
                self.n[vessel] = math.sqrt(self.u[vessel] / abs(self.a[vessel])**3)
        else:   # circle
            self.period[vessel] = (2 * np.pi * math.sqrt(a**3 / u)) / 10
            self.pe_d[vessel] = a * (1 - ecc)
            # there is no apoapsis
            self.ap_d[vessel] = 0
            self.n[vessel] = 2*np.pi / self.period[vessel]

        vessel_orb = [a,
                      self.ref[vessel],
                      ecc,
                      self.pe_d[vessel],
                      self.ap_d[vessel],
                      self.pea[vessel],
                      self.dr[vessel],
                      self.period[vessel]]

        # recalculate ea
        if self.ecc[vessel] < 1:
            self.ea[vessel] = newton_root_kepler_ell(self.ecc[vessel], self.ma[vessel], self.ma[vessel])
        else:
            self.ea[vessel] = newton_root_kepler_hyp(self.ecc[vessel], self.ma[vessel], self.ma[vessel])
        # recalculate points and curves
        self.points(vessel)
        self.curve(vessel)
        return vessel_data, vessel_orb


    def curve(self, vessel):
        """Calculate RELATIVE conic curve line points coordinates for one vessel.
        This should be done only if something changed on vessel or it's orbit, and after points()."""
        self.curves[vessel] = curve_points(self.ecc[vessel], self.a[vessel], self.b[vessel], self.pea[vessel], self.t)


    def points(self, vessel):
        """Find characteristic points on RELATIVE UNROTATED ellipse for one body.
        This should be done only if something changed on vessel or it's orbit, after move()."""
        ecc = self.ecc[vessel]
        ell = ecc < 1
        ref = self.ref[vessel]
        pea = self.pea[vessel]
        dr = self.dr[vessel]
        xc = self.f[vessel]   # body is in focus
        yc = 0
        ea = self.ea[vessel]
        b = self.b[vessel]
        a = self.a[vessel]

        if ell and self.pe_d[vessel] > self.body_size[ref]:
            body_impact_all = np.array([np.nan])
        else:
            body_impact_all = ell_hyp_intersect(a, b, ecc, xc, yc, self.body_size[ref])
        self.body_impact[vessel] = next_point(ea, body_impact_all, dr)

        if ell and self.pe_d[vessel] > self.body_size[ref] + self.body_atm[ref]:
            body_enter_atm_all = np.array([np.nan])
        else:
            body_enter_atm_all = ell_hyp_intersect(a, b, ecc, xc, yc, self.body_size[ref] + self.body_atm[ref])
        self.body_enter_atm[vessel] = next_point(ea, body_enter_atm_all, dr)

        if ell and self.ap_d[vessel] < self.body_coi[ref]:
            coi_leave_all = np.array([np.nan])
            self.coi_leave[vessel] = np.array([np.nan, np.nan])
        else:
            coi_leave_all = ell_hyp_intersect(a, b, ecc, xc, yc, self.body_coi[ref])
            # after enter-coi, use future position to avoid triggering leave-coi and selecting wrong poit
            if self.entered_coi == vessel:
                # calculate vessel ma and ea for next iteration
                if ell:
                    next_ma = self.ma[vessel] + self.n[vessel] * dr
                    next_ea = newton_root_kepler_ell(ecc, next_ma, ea)
                else:
                    next_ma = self.ma[vessel] + self.n[vessel] * dr * -1
                    next_ea = newton_root_kepler_hyp(ecc, next_ma, ea)
                self.coi_leave[vessel] = next_point(next_ea, coi_leave_all, dr)
            else:
                self.coi_leave[vessel] = next_point(ea, coi_leave_all, dr)

        # enter_coi
        enter_data_all = np.empty([0, 5])
        center_x = self.f[vessel] * np.cos(pea)   # center of ellipse/hyperbola relative to reference
        center_y = self.f[vessel] * np.sin(pea)
        check_bodies = np.where(self.body_ref == ref)[0]   # all bodies orbiting reference

        # after leave-coi, use future position to avoid triggering enter-coi and selecting wrong poit
        if self.left_coi == vessel:
            # calculate VESSEL ma and ea for next iteration
            if ell:
                next_ma = self.ma[vessel] + self.n[vessel] * dr
                next_ea = newton_root_kepler_ell(ecc, next_ma, ea)
            else:
                next_ma = self.ma[vessel] + self.n[vessel] * dr * -1
                next_ea = newton_root_kepler_hyp(ecc, next_ma, ea)
            ea = next_ea

        for body in check_bodies:
            b_ma = self.body_ma[body]
            if self.left_coi == vessel:
                # calculate just body ma for next iteration
                if ell:
                    b_ma += self.body_n[body] * self.body_dr[body]
                else:
                    b_ma += + self.body_n[body] * self.body_dr[body] * -1
            # find vessel and body ma and time when vessel will enter body coi
            vessel_data = (ecc, self.ma[vessel], ea, self.pea[vessel], 0.0,
                           a, b, self.f[vessel], self.period[vessel],
                           self.body_coi[self.ref[vessel]], self.dr[vessel])
            body_data = (self.body_ecc[body], b_ma, 0.0, self.body_pea[body], self.body_n[body],
                         self.body_a[body], self.body_b[body], self.body_f[body], 0.0,
                         self.body_dr[body], self.body_coi[body])
            vessel_orbit_center = (center_x, center_y)
            enter_data_one = predict_enter_coi(vessel_data, body_data, vessel_orbit_center)
            if self.left_coi == vessel and self.left_coi_prev_ref == body:
                # if vessel has just left COI of checked body, false positive can occur
                # in that case time_to_new_ma will be very small or very close to period
                if enter_data_one[4] < self.period[vessel] / 750 or \
                   self.period[vessel] - enter_data_one[4] < self.period[vessel] / 750:
                    enter_data_one = np.array([np.nan] * 5)
            enter_data_all = np.vstack((enter_data_all, enter_data_one))
        coi_enter_all = enter_data_all[:, 0]
        first_enter = sort_intersect_indices(ea, coi_enter_all, dr)[0]
        if not np.isnan(first_enter):
            self.coi_enter[vessel] = np.append(check_bodies[first_enter], enter_data_all[first_enter])
        else:
            self.coi_enter[vessel] = np.array([np.nan]*6)


    def move(self, warp, body_pos, body_ma):
        """Move vessel with mean motion."""
        self.body_pos = body_pos
        self.body_ma = body_ma
        hyp = np.where(self.ecc > 1, -1, 1)
        self.ma += self.dr * self.n * warp * hyp
        self.ma = np.where(np.logical_and(self.ecc < 1, self.ma > 2*np.pi), self.ma - 2*np.pi, self.ma)
        self.ma = np.where(np.logical_and(self.ecc < 1, self.ma < 0), self.ma + 2*np.pi, self.ma)
        self.prev_ea = np.array(self.ea)
        for vessel, _ in enumerate(self.names):
            if self.ecc[vessel] < 1:
                ea = newton_root_kepler_ell(self.ecc[vessel], self.ma[vessel], self.ea[vessel])
            else:
                ea = newton_root_kepler_hyp(self.ecc[vessel], self.ma[vessel], self.ea[vessel])
            self.pos[vessel] = self.ea2coord(vessel, ea)
            self.ea[vessel] = ea
        return self.pos, self.ma


    def curve_move(self):
        """Move all orbit curves to parent position.
        This should be done every tick, after move()."""
        self.curves_mov = curve_move_to(self.curves, self.body_pos, self.ref, self.f, self.pea)
        return self.curves_mov


    def curve_segments(self):
        """Calculates two segments for each curve on screen.
        Returns arrays of all x and y points for each segment for all curves on screen.
        Dimensions: (curve, points, axis).
        This should be done every tick after curve_move(), and after points(), which must be run at least once"""
        curves_light = np.empty((len(self.names), self.curve_points, 2))   # shape: (vessel, points, axes)
        curves_dark = np.empty((len(self.names), self.curve_points, 2))
        intersect_type = np.zeros(len(self.names))
        select_range = np.empty((len(self.names), 2)) * np.nan
        first_intersect = np.empty((len(self.names), 2)) * np.nan
        for vessel in self.visible_orbits:
            ea = self.ea[vessel]
            ecc = self.ecc[vessel]
            if ecc < 1:
                ell = True   # is True for ellipse (ecc<1) and False for hyperbola (ecc>1)
            else:
                ell = False
            dr = self.dr[vessel]
            point_vessel = self.pos[vessel]
            curve_light = np.array(self.curves_mov[vessel])   # np.array is same as np.copy but faster
            curve_dark = np.array(self.curves_mov[vessel])

            # check where and what is next intesection
            impact = self.body_impact[vessel, int(not ell)]
            coi_enter = self.coi_enter[vessel, 1]
            coi_leave = self.coi_leave[vessel, int(not ell)]
            all_intersect = np.array((impact, coi_enter, coi_leave))
            next_intersect = sort_intersect_indices(self.ea[vessel], all_intersect, dr)

            # do all possible scenarios
            if next_intersect[0] == 0:   # IMPACT
                curves_dark[vessel] = curve_dark
                ea_next = self.body_impact[vessel, 0]
                coord_next = self.ea2coord(vessel, ea_next)
                if ell:   # for ellipse
                    ea_vessel = round(ea * self.curve_points / (2*np.pi))
                    ea_point_next = round(ea_next * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        if ea_vessel == ea_point_next:
                            ea_vessel -= 1
                        curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                    else:   # CW
                        if ea_vessel == ea_point_next:
                            ea_vessel += 1
                        curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, ea_vessel-1, point_vessel)
                else:   # for hyperbola
                    ea_vessel = self.curve_points - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = self.curve_points - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        if ea_vessel == ea_point_next:
                            ea_vessel += 1
                        if ea < 0:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, ea_vessel-1, point_vessel)
                        else:
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_point_next, ea_vessel-1, coord_next)
                    else:   # CW
                        if ea_vessel == ea_point_next:
                            ea_vessel -= 1
                        if ea < 0:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_vessel+1, ea_point_next, point_vessel)
                        else:
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                first_intersect[vessel] = coord_next
                intersect_type[vessel] = 1

            if next_intersect[0] == 1:   # COI ENTER
                curves_dark[vessel] = curve_dark
                ea_next = coi_enter
                coord_next = self.ea2coord(vessel, ea_next)
                if ell:   # for ellipse
                    ea_vessel = round(ea * self.curve_points / (2*np.pi))
                    ea_point_next = round(ea_next * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        if ea < np.pi:
                            if ea_vessel == ea_point_next:
                                ea_vessel -= 1
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                        else:

                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_vessel, ea_point_next, point_vessel)
                    else:   # CW
                        if ea < np.pi:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, ea_vessel-1, point_vessel)
                        else:
                            if ea_vessel == ea_point_next:
                                ea_vessel += 1
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, ea_vessel-1, point_vessel)
                else:   # for hyperbola
                    ea_vessel = self.curve_points - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = self.curve_points - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        if ea_vessel == ea_point_next:
                            ea_vessel += 1
                        if ea < 0:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, ea_vessel-1, point_vessel)
                        else:
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_point_next, ea_vessel-1, coord_next)
                    else:   # CW
                        if ea_vessel == ea_point_next:
                            ea_vessel -= 1
                        if ea < 0:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_vessel+1, ea_point_next, point_vessel)
                        else:
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                first_intersect[vessel] = coord_next
                intersect_type[vessel] = 2
                select_range[vessel] = [ea, ea_next]

            if next_intersect[0] == 2:   # JUST COI LEAVE
                if ell:   # for ellipse
                    ea_next = self.coi_leave[vessel, 0]
                    ea_prev = self.coi_leave[vessel, 1]
                    coord_next = self.ea2coord(vessel, ea_next)
                    coord_prev = self.ea2coord(vessel, ea_prev)
                    ea_vessel = round(ea * self.curve_points / (2*np.pi))
                    ea_point_next = round(ea_next * self.curve_points / (2*np.pi))
                    ea_point_prev = round(ea_prev * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        if ea < np.pi:
                            if ea_vessel == ea_point_next:
                                ea_vessel -= 1
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                        else:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_vessel, ea_point_next, point_vessel)
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_next, ea_point_prev, ea_point_next, coord_prev)
                    else:   # CW
                        if ea < np.pi:
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_point_next, max(ea_vessel, 0), coord_next)
                        else:
                            if ea_vessel == ea_point_next:
                                ea_vessel += 1
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, max(ea_vessel-1, 0), point_vessel)
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_prev, ea_point_next, ea_point_prev, coord_next)
                else:   # for hyperbola
                    ea_next = self.coi_leave[vessel, 0]
                    ea_prev = self.coi_leave[vessel, 1]
                    coord_next = self.ea2coord(vessel, ea_next)
                    coord_prev = self.ea2coord(vessel, ea_prev)
                    ea_vessel = self.curve_points - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = self.curve_points - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_prev = self.curve_points - round((ea_prev+np.pi) * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        if ea_vessel == ea_point_next:
                            ea_vessel += 1
                        curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, max(ea_vessel-1, 0), point_vessel)
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_next, ea_point_next, ea_point_prev, coord_prev)
                    else:   # CW
                        if ea_vessel == ea_point_next:
                            ea_vessel -= 1
                        curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_prev, ea_point_prev, ea_point_next, coord_next)
                first_intersect[vessel] = coord_next
                intersect_type[vessel] = 3

            elif any(next_intersect == 2):   # COI LEAVE FOR 2 INTERSECTIONS
                if ell:   # for ellipse
                    ea_next = self.coi_leave[vessel, 0]
                    ea_prev = self.coi_leave[vessel, 1]
                    coord_next = self.ea2coord(vessel, ea_next)
                    coord_prev = self.ea2coord(vessel, ea_prev)
                    ea_point_next = round(ea_next * self.curve_points / (2*np.pi))
                    ea_point_prev = round(ea_prev * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_next, ea_point_prev, ea_point_next, coord_prev)
                    else:   # CW
                        if ea < np.pi:
                            curves_dark[vessel] = concat_wrap(curve_dark, coord_prev, ea_point_next, ea_point_prev, coord_next)
                        else:
                            curves_dark[vessel] = concat_wrap(curve_dark, coord_next, ea_point_next, ea_point_prev, coord_prev)
                else:   # for hyperbola
                    ea_next = self.coi_leave[vessel, 0]
                    ea_prev = self.coi_leave[vessel, 1]
                    coord_next = self.ea2coord(vessel, ea_next)
                    coord_prev = self.ea2coord(vessel, ea_prev)
                    ea_vessel = self.curve_points - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = self.curve_points - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_prev = self.curve_points - round((ea_prev+np.pi) * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_next, ea_point_next, ea_point_prev, coord_prev)
                    else:   # CW
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_prev, ea_point_prev, ea_point_next, coord_next)

            if np.isnan(next_intersect[0]):
                curves_light[vessel] = curve_light
                first_intersect[vessel] = np.array([np.nan, np.nan])
        return curves_light, curves_dark, first_intersect, intersect_type, select_range


    def selected(self, vessel):
        """Do physics for selected vessel. This should be done every tick after move()."""
        pos_ref = self.body_pos[self.ref[vessel]]
        periapsis_arg = self.pea[vessel]
        a = self.a[vessel]
        b = self.b[vessel]
        ecc = self.ecc[vessel]
        ea = self.ea[vessel]
        ma = self.ma[vessel]
        period = self.period[vessel]
        ap_d = self.ap_d[vessel]
        pe_d = self.pe_d[vessel]
        dr = self.dr[vessel]
        u = self.u[vessel]

        rel_pos = self.pos[vessel] - pos_ref
        distance = mag(rel_pos)   # distance to parent
        speed_orb = math.sqrt(u * ((2 / distance) - (1 / a)))   # velocity magnitude from vis-viva eq
        if ecc < 1:
            ta = math.acos((math.cos(ea) - ecc)/(1 - ecc * math.cos(ea)))   # true anomaly from eccentric anomaly
        else:
            ta = math.acos((math.cosh(ea) - ecc)/(1 - ecc * math.cosh(ea)))   # for hyperbola
        if ma > np.pi:
            ta = 2*np.pi - ta
        angle = (ta - math.atan(-b * (math.cos(ea)) / (math.sin(ea) * a))) % np.pi
        speed_vert = speed_orb * math.cos(angle)
        speed_hor = speed_orb * math.sin(angle)

        if ecc != 0:   # not circle
            if ecc < 1:   # ellipse
                if np.pi < ta < 2*np.pi:
                    ea = 2*np.pi - ea   # quadrant problems
                pe_t = orbit_time_to(ma, 0, period, dr)
                ap = np.array([ap_d * math.cos(periapsis_arg), ap_d * math.sin(periapsis_arg)]) + pos_ref
                ap_t = orbit_time_to(ma, np.pi, period, dr)
            else:
                if ecc > 1:   # hyperbola
                    pe_t = math.sqrt((-a)**3 / u) * ma
                else:   # parabola
                    pe_t = math.sqrt(2*(a/2)**3) * ma
                period = 0   # period is undefined
                # there is no apoapsis
                ap = np.array([0, 0])
                ap_t = 0
        else:   # circle
            ma = ta
            period = (2 * np.pi * math.sqrt(a**3 / u)) / 10
            pe_t = orbit_time_to(ma, 0, period, dr)
            # there is no apoapsis
            ap = np.array([0, 0])
            ap_t = 0
        pe = np.array([pe_d * math.cos(periapsis_arg - np.pi), pe_d * math.sin(periapsis_arg - np.pi)]) + pos_ref

        return ta, pe, pe_t, ap, ap_t, distance, speed_orb, speed_hor, speed_vert


    def check_warp(self, warp):
        """Returns vessel that will in next iteration meet conditions for switching warp, and what is that condition.
        This should be done every tick after move(), and after points(), which must be run at least once.
        Conditions (situations):
        0 space -> impact
        1 space -> atmosphere
        2 atmosphere -> space
        3 crossing coi"""

        situation = None
        alarm_vessel = None
        for vessel, _ in enumerate(self.names):
            ecc = self.ecc[vessel]
            dr = self.dr[vessel]

            # find what is next relevant intersection
            ea_vessel_1 = self.ea[vessel]
            impact = self.body_impact[vessel, 0]
            enter_atm = self.body_enter_atm[vessel, 0]
            leave_atm = self.body_enter_atm[vessel, 1]
            leave_coi = self.coi_leave[vessel, 0]
            enter_coi = self.coi_enter[vessel, 1]
            all_intersect = np.array((impact, enter_atm, leave_atm, enter_coi, leave_coi))
            next_intersections = sort_intersect_indices(ea_vessel_1, all_intersect, dr)
            if not np.all(np.isnan(next_intersections)):
                next_intersect = next_intersections[0]
                ea_intersect = all_intersect[next_intersect]

                # calculate vessel ea for next iteration
                if ecc < 1:
                    next_ma = self.ma[vessel] + self.n[vessel] * warp * dr * 2
                    ea_vessel_2 = newton_root_kepler_ell(ecc, next_ma, ea_vessel_1)
                else:
                    next_ma = self.ma[vessel] + self.n[vessel] * warp * dr * -1 * 2
                    ea_vessel_2 = newton_root_kepler_hyp(ecc, next_ma, ea_vessel_1)
                # checking if vessel will pass point in next iteration
                angle_1 = abs(ea_vessel_1 - ea_intersect)
                angle_2 = abs(ea_vessel_1 - ea_vessel_2)
                if ea_vessel_1 > ea_intersect:
                    angle_1 = 2*np.pi - angle_1
                if ea_vessel_1 > ea_vessel_2:
                    angle_2 = 2*np.pi - angle_2
                if dr < 0:   # if clockwsise
                    angle_1, angle_2 = angle_2, angle_1
                if angle_1 < angle_2:
                    # handling cases
                    alarm_vessel = vessel
                    if next_intersect in [0, 1]:
                        if vessel not in self.physical_hold:
                            self.physical_hold = np.append(self.physical_hold, vessel)
                        situation = next_intersect
                    elif next_intersect == 2:
                        self.physical_hold = self.physical_hold[self.physical_hold != vessel]
                        situation = next_intersect
                    else:
                        situation = 3
                else:
                    self.physical_hold = self.physical_hold[self.physical_hold != vessel]
            else:
                if vessel in self.physical_hold:
                    self.physical_hold = self.physical_hold[self.physical_hold != vessel]
        return situation, alarm_vessel, len(self.physical_hold)


    def cross_coi(self, warp):
        """Changes vessel orbit reference and orbital parametes when it is leaving or entering COI"""
        for vessel, _ in enumerate(self.names):
            ecc = self.ecc[vessel]
            ell = ecc < 1
            dr = self.dr[vessel]
            ea_vessel_1 = self.prev_ea[vessel]
            coi_leave = self.coi_leave[vessel, 0]
            coi_enter = self.coi_enter[vessel]

            # in case there are multiple points, find next point
            impact = self.body_impact[vessel, int(not ell)]
            all_intersect = np.array((impact, coi_enter[1], coi_leave))   # coi_enter[0] is new reference
            next_intersect = sort_intersect_indices(ea_vessel_1, all_intersect, dr)

            # protection so leave/enter-coi don't pick previous position after crossing and trigger another cross
            if self.entered_coi == vessel:
                self.entered_coi = None   # this is used in self.points()
            if self.left_coi == vessel:
                self.left_coi = None
                self.left_coi_prev_ref = None

            if next_intersect[0] == 2:   # LEAVE COI
                ea_vessel_2 = self.ea[vessel]
                angle_1 = abs(ea_vessel_1 - coi_leave)
                angle_2 = abs(ea_vessel_1 - ea_vessel_2)
                if ea_vessel_1 > coi_leave:
                    angle_1 = 2*np.pi - angle_1
                if ea_vessel_1 > ea_vessel_2:
                    angle_2 = 2*np.pi - angle_2
                if dr < 0:   # if clockwsise
                    angle_1, angle_2 = angle_2, angle_1
                if angle_1 < angle_2:
                    ref = self.ref[vessel]
                    new_u = self.gc * self.body_mass[self.body_ref[ref]]
                    # calculate vessel and reference relative positions (to their references)
                    ves_abs_pos = self.ea2coord(vessel, coi_leave)
                    ref_abs_pos = self.body_pos[ref]
                    ves_rel_pos = ves_abs_pos - ref_abs_pos
                    ref_rel_pos = ref_abs_pos - self.body_pos[self.body_ref[ref]]
                    # calculate vessel and reference relative velocities (to their references)
                    ves_rel_vel = kepler_to_velocity(ves_rel_pos, self.a[vessel], ecc, self.pea[vessel], self.u[vessel], dr)
                    ref_rel_vel = kepler_to_velocity(ref_rel_pos, self.body_a[ref], self.body_ecc[ref], self.body_pea[ref], new_u, self.body_dr[ref])
                    # add vessels and its references relative positions and velocities
                    new_ves_pos = ves_rel_pos + ref_rel_pos
                    new_ves_vel = ves_rel_vel + ref_rel_vel
                    # convert this position and absolute velocity to orbital parameters
                    self.a[vessel], self.ecc[vessel], self.pea[vessel], self.ma[vessel], self.dr[vessel] = velocity_to_kepler(new_ves_pos, new_ves_vel, new_u, failsafe=1)
                    # set new reference
                    self.ref[vessel] = self.body_ref[ref]
                    self.left_coi = vessel
                    self.left_coi_prev_ref = ref
                    return vessel

            elif next_intersect[0] == 1:   # ENTER COI
                ea_vessel_2 = self.ea[vessel]
                coi_enter_ea = coi_enter[1]
                angle_1 = abs(ea_vessel_1 - coi_enter_ea)
                angle_2 = abs(ea_vessel_1 - ea_vessel_2)
                if ea_vessel_1 > coi_enter_ea:
                    angle_1 = 2*np.pi - angle_1
                if ea_vessel_1 > ea_vessel_2:
                    angle_2 = 2*np.pi - angle_2
                if dr < 0:
                    angle_1, angle_2 = angle_2, angle_1
                if angle_1 < angle_2:
                    ref = self.ref[vessel]
                    new_ref = int(coi_enter[0])
                    new_u = self.gc * self.body_mass[new_ref]
                    ves_abs_pos = self.ea2coord(vessel, coi_enter_ea)
                    ref_abs_pos = self.body_pos[ref]
                    ves_rel_pos = ves_abs_pos - ref_abs_pos
                    new_ref_abs_pos = self.body_pos[new_ref]
                    new_ref_rel_pos = new_ref_abs_pos - ref_abs_pos
                    ves_rel_vel = kepler_to_velocity(ves_rel_pos, self.a[vessel], ecc, self.pea[vessel], self.u[vessel], dr)
                    new_ref_rel_vel = kepler_to_velocity(new_ref_rel_pos, self.body_a[new_ref], self.body_ecc[new_ref], self.body_pea[new_ref], new_u, self.body_dr[new_ref])
                    new_ves_pos = ves_rel_pos - new_ref_rel_pos
                    new_ves_vel = ves_rel_vel - new_ref_rel_vel
                    self.a[vessel], self.ecc[vessel], self.pea[vessel], self.ma[vessel], self.dr[vessel] = velocity_to_kepler(new_ves_pos, new_ves_vel, new_u, failsafe=2)
                    self.ref[vessel] = new_ref
                    self.entered_coi = vessel
                    return vessel

        return None

    def rotate(self, warp, vessel, direction):
        """Rotates all vessels, and changes rotation speed of active vessel,
        according to its maximum rotation acceleration, in specified direction.
        If warp is not x1, rotation speeds for all vessels are set to zero."""
        if warp == 1:
            self.rot_speed[vessel] += self.rot_acc[vessel] * direction
            self.rot_angle += self.rot_speed
            self.rot_angle = np.where(self.rot_angle > 2*np.pi, 0, self.rot_angle)
            self.rot_angle = np.where(self.rot_angle < 0, 2*np.pi, self.rot_angle)
        else:
            self.rot_speed *= 0.0
        return self.rot_angle
