import importlib.util
import math
from itertools import repeat

import numpy as np
import pygame

from volatilespace import defaults, peripherals
from volatilespace.physics.enhanced_kepler_solver import solve_kepler_ell
from volatilespace.physics.phys_shared import (
    c,
    culling,
    curve_move_to,
    curve_points,
    gc,
    ls,
    mag,
    ms,
    newton_root_kepler_hyp,
    orbit_time_to,
    sigma,
)

numba_avail = bool(importlib.util.find_spec("numba"))


def calc_orb_one(body, ref, mass, gc, coi_coef, a, ecc):
    """Calculate additional body orbital parameters"""
    if body:   # skip root
        u = gc * mass[ref]   # standard gravitational parameter
        f = a * ecc
        b = math.sqrt(abs(f**2 - a**2))
        if a > 0:   # if eccentricity is larger than 1, semi major will be negative
            coi = a * (mass[body] / mass[ref])**(coi_coef)
        else:
            coi = 0

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
        return b, f, coi, pe_d, ap_d, period, n, u
    return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


def temp_color(temp, base_color):
    """Calculate color depending on temperature"""
    # mixed color
    fg_opacity = np.where(
        np.logical_and(temp > 1000, temp <= 2300),
        1 - 1 / (1300 / (temp - 1000)),
        -1,
    )
    color = np.copy(base_color)
    color[:, 0] = np.where(
        fg_opacity != -1,
        base_color[:, 0] * fg_opacity + 255 * (1 - fg_opacity),
        base_color[:, 0],
    )
    color[:, 1] = np.where(
        fg_opacity != -1,
        base_color[:, 1] * fg_opacity + 184 * (1 - fg_opacity),
        base_color[:, 1],
    )
    color[:, 2] = np.where(
        fg_opacity != -1,
        base_color[:, 2] * fg_opacity + 111 * (1 - fg_opacity),
        base_color[:, 2],
    )

    # heated color
    color[:, 0] = np.where(
        temp > 2300,
        130 + 125 / (1 + (temp / 5922)**55.525)**0.065,
        color[:, 0],
    )
    color[:, 1] = np.where(
        np.logical_and(temp > 2300, temp <= 6000),
        257 - 73 / (1 + (temp / 4742)**6.687),
        color[:, 1],
    )
    color[:, 1] = np.where(
        temp > 6000,
        170 + 165766330 / (1 + (temp / 24)**2.651),
        color[:, 1],
    )
    color[:, 2] = np.where(
        temp > 2300,
        283 - 176 / (1 + (temp / 4493)**5.792),
        color[:, 2],
    )
    return np.clip(color.astype(int), 0, 255)


# if numba is enabled, compile functions ahead of time
use_numba = peripherals.load_settings("game", "numba")
if numba_avail and use_numba:
    enable_fastmath = peripherals.load_settings("game", "fastmath")
    jitkw = {"cache": True, "fastmath": enable_fastmath}   # numba JIT setings



class Physics():
    """Body physics class"""
    def __init__(self):
        # body internal
        self.names = np.array([])
        self.mass = np.array([])
        self.den = np.array([])
        self.radius = np.array([])
        self.base_color = np.empty((0, 3), int)   # original color unaffected by temperature
        self.types = np.array([])
        self.atm_pres0 = np.array([])
        self.atm_scale_h = np.array([])
        self.atm_den0 = np.array([])
        self.atm_h = np.array([])
        # body orbit main
        self.a = np.array([])
        self.ecc = np.array([])
        self.pea = np.array([])
        self.ma = np.array([])
        self.ref = np.array([])
        self.dr = np.array([])
        # body orbit extra
        self.b = np.array([])
        self.f = np.array([])
        self.pe_d = np.array([])
        self.ap_d = np.array([])
        self.period = np.array([])
        self.n = np.array([])
        self.coi = np.array([])
        self.curves = np.array([])
        self.pos = np.array([])
        self.ea = np.array([])
        self.u = np.array([])
        self.gc = defaults.sim_config["gc"]
        self.rad_mult = defaults.sim_config["rad_mult"]
        self.mass_thermal_mult = defaults.sim_config["mass_thermal_mult"]
        self.coi_coef = defaults.sim_config["coi_coef"]
        self.reload_settings()


    def reload_settings(self):
        """Reload all settings, should be run every time game is entered"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
        self.curve_points = int(peripherals.load_settings("graphics", "curve_points"))   # number of points from which curve is drawn
        self.curves = np.zeros((len(self.mass), self.curve_points, 2))
        self.t = np.linspace(-np.pi, np.pi, self.curve_points)   # parameter
        for body, _ in enumerate(self.names):
            self.curve(body)


    def load_conf(self, conf):
        """Loads physics related config"""
        self.gc = conf["gc"]
        self.rad_mult = conf["rad_mult"]
        self.mass_thermal_mult = conf["mass_thermal_mult"]
        self.coi_coef = conf["coi_coef"]
        self.min_mass = conf["min_planet_mass"]

    def load(self, conf, body_data, body_orb_data):
        """Load new system"""
        self.load_conf(conf)
        self.names = body_data["name"]
        self.mass = body_data["mass"]
        self.den = body_data["den"]
        self.base_color = body_data["color"]
        self.atm_pres0 = body_data["atm_pres0"]
        self.atm_scale_h = body_data["atm_scale_h"]
        self.atm_den0 = body_data["atm_den0"]
        # body orbit
        self.a = body_orb_data["a"]
        self.ecc = body_orb_data["ecc"]
        self.pea = body_orb_data["pe_arg"]
        self.ma = body_orb_data["ma"]
        self.ref = body_orb_data["ref"]
        self.dr = body_orb_data["dir"]
        self.pos = np.zeros([len(self.mass), 2])   # position will be updated later
        self.ea = np.zeros(len(self.mass))
        self.curves = np.zeros((len(self.mass), self.curve_points, 2))   # shape: (vessel, points, axes)
        self.curves_mov = np.zeros((len(self.mass), self.curve_points, 2))


    def culling(self, sim_screen, zoom):
        """
        Return separate lists of:
        - Bodies whose COI is visible on screen
        - Bodies that are visible on screen (atmosphere incl)
        - Bodies whose orbits are inside COI that is visible on screen and COI is larger than N pixels
        """
        atm_radius = (self.radius + self.atm_h) * zoom
        visible_bodies_truth = culling(self.pos, atm_radius, sim_screen, zoom)
        visible_bodies = np.arange(len(self.mass))[visible_bodies_truth]
        visible_coi_truth = culling(self.pos, self.coi, sim_screen, zoom)
        visible_coi = np.concatenate(([0], np.arange(len(self.mass))[visible_coi_truth]))
        visible_orbits_truth = np.logical_and(visible_coi_truth[self.ref], self.coi[self.ref] > 8 / zoom)
        visible_orbits_truth = np.logical_or(visible_orbits_truth, self.ref == 0)   # incl all orbits around main ref
        visible_orbits_truth = np.logical_and(visible_orbits_truth, self.a * zoom < self.screen_x*15)
        visible_orbits = np.arange(len(self.mass))[visible_orbits_truth]
        # not returning truth values so "for vessel in visible_bodies" can easily be done
        return visible_bodies, visible_coi, visible_orbits


    def initial(self, warp):
        """
        Do all body related physics.
        This should be done only if something changed on body or it's orbit.
        """

        # body data
        volume = self.mass / self.den
        self.radius = self.rad_mult * np.cbrt(3 * volume / (4 * np.pi))
        thermal_mass = self.mass * self.mass_thermal_mult
        thermal_volume = thermal_mass / self.den
        thermal_radius = np.cbrt(3 * thermal_volume / (4 * np.pi))
        luminosity = ls * (thermal_mass / ms)**3.5   # mass and radius must be adjusted
        temp = luminosity**(1/4) / (np.sqrt(thermal_radius) * np.sqrt(2) * np.pi**(1/4) * sigma**(1/4))
        rad_sc = 2 * thermal_mass * gc / c**2   # Schwarzschild radius
        # because thermal_mass is used, scale rad_sc with proportion to thermal radius
        rad_sc = rad_sc * self.radius / thermal_radius
        color = temp_color(temp, self.base_color)
        surf_grav = self.mass / self.radius**2
        self.atm_h = np.zeros(len(self.mass))
        for body, _ in enumerate(self.mass):
            if all(x != 0 for x in [self.atm_pres0[body], self.atm_scale_h[body], self.atm_den0[body]]):
                self.atm_h[body] = - self.atm_scale_h[body] * math.log(0.001 / self.atm_den0[body]) * self.rad_mult

        # classification
        self.types = np.zeros(len(self.mass))  # it is a dwarf planet
        self.types = np.where(self.mass > self.min_mass, 1, self.types)    # if it has high enough mass: it is a solid planet
        self.types = np.where(self.den < 1500, 2, self.types)    # if it is not dense enough: it is a gas planet
        self.types = np.where(temp > 1000, 3, self.types)    # if temperature is over 1000 degrees: it is a star
        self.types = np.where(rad_sc > self.radius, 4, self.types)   # if schwarzschild radius is greater than radius: it is a black hole

        # star classification
        stars = np.where(self.types == 3, True, False)
        stellar_class = np.where(stars, "M", "Unknown")
        stellar_class = np.where(temp > 3900, "K", stellar_class)
        stellar_class = np.where(temp > 5300, "G", stellar_class)
        stellar_class = np.where(temp > 6000, "F", stellar_class)
        stellar_class = np.where(temp > 7300, "A", stellar_class)
        stellar_class = np.where(temp > 10000, "B", stellar_class)
        stellar_class = np.where(temp > 33000, "O", stellar_class)

        # recolor black hole
        bh = np.where(rad_sc > self.radius)
        color[bh] = [0, 0, 0]
        # black hole does not have atmosphere [citation needed]
        self.atm_h = np.where(rad_sc > self.radius, 0, self.atm_h)

        body_data = {
            "name": self.names,
            "type": self.types,
            "mass": self.mass,
            "den": self.den,
            "temp": temp,
            "lum": luminosity,
            "class": stellar_class,
            "color_b": self.base_color,
            "color": color,
            "radius": self.radius,
            "rad_sc": rad_sc,
            "surf_grav": surf_grav,
            "atm_pres0": self.atm_pres0,
            "atm_scale_h": self.atm_scale_h,
            "atm_den0": self.atm_den0,
            "atm_h": self.atm_h,
        }

        # orbit data
        values = list(map(calc_orb_one, list(range(len(self.mass))), self.ref, repeat(self.mass), repeat(self.gc), repeat(self.coi_coef), self.a, self.ecc))
        self.b, self.f, self.coi, self.pe_d, self.ap_d, self.period, self.n, self.u = list(map(np.array, zip(*values)))
        body_orb = {
            "a": self.a,
            "b": self.b,
            "f": self.f,
            "coi": self.coi,
            "ref": self.ref,
            "ecc": self.ecc,
            "pe_d": self.pe_d,
            "ap_d": self.ap_d,
            "pea": self.pea,
            "n": self.n,
            "dir": self.dr,
            "per": self.period,
            "u": self.u,
        }

        # move
        self.move(warp)
        for body, _ in enumerate(self.names):
            self.curve(body)
        self.curve_move()

        return body_data, body_orb, self.pos, self.ma, self.ea, self.curves_mov


    def curve(self, body):
        """
        Calculate RELATIVE conic curve line points coordinates for one body.
        This should be done only if something changed on body or it's orbit, and after points().
        """
        self.curves[body] = curve_points(self.ecc[body], self.a[body], self.b[body], self.pea[body], self.t)


    def move(self, warp):
        """Move body with mean motion"""
        self.ma += self.dr * self.n * warp
        self.ma = np.where(self.ma > 2*np.pi, self.ma - 2*np.pi, self.ma)
        self.ma = np.where(self.ma < 0, self.ma + 2*np.pi, self.ma)
        bodies_sorted = np.argsort(self.coi)[-1::-1]
        for body in bodies_sorted:
            pea = self.pea[body]
            ecc = self.ecc[body]
            a = self.a[body]
            b = self.b[body]
            if ecc < 1:
                ea = solve_kepler_ell(ecc, self.ma[body], 1e-10)
                pr_x = a * math.cos(ea) - self.f[body]
                pr_y = b * math.sin(ea)
            else:
                ea = newton_root_kepler_hyp(ecc, self.ma[body], self.ea[body])
                pr_x = a * np.cosh(ea) - self.f[body]
                pr_y = b * np.sinh(ea)
            pr = np.array([pr_x * math.cos(pea - np.pi) - pr_y * math.sin(pea - np.pi),
                           pr_x * math.sin(pea - np.pi) + pr_y * math.cos(pea - np.pi)])
            self.pos[body] = self.pos[self.ref[body]] + pr
            self.ea[body] = ea
        return self.pos, self.ma, self.ea


    def selected(self, body):
        """
        Do physics for selected body.
        This should be done every tick after body_move().
        """
        if body:
            pos_ref = self.pos[self.ref[body]]
            periapsis_arg = self.pea[body]
            a = self.a[body]
            b = self.b[body]
            ecc = self.ecc[body]
            ea = self.ea[body]
            ma = self.ma[body]
            u = self.u[body]
            ap_d = self.ap_d[body]
            pe_d = self.pe_d[body]
            dr = self.dr[body]
            n = self.n[body]

            rel_pos = self.pos[body] - pos_ref
            distance = mag(rel_pos)   # distance to parent
            speed_orb = math.sqrt(u * ((2 / distance) - (1 / a)))   # velocity vector magnitude from vis-viva eq
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
                    pe_t = orbit_time_to(ma, 0, ecc, dr, n)
                    ap = np.array([ap_d * math.cos(periapsis_arg), ap_d * math.sin(periapsis_arg)]) + pos_ref
                    ap_t = orbit_time_to(ma, np.pi, ecc, dr, n)
                else:
                    pe_t = orbit_time_to(ma, 0, ecc, dr, n)
                    # there is no apoapsis
                    ap = np.array([0, 0])
                    ap_t = 0
            else:   # circle
                ma = ta
                pe_t = orbit_time_to(ma, 0, ecc, dr, n)
                # there is no apoapsis
                ap = np.array([0, 0])
                ap_t = 0
            pe = np.array([pe_d * math.cos(periapsis_arg - np.pi), pe_d * math.sin(periapsis_arg - np.pi)]) + pos_ref

            return ta, pe, pe_t, ap, ap_t, distance, speed_orb, speed_hor, speed_vert
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


    def curve_move(self):
        """
        Move all orbit curves to parent position.
        This should be done every tick after move().
        """
        self.curves_mov = curve_move_to(self.curves, self.pos, self.ref, self.f, self.pea)
        return self.curves_mov
