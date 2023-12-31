from ast import literal_eval as leval
import math
from itertools import repeat
import numpy as np
try:   # to allow building without numba
    from numba import njit, types, int32, int64, float64, bool_
    numba_avail = True
except ImportError:
    numba_avail = False

from volatilespace import fileops
from volatilespace import defaults


###### --Constants-- ######
c = 299792458   # speed of light in vacuum
k = 1.381 * 10**-23   # boltzman constant
m_h = 1.674 * 10**-27    # hydrogen atom mass in kg
m_he = 6.646 * 10**-27   # helium atom mass in kg
mp = (m_h * 99 + m_he * 1) / 100   # average particle mass   # depends on star age


###### --Functions-- ######
def newton_root(function, derivative, root_guess, variables={}):
    """Newton root solver"""
    root = root_guess   # take guessed root input
    for _ in range(50):
        delta_x = function(root, variables) / derivative(root, variables)   # guess correction
        root -= delta_x   # better guess
        if abs(delta_x) < 1e-10:   # if correction is small enough:
            return root   # return root
    return root   # if it is not returned above (it has too high deviation) return it anyway


def keplers_eq(ea, variables):
    """Keplers equation"""
    return ea - variables['e'] * np.sin(ea) - variables['Ma']


def keplers_eq_derivative(ea, variables):
    """Derivative of keplers equation"""
    return 1.0 - variables['e'] * np.cos(ea)


def keplers_eq_hyp(ea, variables):
    """Keplers equation for hyperbola"""
    return ea - variables['e'] * np.sinh(ea) - variables['Ma']


def keplers_eq_hyp_derivative(ea, variables):
    """Derivative of keplers equation for hyperbola"""
    return 1.0 - variables['e'] * np.cosh(ea)


def get_angle(a, b, c):
    """Angle between 3 points in 2D or 3D"""
    ba = a - b   # get 2 vectors from 3 points
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))   # angle between 2 vectors
    return np.arccos(cosine_angle)


def orbit_time_to(mean_anomaly, target_angle, period, dr):
    """Time to point on orbit"""
    return period - (dr * mean_anomaly + target_angle)*(period / (2 * np.pi)) % period


def dot_2d(v1, v2):
    """Fastest 2D dot product. It is slightly faster than built in: v1 @ v2."""
    return v1[0]*v2[0] + v1[1]*v2[1]


def mag(vector):
    """Vector magnitude"""
    return math.sqrt(dot_2d(vector, vector))


def cross_2d(v1, v2):
    """Faster than numpy's"""
    return np.array([v1[0]*v2[1] - v1[1]*v2[0]])


def culling(curve, sim_screen, ref_coi, curve_points, cull):
    sim_screen_size = np.absolute(sim_screen[1] - sim_screen[0])
    x_max = np.amax(curve[:, 0])
    y_max = np.amax(curve[:, 1])
    x_min = np.amin(curve[:, 0])
    y_min = np.amin(curve[:, 1])
    diff = np.array([x_max - x_min, y_max - y_min])
    screen_diff = sim_screen_size / diff
    if ref_coi != 0.0:
        if diff[0] + diff[1] > ref_coi * 3:
            screen_diff = sim_screen_size / np.array([ref_coi * 1.5, ref_coi * 1.5])
    if screen_diff[0] + screen_diff[1] < 130:
        if cull:
            factor = int(curve_points / 25)
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


def calc_orb_one(body, ref, mass, gc, coi_coef, a, ecc):
    """Additional body orbital parameters."""
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
    else:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


def temp_color(temp, base_color):
    """Set color depending on temperature."""
    color = base_color[:]
    # temperature to 1000 - BASE
    # temperature from 1000 to 3000 - RE
    color[:, 0] = np.where(temp > 1000, base_color[:, 0] + ((255 - base_color[:, 0]) * (temp - 1000)) / 2000, base_color[:, 0])   # base red to full red
    color[:, 1] = np.where(temp > 1000, base_color[:, 1] - ((base_color[:, 1]) * (temp - 1000)) / 2000, base_color[:, 1])   # base green to no green
    color[:, 2] = np.where(temp > 1000, base_color[:, 2] - ((base_color[:, 2]) * (temp - 1000)) / 2000, base_color[:, 2])   # base blue to no blue
    # temperature from 3000 to 6000 - YELLOW
    color[:, 1] = np.where(temp > 3000, (255 * (temp - 3000)) / 3000, color[:, 1])   # no green to full green
    # temperature from 6000 to 10000 - WHITE
    color[:, 2] = np.where(temp > 6000, (255 * (temp - 6000)) / 4000, color[:, 2])   # no blue to full blue
    # temperature from 10000 to 30000 - BLUE
    color[:, 0] = np.where(temp > 10000, 255 - ((255 * (temp - 10000) / 10000)), color[:, 0])   # full red to no red
    color[:, 1] = np.where(temp > 10000, 255 - ((135 * (temp - 10000) / 20000)), color[:, 1])   # full green to 120 green
    color = np.clip(color, 0, 255)
    return color


# if numba is enabled, compile functions ahead of time
use_numba = leval(fileops.load_settings("game", "numba"))
if numba_avail and use_numba:
    enable_fastmath = leval(fileops.load_settings("game", "fastmath"))
    jitkw = {"cache": True, "fastmath": enable_fastmath}   # numba JIT setings
    dot_2d = njit(float64(float64[:], float64[:]), **jitkw)(dot_2d)
    mag = njit(float64(float64[:]), **jitkw)(mag)
    cross_2d = njit(float64[:](float64[:], float64[:]), **jitkw)(cross_2d)
    culling = njit(bool_(float64[:, :], float64[:, :], float64, int32, bool_), **jitkw)(culling)



class Physics():
    def __init__(self):
        # body internal
        self.names = np.array([])
        self.visible_bodies = []
        self.mass = np.array([])
        self.den = np.array([])
        self.base_color = np.empty((0, 3), int)   # original color unaffected by temperature
        self.types = np.array([])
        self.atm_pres0 = np.array([])
        self.atm_scale_h = np.array([])
        self.atm_den0 = np.array([])
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
        self.coi_coef = defaults.sim_config["coi_coef"]
        self.reload_settings()


    def reload_settings(self):
        """Reload all settings, should be run every time game is entered"""
        self.curve_points = int(fileops.load_settings("graphics", "curve_points"))   # number of points from which curve is drawn
        self.curves = np.zeros((len(self.mass), self.curve_points, 2))
        self.cull = leval(fileops.load_settings("graphics", "culling"))
        # parameters
        self.ell_t = np.linspace(-np.pi, np.pi, self.curve_points)   # ellipse parameter
        self.par_t = np.linspace(- np.pi - 1, np.pi + 1, self.curve_points)   # parabola parameter


    def load_conf(self, conf):
        """Loads physics related config."""
        self.gc = conf["gc"]
        self.rad_mult = conf["rad_mult"]
        self.coi_coef = conf["coi_coef"]

    def load(self, conf, body_data, body_orb_data):
        """Load new system."""
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


    def culling(self, sim_screen):
        """Returns list of bodies orbits that are visible on screen and are large enough.
        Checking for orbits that are on screen can be toggle in settings"""
        values = list(map(culling, self.curves_mov, repeat(sim_screen), self.coi[self.ref], repeat(self.curve_points), repeat(self.cull)))
        self.visible_bodies = np.concatenate(([0], np.arange(len(self.mass))[values]))
        return self.visible_bodies


    def initial(self, warp):
        """Do all body related physics. This should be done only if something changed on body or it's orbit."""

        # BODY DATA #
        volume = self.mass / self.den
        size = self.rad_mult * np.cbrt(3 * volume / (4 * np.pi))
        core_temp = (self.gc * mp * self.mass) / ((3/2) * k * size * self.rad_mult)
        temp = 0 / core_temp   # surface temperature # ### temporarily ###
        rad_sc = 2 * self.mass * self.gc / c**2   # Schwarzschild radius
        color = temp_color(temp, self.base_color)
        surf_grav = self.gc * self.mass / size**2
        atm_h = np.zeros(len(self.mass))
        for body, _ in enumerate(self.mass):
            if all(x != 0 for x in [self.atm_pres0[body], self.atm_scale_h[body], self.atm_den0[body]]):
                atm_h[body] = - self.atm_scale_h[body] * math.log(0.001 / self.atm_den0[body]) * self.rad_mult

        # CLASSIFICATION #
        self.types = np.zeros(len(self.mass))  # it is moon
        self.types = np.where(self.mass > 200, 1, self.types)    # if it has high enough mass: it is solid planet
        self.types = np.where(self.den < 1, 2, self.types)    # if it is not dense enough: it is gas planet
        self.types = np.where(self.mass > 5000, 3, self.types)   # ### temporarily ###
        # self.types = np.where(self.temp > 1000, 3, self.types)    # if temperature is over 1000 degrees: it is a star
        # self.types = np.where(self.rad_sc > self.rad, 4, self.types)   # if schwarzschild radius is greater than radius: it is black hole
        body_data = {"name": self.names,
                     "type": self.types,
                     "mass": self.mass,
                     "den": self.den,
                     "temp": temp,
                     "color_b": self.base_color,
                     "color": color,
                     "size": size,
                     "rad_sc": rad_sc,
                     "surf_grav": surf_grav,
                     "atm_pres0": self.atm_pres0,
                     "atm_scale_h": self.atm_scale_h,
                     "atm_den0": self.atm_den0,
                     "atm_h": atm_h}

        # ORBIT DATA #
        values = list(map(calc_orb_one, list(range(len(self.mass))), self.ref, repeat(self.mass), repeat(self.gc), repeat(self.coi_coef), self.a, self.ecc))
        self.b, self.f, self.coi, self.pe_d, self.ap_d, self.period, self.n, self.u = list(map(np.array, zip(*values)))
        body_orb = {"a": self.a,
                    "b": self.b,
                    "f": self.f,
                    "coi": self.coi,
                    "ref": self.ref,
                    "ecc": self.ecc,
                    "pe_d": self.pe_d,
                    "ap_d": self.ap_d,
                    "pea": self.pea,
                    "dir": self.dr,
                    "per": self.period}

        # MOVE #
        self.move(warp)
        for body, _ in enumerate(self.names):
            self.curve(body)
        self.curve_move()

        return body_data, body_orb, self.pos, self.ma, self.curves_mov


    def curve(self, body):
        """Calculate RELATIVE conic curve line points coordinates for one body.
        This should be done only if something changed on body or it's orbit, and after points()."""
        ecc = self.ecc[body]
        pea = self.pea[body]

        # curves points
        if ecc < 1:   # ellipse
            curves = np.array([self.a[body] * np.cos(self.ell_t), self.b[body] * np.sin(self.ell_t)])   # raw ellipses
        else:
            curves = np.array([-self.a[body] * np.cosh(self.ell_t), self.b[body] * np.sinh(self.ell_t)])   # raw hyperbolas
            # parametric equation for circle is same as for ellipse, just semi_major = semi_minor, thus it is not required
        # rotation matrix
        rot = np.array([[np.cos(pea), - np.sin(pea)], [np.sin(pea), np.cos(pea)]])
        self.curves[body] = np.swapaxes(np.dot(rot, curves), 0, 1)


    def move(self, warp):
        """Move body with mean motion."""
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
                ea = newton_root(keplers_eq, keplers_eq_derivative, self.ea[body], {'Ma': self.ma[body], 'e': self.ecc[body]})
                pr_x = a * math.cos(ea) - self.f[body]
                pr_y = b * math.sin(ea)
            else:
                ea = newton_root(keplers_eq_hyp, keplers_eq_hyp_derivative, self.ea[body], {'Ma': self.ma[body], 'e': self.ecc[body]})
                pr_x = a * np.cosh(ea) - self.f[body]
                pr_y = b * np.sinh(ea)
            pr = np.array([pr_x * math.cos(pea - np.pi) - pr_y * math.sin(pea - np.pi),
                           pr_x * math.sin(pea - np.pi) + pr_y * math.cos(pea - np.pi)])
            self.pos[body] = self.pos[self.ref[body]] + pr
            self.ea[body] = ea

        return self.pos, self.ma


    def selected(self, body):
        """Do physics for selected body. This should be done every tick after body_move()."""
        if body:
            pos_ref = self.pos[self.ref[body]]
            periapsis_arg = self.pea[body]
            a = self.a[body]
            b = self.b[body]
            ecc = self.ecc[body]
            ea = self.ea[body]
            ma = self.ma[body]
            period = self.period[body]
            u = self.u[body]
            ap_d = self.ap_d[body]
            pe_d = self.pe_d[body]
            dr = self.dr[body]

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
        else:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


    def curve_move(self):
        """Move all orbit curves to parent position.
        This should be done every tick after move()."""
        focus_x = self.f * np.cos(self.pea)
        focus_y = self.f * np.sin(self.pea)
        focus = np.column_stack((focus_x, focus_y))
        self.curves_mov = self.curves + focus[:, np.newaxis, :] + self.pos[self.ref, np.newaxis, :]
        return self.curves_mov
