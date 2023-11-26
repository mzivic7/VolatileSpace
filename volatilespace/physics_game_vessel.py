from ast import literal_eval as leval
import math
from itertools import repeat
import numpy as np
try:   # to allow building without numba
    from numba import njit, float64
    numba_avail = True
except ImportError:
    numba_avail = False

from volatilespace import fileops
from volatilespace import defaults


###### --Functions-- ######
def newton_root(function, derivative, root_guess, variables={}):
    """Newton root solver"""
    root = root_guess   # take guessed root input
    for _ in range(100):
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


def loc2glob(a, b, f, ecc, pea, pos, ea):
    if ea:
        if ecc < 1:
            x_n = a * np.cos(ea) - f
            y_n = b * np.sin(ea)
        else:
            x_n = a * np.cosh(ea) - f
            y_n = b * np.sinh(ea)
        x = (x_n * np.cos(pea - np.pi) - y_n * np.sin(pea - np.pi)) + pos[0]
        y = (x_n * np.sin(pea - np.pi) + y_n * np.cos(pea - np.pi)) + pos[1]
        return [x, y]
    else:
        return [None, None]


def orbit_intersect(a, b, ecc, c_x, c_y, r):
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
        roots = np.polynomial.polynomial.polyroots([a_0, a_1, a_2, a_3, a_4])
        # take only non-complex roots
        real_roots = np.real(roots[np.isreal(roots)])

        if any(real_roots):
            ea = np.arctan2(2*real_roots, 1.0 - real_roots**2)
            if a_4 <= 0:
                ea += np.pi
            return ea % (2*np.pi)
        else:
            return np.array([np.NaN])
    else:   # hyperbola
        a_0 = -a**2 * (c_y**2 + b**2) + b**2 * (c_x + r)**2
        a_1 = -4 * a**2 * r * c_y
        a_2 = -2 * (a**2 * (c_y**2 + b**2 + 2*r**2) + b**2 * (r**2 - c_x**2))
        a_3 = -4 * a**2 * r * c_y
        a_4 = -a**2 * (c_y**2 + b**2) + b**2 * (c_x - r)**2
        roots = np.polynomial.polynomial.polyroots([a_0, a_1, a_2, a_3, a_4])
        real_roots = np.real(roots[np.isreal(roots)])
        if any(real_roots):
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
        angle = np.absolute(ea_vessel - ea_points)
        # where ea_vessel is larger: invert
        angle = np.where(ea_vessel > ea_points, 2*np.pi - angle, angle)
        if direction < 0:   # if direction is clockwise: invert
            angle = np.pi*2 - angle
        ea_points_sorted = ea_points[np.argsort(angle)]
        return np.array([ea_points_sorted[0], ea_points_sorted[-1]])
    else:
        return None


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
    dot_2d = njit(float64(float64[:], float64[:]), **jitkw)(dot_2d)
    mag = njit(float64(float64[:]), **jitkw)(mag)
    cross_2d = njit(float64[:](float64[:], float64[:]), **jitkw)(cross_2d)
    # ellipse_circle = njit(float64[:](float64, float64, float64, float64, float64))(ellipse_circle)   # scipy is required



class Physics():
    def __init__(self):
        # vessel internal
        self.names = np.array([])
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
        self.u = np.array([])
        self.body_mass = np.array([])
        self.body_pos = np.array([])
        self.gc = defaults.sim_config["gc"]
        self.rad_mult = defaults.sim_config["rad_mult"]
        self.coi_coef = defaults.sim_config["coi_coef"]
        self.vessl_scale = defaults.sim_config["vessel_scale"]
        self.reload_settings()


    def reload_settings(self):
        """Reload all settings, should be run every time game is entered"""
        self.curve_points = int(fileops.load_settings("graphics", "curve_points"))   # number of points from which curve is drawn
        # parameters
        self.ell_t = np.linspace(-np.pi, np.pi, self.curve_points)   # ellipse parameter
        self.par_t = np.linspace(- np.pi - 1, np.pi + 1, self.curve_points)   # parabola parameter


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
        self.body_coi = body_orb["coi"]
        self.load_conf(conf)
        self.names = vessel_data["name"]
        # vessel orbit
        self.a = vessel_orb_data["a"]
        self.ecc = vessel_orb_data["ecc"]
        self.pea = vessel_orb_data["pe_arg"]
        self.ma = vessel_orb_data["ma"]
        self.ref = vessel_orb_data["ref"]
        self.dr = vessel_orb_data["dir"]
        self.pos = np.zeros([len(self.names), 2])   # position will be updated later
        self.ea = np.zeros(len(self.names))
        self.curves = np.zeros((len(self.names), 2, self.curve_points))   # shape: (vessel, axis, points)
        # orbit points
        self.body_impact = np.zeros((len(self.names), 2)) * np.nan
        self.coi_leave = np.zeros((len(self.names), 2)) * np.nan
        self.coi_enter = np.zeros((len(self.names), 2)) * np.nan
        self.curve_data_light = np.zeros((len(self.names), 5)) * np.nan
        self.curve_data_dark = np.zeros((len(self.names), 4)) * np.nan

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
        return loc2glob(a, b, f, ecc, pea, ref, ea)


    def initial(self, warp, body_pos):
        # VESSEL DATA #
        vessel_data = {"name": self.names
                       }

        # ORBIT DATA #
        if len(self.names):
            values = list(map(calc_orb_one, list(range(len(self.names))), self.ref, repeat(self.body_mass), repeat(self.gc), self.a, self.ecc))
            self.b, self.f, self.pe_d, self.ap_d, self.period, self.n, self.u = list(map(np.array, zip(*values)))
        vessel_orb = {"a": self.a,
                      "ref": self.ref,
                      "ecc": self.ecc,
                      "pe_d": self.pe_d,
                      "ap_d": self.ap_d,
                      "pea": self.pea,
                      "dir": self.dr,
                      "per": self.period}

        # MOVE #
        self.move(warp, body_pos)
        for vessel, _ in enumerate(self.names):
            self.curve(vessel)
        curves = self.curve_move()
        self.curve_points_move()

        # POINTS #
        for vessel, _ in enumerate(self.names):
            self.points(vessel)

        return vessel_data, vessel_orb, self.pos, self.ma, curves, self.curve_data_light, self.curve_data_dark


    def change_vessel(self, vessel):
        """Do all vessel related physics to one vessel. This should be done only if something changed on vessel or it's orbit."""

        # this is packed in list because reading from dict is slow

        # VESSEL DATA #
        vessel_data = [self.names]

        # ORBIT DATA #
        a = self.a[self]
        ecc = self.ecc[vessel]
        self.u[vessel] = u = self.gc * self.body_mass[self.ref[vessel]]   # standard gravitational parameter
        self.f[vessel] = f = a * ecc
        self.b[vessel] = math.sqrt(abs(f**2 - a**2))

        if ecc != 0:   # if orbit is not circle
            self.pe_d[vessel] = a * (1 - ecc)
            if ecc < 1:   # if orbit is ellipse
                self.period[vessel] = 2 * np.pi * math.sqrt(a**3 / u)
                self.ap_d[vessel] = a * (1 + ecc)
            else:
                if ecc > 1:   # hyperbola
                    self.pe_d[vessel] = a * (1 - ecc)
                else:   # parabola
                    self.pe_d[vessel] = a
                self.period[vessel] = 0   # period is undefined
                # there is no apoapsis
                self.ap_d[vessel] = 0
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

        return vessel_data, vessel_orb


    def curve(self, vessel):
        """Calculate RELATIVE conic curve line points coordinates for one vessel.
        This should be done only if something changed on vessel or it's orbit, and after points()."""
        ecc = self.ecc[vessel]
        pea = self.pea[vessel]

        # curves points
        if ecc < 1:   # ellipse
            curves = np.array([self.a[vessel] * np.cos(self.ell_t), self.b[vessel] * np.sin(self.ell_t)])   # raw ellipses
        else:
            curves = np.array([-self.a[vessel] * np.cosh(self.ell_t), self.b[vessel] * np.sinh(self.ell_t)])   # raw hyperbolas
            # parametric equation for circle is same as for ellipse, just semi_major = semi_minor, thus it is not required
        # rotation matrix
        rot = np.array([[np.cos(pea), - np.sin(pea)], [np.sin(pea), np.cos(pea)]])
        self.curves[vessel] = np.dot(rot, curves)


    def points(self, vessel):
        """Find characteristic points RELATIVE UNROTATED position for one body.
        This should be done only if something changed on vessel or it's orbit, after move()."""
        ref = self.ref[vessel]
        ecc = self.ecc[vessel]
        dr = self.dr[vessel]
        xc = self.f[vessel]   # body is in focus
        yc = 0

        body_impact_all = orbit_intersect(self.a[vessel], self.b[vessel], ecc, xc, yc, self.body_size[ref])
        self.body_impact[vessel, :] = next_point(self.ea[vessel], body_impact_all, dr)

        coi_leave_all = orbit_intersect(self.a[vessel], self.b[vessel], ecc, xc, yc, self.body_coi[ref])
        self.coi_leave[vessel] = next_point(self.a[vessel], coi_leave_all, dr)

        # TODO: leave_coi
        # pea = self.pea[vessel]
        # body_x = self.body_pos[ref, 0]
        # body_y = self.body_pos[ref, 1]
        # focus_x = self.f[vessel] * np.cos(pea)
        # focus_y = self.f[vessel] * np.sin(pea)
        # pos = [body_x + focus_x, body_y + focus_y]
        # xc = math.cos(-pea) * (body_x - pos[0]) - math.sin(-pea) * (body_y - pos[1])
        # yc = math.sin(-pea) * (body_x - pos[0]) + math.cos(-pea) * (body_y - pos[1])
        # coi_enter_all = ellipse_circle(self.a[vessel], self.b[vessel], xX, yX, self.body_coi[X])
        # self.coi_enter[vessel] = next_point(self.a[vessel], coi_enter_all, dr)
        self.coi_enter[vessel] = None


    def move(self, warp, body_pos):
        """Move vessel with mean motion."""
        self.body_pos = body_pos
        hyp = np.where(self.ecc > 1, -1, 1)
        self.ma += self.dr * self.n * warp * hyp
        self.ma = np.where(np.logical_and(self.ecc < 1, self.ma > 2*np.pi), self.ma - 2*np.pi, self.ma)
        self.ma = np.where(np.logical_and(self.ecc < 1, self.ma < 0), self.ma + 2*np.pi, self.ma)
        for vessel, _ in enumerate(self.names):
            if self.ecc[vessel] < 1:
                ea = newton_root(keplers_eq, keplers_eq_derivative, self.ea[vessel], {'Ma': self.ma[vessel], 'e': self.ecc[vessel]})
            else:
                ea = newton_root(keplers_eq_hyp, keplers_eq_hyp_derivative, self.ea[vessel], {'Ma': self.ma[vessel], 'e': self.ecc[vessel]})
            self.pos[vessel] = self.ea2coord(vessel, ea)
            self.ea[vessel] = ea

        return self.pos, self.ma


    def curve_move(self):
        """Move all orbit curves to parent position.
        This should be done every tick after vessel_move()."""
        focus_x = self.f * np.cos(self.pea)
        focus_y = self.f * np.sin(self.pea)
        focus = np.column_stack((focus_x, focus_y))
        curves = self.curves + focus[:, :, np.newaxis] + self.body_pos[self.ref, :, np.newaxis]
        return curves


    def curve_points_move(self):
        """Move all relevant curve points and calculates curves ranges.
        This should be done every tick after curve_move()."""
        for vessel, _ in enumerate(self.names):
            ea = self.ea[vessel]
            ecc = self.ecc[vessel]
            # types: 1-impact, 2-leave_coi(0,pi) 3-leave_coi(pi,2pi), 4-leave_coi_hyp, 5-enter_coi
            if not np.isnan(self.body_impact[vessel, 0]):
                ea_next = self.body_impact[vessel, 0]
                ea_prev = self.body_impact[vessel, 1]
                coord_next = self.ea2coord(vessel, ea_next)
                coord_prev = self.ea2coord(vessel, ea_prev)
                if ecc < 1:   # for ellipse
                    ea_vessel = round(ea * self.curve_points / (2*np.pi))
                    ea_point_next = round(ea_next * self.curve_points / (2*np.pi))
                    ea_point_prev = round(ea_prev * self.curve_points / (2*np.pi))
                    if self.dr[vessel] > 0:   # CCW
                        self.curve_data_light[vessel] = np.array([ea_vessel+1, ea_point_next, coord_next[0], coord_next[1], 1])
                        self.curve_data_dark[vessel] = np.array([ea_point_prev, ea_vessel-1, coord_prev[0], coord_prev[1]])
                    else:   # CW
                        self.curve_data_light[vessel] = np.array([ea_point_next, ea_vessel-1, coord_next[0], coord_next[1], 1])
                        self.curve_data_dark[vessel] = np.array([ea_vessel+1, ea_point_prev, coord_prev[0], coord_prev[1]])
                else:   # for hyperbola
                    ea_vessel = 100 - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = 100 - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_prev = 100 - round((ea_prev+np.pi) * self.curve_points / (2*np.pi))
                    if ea < 0:
                        type = 2
                    else:
                        type = 3
                    if self.dr[vessel] < 0:   # CW
                        self.curve_data_light[vessel] = np.array([ea_vessel+1, ea_point_next, coord_next[0], coord_next[1], type])
                        self.curve_data_dark[vessel] = np.array([ea_point_prev, ea_vessel-1, coord_prev[0], coord_prev[1]])
                    else:   # CCW
                        self.curve_data_light[vessel] = np.array([ea_point_next, ea_vessel-1, coord_next[0], coord_next[1], type])
                        self.curve_data_dark[vessel] = np.array([ea_vessel+1, ea_point_prev, coord_prev[0], coord_prev[1]])

            elif not np.isnan(self.coi_leave[vessel, 0]):
                if ecc < 1:   # for ellipse
                    ea_next = self.coi_leave[vessel, 0]
                    ea_prev = self.coi_leave[vessel, 1]
                    coord_next = self.ea2coord(vessel, ea_next)
                    coord_prev = self.ea2coord(vessel, ea_prev)
                    ea_vessel = round(ea * self.curve_points / (2*np.pi))
                    ea_point_next = round(ea_next * self.curve_points / (2*np.pi))
                    ea_point_prev = round(ea_prev * self.curve_points / (2*np.pi))
                    if ea < np.pi:
                        type = 4
                    else:
                        type = 5
                    if self.dr[vessel] > 0:
                        self.curve_data_light[vessel] = np.array([ea_vessel-1, ea_point_next, coord_next[0], coord_next[1], type])
                        self.curve_data_dark[vessel] = np.array([ea_point_prev, max(ea_vessel-1, 0), coord_prev[0], coord_prev[1]])
                    else:
                        self.curve_data_light[vessel] = np.array([ea_point_next, max(ea_vessel-1, 0), coord_next[0], coord_next[1], type])
                        self.curve_data_dark[vessel] = np.array([ea_vessel+1, ea_point_prev, coord_prev[0], coord_prev[1]])
                else:   # for hyperbola
                    ea_next = self.coi_leave[vessel, 1]
                    ea_prev = self.coi_leave[vessel, 0]
                    coord_next = self.ea2coord(vessel, ea_next)
                    coord_prev = self.ea2coord(vessel, ea_prev)
                    ea_vessel = 100 - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = 100 - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_prev = 100 - round((ea_prev+np.pi) * self.curve_points / (2*np.pi))
                    if self.dr[vessel] < 0:   # CW
                        self.curve_data_light[vessel] = np.array([ea_vessel+1, ea_point_next, coord_next[0], coord_next[1], 6])
                        self.curve_data_dark[vessel] = np.array([ea_point_prev, max(ea_vessel-1, 0), coord_prev[0], coord_prev[1]])
                    else:   # CCW
                        self.curve_data_light[vessel] = np.array([ea_point_next, max(ea_vessel-1, 0), coord_next[0], coord_next[1], 5])
                        self.curve_data_dark[vessel] = np.array([ea_vessel+1, ea_point_prev, coord_prev[0], coord_prev[1]])

            elif not np.isnan(self.coi_enter[vessel, 0]):
                ea_vessel = round(ea * self.curve_points / (2*np.pi))
                ea_next = self.coi_enter[vessel, 0]
                ea_point_next = round(ea_next * self.curve_points / (2*np.pi))
                coord_next = self.ea2coord(vessel, ea_next)
                if ecc < 1:   # for ellipse
                    if self.dr[vessel] > 0:
                        self.curve_data_light[vessel] = np.array([ea_vessel+1, ea_point_next, coord_next[0], coord_next[1], 8])
                    else:
                        self.curve_data_light[vessel] = np.array([ea_point_next, ea_vessel-1, coord_next[0], coord_next[1], 8])
                else:   # for hyperbola
                    ea_vessel = 100 - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = 100 - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    if self.dr[vessel] < 0:   # CW
                        self.curve_data_light[vessel] = np.array([ea_vessel+1, ea_point_next, coord_next[0], coord_next[1], 9])
                    else:   # CCW
                        self.curve_data_light[vessel] = np.array([ea_point_next, ea_vessel-1, coord_next[0], coord_next[1], 10])
        return self.curve_data_light, self.curve_data_dark


    def selected(self, vessel):
        """Do physics for selected vessel. This should be done every tick after vessel_move()."""
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
        speed_orb = math.sqrt((2 * a * u - distance * u) / (a * distance))   # velocity vector magnitude from semi-major axis equation
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
