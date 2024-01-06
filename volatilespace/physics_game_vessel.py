from ast import literal_eval as leval
import math
from itertools import repeat
import numpy as np
try:   # to allow building without numba
    from numba import njit, int32, float64, bool_
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
        return np.array(([x, y]))
    else:
        return np.array(([None, None]))


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
            return np.array([np.nan])


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


def sort_intersect_indices(ea_vessel, ea_points, direction):
    if not np.all(np.isnan(ea_points)):
        angle = np.where(np.isnan(ea_points), np.nan, np.absolute(ea_vessel - ea_points))
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


def concat_wrap(array, point_start, range_start, range_end, point_end):
    """Concatenates [point_start, array[range_start, range_end], point_end] such that if range_start > range_end,
    range goes from range_end to array_end + array_start to range_start, and point_1 and point_2 swaps places."""
    # not using np.concatenate because it cannot be easily NJIT-ed with numba, and this is faster
    out = np.empty((array.shape[0], 2))
    out[:] = np.nan
    if range_start <= range_end:
        out[0, :] = point_start
        out[1 : 1+range_end-range_start, :] = array[range_start : range_end, :]
        out[1+range_end-range_start, :] = point_end
    else:
        out[0, :] = point_end
        range_first = array[range_start :, :]
        range_second = array[: range_end, :]
        out[1 : 1+range_first.shape[0], :] = range_first
        out[1+range_first.shape[0] : 1+range_first.shape[0]+range_second.shape[0], :] = range_second
        out[range_first.shape[0]+range_second.shape[0], :] = point_start
    # if there are nans in input array they need to be cleaned from output:
    if np.any(np.isnan(array)):
        out_clean = out[~np.isnan(out[:,0]), :]
        out[:] = np.nan
        out[: out_clean.shape[0], :] = out_clean
    return out


def culling(curve, sim_screen, ref_coi, curve_points, cull):
    sim_screen_size = np.absolute(sim_screen[1] - sim_screen[0])
    x_max = np.amax(curve[:, 0])   # numba does not support axis argument, yet
    y_max = np.amax(curve[:, 1])   # https://github.com/numba/numba/issues/1269
    x_min = np.amin(curve[:, 0])
    y_min = np.amin(curve[:, 1])
    diff = np.array([max(x_max - x_min, 1), max(y_max - y_min, 1)])
    screen_diff = sim_screen_size / diff
    if ref_coi != 0:
        if diff[0] + diff[1] > ref_coi * 3:
            screen_diff = sim_screen_size / np.array([ref_coi * 1.5, ref_coi * 1.5])
    if screen_diff[0] + screen_diff[1] < 130:
        if cull:
            factor = max(int(curve_points / 25), 4)
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


def rot_ellipse_by_y(x, a, b, p):
    """Rotatted ellipse by y, but only positive half"""
    y = (a*b*math.sqrt(-x**2 * (math.cos(p)**4 + math.sin(p)**4) - 2 * x**2 * math.cos(p)**2 * math.sin(p)**2 + b**2 * math.sin(p)**2 + a**2 * math.cos(p)**2) + a**2 * x * math.sin(p) * math.cos(p) - b**2 * x * math.sin(p) * math.cos(p)) / (a**2 * math.cos(p)**2 + b**2 * math.sin(p)**2)
    return y


def rot_hyperbola_by_y(x, a, b, p):
    """Rotatted hyperbola by y, but only positive half"""
    y = -((a*b*math.sqrt(-x**2 * (math.cos(p)**4 + math.sin(p)**4) + 2 * x**2 * math.cos(p)**2 * math.sin(p)**2 + b**2 * math.sin(p)**2 - a**2 * math.cos(p)**2) + a**2 * x * math.sin(p) * math.cos(p) + b**2 * x * math.sin(p) * math.cos(p)) / (-a**2 * math.cos(p)**2 + b**2 * math.sin(p)**2))
    return y


def kepler_to_velocity(rel_pos, a, ecc, pe_arg, u, dr):
    """Converts from kepler parameters to relative velocity vector, given that relative position vectoris known."""
    # same as in physics_convert.py
    if ecc < 1:
        b = a * math.sqrt(1 - ecc**2)
        f = math.sqrt(a**2 - b**2)
        f_rot = [f * math.cos(pe_arg), f * math.sin(pe_arg)]
        p_x, p_y = rel_pos[0] - f * np.cos(pe_arg), rel_pos[1] - f * np.sin(pe_arg)
        rel_vel_angle = np.arctan(
            -(b**2 * p_x * math.cos(pe_arg)**2 + a**2 * p_x * math.sin(pe_arg)**2 +
              b**2 * p_y * math.sin(pe_arg) * math.cos(pe_arg) - a**2 * p_y * math.sin(pe_arg) * math.cos(pe_arg)) /
             (a**2 * p_y * math.cos(pe_arg)**2 + b**2 * p_y * math.sin(pe_arg)**2 +
              b**2 * p_x * math.sin(pe_arg) * math.cos(pe_arg) - a**2 * p_x * math.sin(pe_arg) * math.cos(pe_arg)))
        x_max = math.sqrt(a**2 * math.cos(2*pe_arg) + a**2 - b**2 * math.cos(2*pe_arg) + b**2)/math.sqrt(2) - 10**-6
        y_max = rot_ellipse_by_y(x_max, a, b, pe_arg)
        x_max1, y_max1 = x_max + f_rot[0], y_max + f_rot[1]
        x_max2, y_max2 = -x_max + f_rot[0], -y_max + f_rot[1]
        if ((x_max2 - x_max1) * (rel_pos[1] - y_max1)) - ((y_max2 - y_max1) * (rel_pos[0] - x_max1)) < 0:
            rel_vel_angle += np.pi
    else:
        # note: a is negative
        f = a * ecc
        f_rot = [f * math.cos(pe_arg), f * math.sin(pe_arg)]
        b = math.sqrt(f**2 - a**2)
        p_x, p_y = rel_pos[0] - f * np.cos(pe_arg), rel_pos[1] - f * np.sin(pe_arg)
        rel_vel_angle = np.arctan(
            -(b**2 * p_x * math.cos(pe_arg)**2 - a**2 * p_x * math.sin(pe_arg)**2 +
              b**2 * p_y * math.sin(pe_arg) * math.cos(pe_arg) + a**2 * p_y * math.sin(pe_arg) * math.cos(pe_arg)) /
             (- a**2 * p_y * math.cos(pe_arg)**2 + b**2 * p_y * math.sin(pe_arg)**2 +
              b**2 * p_x * math.sin(pe_arg) * math.cos(pe_arg) + a**2 * p_x * math.sin(pe_arg) * math.cos(pe_arg)))
        try:
            x_max = math.sqrt(a**2 * math.cos(2*pe_arg) + a**2 + b**2 * math.cos(2*pe_arg) - b**2)/math.sqrt(2) - 10**-6
            y_max = rot_hyperbola_by_y(x_max, a, b, pe_arg)
            x_max1, y_max1 = x_max + f_rot[0], y_max + f_rot[1]
            x_max2, y_max2 = -x_max + f_rot[0], -y_max + f_rot[1]
            if ((x_max2 - x_max1) * (rel_pos[1] - y_max1)) - ((y_max2 - y_max1) * (rel_pos[0] - x_max1)) < 0:
                rel_vel_angle += np.pi
        except ValueError:
            if np.pi <= pe_arg < 2*np.pi:
                rel_vel_angle += np.pi
    rel_vel_angle = rel_vel_angle % (2*np.pi)
    distance = mag(rel_pos)
    rel_speed = dr * math.sqrt(u * ((2 / distance) - (1 / a)))
    rel_vel_x = rel_speed * math.cos(rel_vel_angle)
    rel_vel_y = rel_speed * math.sin(rel_vel_angle)
    return np.array([rel_vel_x, rel_vel_y])


def velocity_to_kepler(rel_pos, rel_vel, u):
    a = -1 * u / (2*(dot_2d(rel_vel, rel_vel) / 2 - u / mag(rel_pos)))   # mag(x)^2 = x dot x
    momentum = cross_2d(rel_pos, rel_vel)    # orbital momentum, since this is 2d, momentum is scalar
    rel_vel[0], rel_vel[1] = rel_vel[1], -rel_vel[0]
    ecc_v = (rel_vel * momentum / u) - rel_pos / mag(rel_pos)
    ecc = mag(ecc_v)
    pe_arg = ((3 * np.pi / 2) + math.atan2(-ecc_v[0], ecc_v[1])) % (2*np.pi)
    dr = int(math.copysign(1, momentum[0]))   # if moment is negative, rotation is clockwise (-1)
    ta = (pe_arg - (math.atan2(rel_pos[1], rel_pos[0]) - np.pi)) % (2*np.pi)
    if dr > 0:
        ta = 2*np.pi - ta   # invert Ta to be calculated in opposite direction !? WHY ?!
    if ecc < 1:
        ea = math.acos((ecc + math.cos(ta))/(1 + (ecc * math.cos(ta))))
        if np.pi < ta < 2*np.pi:   # quadrant problems
            ea = 2*np.pi - ea
        ma = (ea - ecc * math.sin(ea)) % (2*np.pi)
    else:
        ea = math.acosh((ecc + math.cos(ta))/(1 + (ecc * math.cos(ta))))
        ma = ecc * math.sinh(ea) - ea
    return a, ecc, pe_arg, ma, dr


# if numba is enabled, compile functions ahead of time
use_numba = leval(fileops.load_settings("game", "numba"))
if numba_avail and use_numba:
    enable_fastmath = leval(fileops.load_settings("game", "fastmath"))
    jitkw = {"cache": True, "fastmath": enable_fastmath}   # numba JIT setings
    dot_2d = njit(float64(float64[:], float64[:]), **jitkw)(dot_2d)
    mag = njit(float64(float64[:]), **jitkw)(mag)
    cross_2d = njit(float64[:](float64[:], float64[:]), **jitkw)(cross_2d)
    concat_wrap = njit((float64[:, :], float64[:], int32, int32, float64[:]), **jitkw)(concat_wrap)
    culling = njit(bool_(float64[:, :], float64[:, :], float64, int32, bool_), **jitkw)(culling)
    # ellipse_circle = njit(float64[:](float64, float64, float64, float64, float64), **jitkw)(ellipse_circle)   # scipy is required



class Physics():
    def __init__(self):
        # vessel internal
        self.names = np.array([])
        self.rot_angle = np.array([])
        self.rot_speed = np.array([])
        self.rot_acc = np.array([])
        self.visible_vessels = []
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
        self.curve_points = int(fileops.load_settings("graphics", "curve_points"))   # number of points from which curve is drawn
        self.curves = np.zeros((len(self.names), self.curve_points, 2))
        self.cull = leval(fileops.load_settings("graphics", "culling"))
        # parameters
        self.ell_t = np.linspace(-np.pi, np.pi, self.curve_points)   # ellipse parameter
        self.par_t = np.linspace(- np.pi - 1, np.pi + 1, self.curve_points)   # parabola parameter
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
        self.body_ecc = body_orb["ecc"]
        self.body_pea = body_orb["pea"]
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
        self.coi_enter = np.zeros((len(self.names), 2)) * np.nan

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


    def culling(self, sim_screen):
        """Returns list of vessels orbits that are visible on screen and are large enough.
        Checking for orbits that are on screen can be toggle in settings"""
        values = list(map(culling, self.curves_mov, repeat(sim_screen), self.body_coi[self.ref], repeat(self.curve_points), repeat(self.cull)))
        self.visible_vessels = np.arange(len(self.names))[values]
        return self.visible_vessels


    def initial(self, warp, body_pos):
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
            self.ea[vessel] = newton_root(keplers_eq, keplers_eq_derivative, self.ea[vessel], {'Ma': self.ma[vessel], 'e': self.ecc[vessel]})
        else:
            self.ea[vessel] = newton_root(keplers_eq_hyp, keplers_eq_hyp_derivative, self.ea[vessel], {'Ma': self.ma[vessel], 'e': self.ecc[vessel]})
        # recalculate points and curves
        self.points(vessel)
        self.curve(vessel)
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
        self.curves[vessel] = np.swapaxes(np.dot(rot, curves), 0, 1)


    def points(self, vessel):
        """Find characteristic points on RELATIVE UNROTATED ellipse for one body.
        This should be done only if something changed on vessel or it's orbit, after move()."""
        ref = self.ref[vessel]
        ecc = self.ecc[vessel]
        dr = self.dr[vessel]
        xc = self.f[vessel]   # body is in focus
        yc = 0

        body_impact_all = orbit_intersect(self.a[vessel], self.b[vessel], ecc, xc, yc, self.body_size[ref])
        self.body_impact[vessel] = next_point(self.ea[vessel], body_impact_all, dr)

        body_enter_atm_all = orbit_intersect(self.a[vessel], self.b[vessel], ecc, xc, yc, self.body_size[ref] + self.body_atm[ref])
        self.body_enter_atm[vessel] = next_point(self.ea[vessel], body_enter_atm_all, dr)

        coi_leave_all = orbit_intersect(self.a[vessel], self.b[vessel], ecc, xc, yc, self.body_coi[ref])
        self.coi_leave[vessel] = next_point(self.a[vessel], coi_leave_all, dr)

        # TODO: enter_coi
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
        This should be done every tick after move()."""
        focus_x = self.f * np.cos(self.pea)
        focus_y = self.f * np.sin(self.pea)
        focus = np.column_stack((focus_x, focus_y))
        self.curves_mov = self.curves + focus[:, np.newaxis, :] + self.body_pos[self.ref, np.newaxis, :]
        return self.curves_mov


    def curve_segments(self):
        """Calculates two segments for each curve on screen.
        Returns arrays of all x and y points for each segment for all curves on screen.
        Dimensions: (curve, points, axis).
        This should be done every tick after curve_move(), and after points(), which must be run at least once"""
        curves_light = np.empty((len(self.names), self.curve_points, 2))   # shape: (vessel, points, axes)
        curves_dark = np.empty((len(self.names), self.curve_points, 2))
        intersect_type = np.zeros(len(self.names))
        first_intersect = np.empty((len(self.names), 2)) * np.nan
        for vessel in self.visible_vessels:
            ea = self.ea[vessel]
            ecc = self.ecc[vessel]
            if ecc < 1:
                ell = True   # is True for ellipse (ecc<1) and False for hyperbola (ecc>1)
            else:
                ell = False
            dr = self.dr[vessel]
            point_vessel = self.pos[vessel]
            curve_light = np.copy(self.curves_mov[vessel])
            curve_dark = np.copy(self.curves_mov[vessel])

            # check where and what is next intesection
            impact = self.body_impact[vessel, int(not ell)]
            coi_enter = self.coi_enter[vessel, int(not ell)]
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
                        curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                    else:   # CW
                        curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, ea_vessel-1, point_vessel)
                else:   # for hyperbola
                    ea_vessel = self.curve_points - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = self.curve_points - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        if ea < 0:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, ea_vessel-1, point_vessel)
                        else:
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_point_next, ea_vessel-1, coord_next)
                    else:   # CW
                        if ea < 0:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_vessel+1, ea_point_next, point_vessel)
                        else:
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                first_intersect[vessel] = coord_next
                intersect_type[vessel] = 1

            if next_intersect[0] == 1:   # COI ENTER
                curves_dark[vessel] = curve_dark
                ea_next = self.coi_enter[vessel, 0]
                coord_next = self.ea2coord(vessel, ea_next)
                if ell:   # for ellipse
                    ea_vessel = round(ea * self.curve_points / (2*np.pi))
                    ea_point_next = round(ea_next * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                    else:   # CW
                        curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, ea_vessel-1, point_vessel)
                else:   # for hyperbola
                    ea_vessel = self.curve_points - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = self.curve_points - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    if dr > 0:   # CCW
                        if ea < 0:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, ea_vessel-1, point_vessel)
                        else:
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_point_next, ea_vessel-1, coord_next)
                    else:   # CW
                        if ea < 0:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_vessel+1, ea_point_next, point_vessel)
                        else:
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                first_intersect[vessel] = coord_next
                intersect_type[vessel] = 3

            if next_intersect[0] == 2:   # JUST COI LEAVE
                if ell:   # for ellipse
                    ea_next = self.coi_leave[vessel, 0]
                    ea_prev = self.coi_leave[vessel, 1]
                    coord_next = self.ea2coord(vessel, ea_next)
                    coord_prev = self.ea2coord(vessel, ea_prev)
                    ea_vessel = round(ea * self.curve_points / (2*np.pi))
                    ea_point_next = round(ea_next * self.curve_points / (2*np.pi))
                    ea_point_prev = round(ea_prev * self.curve_points / (2*np.pi))
                    if dr < 0:   # CW
                        if ea < np.pi:
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_point_next, max(ea_vessel, 0), coord_next)
                        else:
                            if ea_vessel == ea_point_next:
                                ea_vessel += 1
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, max(ea_vessel-1, 0), point_vessel)
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_prev, ea_point_next, ea_point_prev, coord_next)
                    else:   # CCW
                        if ea < np.pi:
                            if ea_vessel == ea_point_next:
                                ea_vessel -= 1
                            curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                        else:
                            curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_vessel, ea_point_next, point_vessel)
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_next, ea_point_prev, ea_point_next, coord_prev)
                else:   # for hyperbola
                    ea_next = self.coi_leave[vessel, 1]
                    ea_prev = self.coi_leave[vessel, 0]
                    coord_next = self.ea2coord(vessel, ea_next)
                    coord_prev = self.ea2coord(vessel, ea_prev)
                    ea_vessel = self.curve_points - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = self.curve_points - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_prev = self.curve_points - round((ea_prev+np.pi) * self.curve_points / (2*np.pi))
                    if dr < 0:   # CW
                        if ea_vessel == ea_point_next:
                            ea_vessel -= 1
                        curves_light[vessel] = concat_wrap(curve_light, point_vessel, ea_vessel+1, ea_point_next, coord_next)
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_prev, ea_point_prev, ea_point_next, coord_next)
                    else:   # CCW
                        if ea_vessel == ea_point_next:
                            ea_vessel += 1
                        curves_light[vessel] = concat_wrap(curve_light, coord_next, ea_point_next, max(ea_vessel-1, 0), point_vessel)
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_next, ea_point_next, ea_point_prev, coord_prev)
                first_intersect[vessel] = coord_next
                intersect_type[vessel] = 2

            elif any(next_intersect == 2):   # COI LEAVE FOR 2 INTERSECTIONS
                if ell:   # for ellipse
                    ea_next = self.coi_leave[vessel, 0]
                    ea_prev = self.coi_leave[vessel, 1]
                    coord_next = self.ea2coord(vessel, ea_next)
                    coord_prev = self.ea2coord(vessel, ea_prev)
                    ea_point_next = round(ea_next * self.curve_points / (2*np.pi))
                    ea_point_prev = round(ea_prev * self.curve_points / (2*np.pi))
                    if dr < 0:   # CW
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_next, ea_point_next, ea_point_prev, coord_prev)
                    else:   # CCW
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_next, ea_point_prev, ea_point_next, coord_prev)
                else:   # for hyperbola
                    ea_next = self.coi_leave[vessel, 1]
                    ea_prev = self.coi_leave[vessel, 0]
                    coord_next = self.ea2coord(vessel, ea_next)
                    coord_prev = self.ea2coord(vessel, ea_prev)
                    ea_vessel = self.curve_points - round((ea+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_next = self.curve_points - round((ea_next+np.pi) * self.curve_points / (2*np.pi))
                    ea_point_prev = self.curve_points - round((ea_prev+np.pi) * self.curve_points / (2*np.pi))
                    if dr < 0:   # CW
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_prev, ea_point_prev, ea_point_next, coord_next)
                    else:   # CCW
                        curves_dark[vessel] = concat_wrap(curve_dark, coord_next, ea_point_next, ea_point_prev, coord_prev)

            if np.isnan(next_intersect[0]):
                curves_light[vessel] = curve_light
                first_intersect[vessel] = np.array([np.nan, np.nan])
        return curves_light, curves_dark, first_intersect, intersect_type


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
        """Returns vessel that will in next iteration meet conditions for switching warp, and that condition.
        This should be done every tick after move(), and after points(), which must be run at least once.
        Conditions (situations):
        0 space -> impact
        1 space -> atmosphere
        2 atmosphere -> space"""

        situation = None
        alarm_vessel = None
        for vessel, _ in enumerate(self.names):
            ecc = self.ecc[vessel]
            dr = self.dr[vessel]

            # find what is next intersection
            ea_vessel_1 = self.ea[vessel]
            impact = self.body_impact[vessel, int(not (ecc < 1))]
            enter_atm = self.body_enter_atm[vessel, int(not (ecc < 1))]
            leave_atm = self.body_enter_atm[vessel, int(ecc < 1)]
            all_intersect = np.array((impact, enter_atm, leave_atm))
            next_intersections = sort_intersect_indices(ea_vessel_1, all_intersect, dr)
            if not np.all(np.isnan(next_intersections)):
                next_intersect = next_intersections[0]
                ea_intersect = all_intersect[next_intersect]

                # calculate vessel ea for next iteration
                if ecc < 1:
                    next_ma = self.ma[vessel] + self.n[vessel] * warp * dr
                    ea_vessel_2 = newton_root(keplers_eq, keplers_eq_derivative, ea_vessel_1, {'Ma': next_ma, 'e': ecc})
                else:
                    next_ma = self.ma[vessel] + self.n[vessel] * warp * dr * -1
                    ea_vessel_2 = newton_root(keplers_eq_hyp, keplers_eq_hyp_derivative, ea_vessel_1, {'Ma': next_ma, 'e': ecc})

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
                    if next_intersect in [0,1]:
                        if not vessel in self.physical_hold:
                            self.physical_hold = np.append(self.physical_hold, vessel)
                        situation = next_intersect
                    else:
                        self.physical_hold = self.physical_hold[self.physical_hold != vessel]
                        situation = 2
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
            dr = self.dr[vessel]
            ea_vessel_1 = self.ea[vessel]

            # LEAVE COI #

            leave_coi = self.coi_leave[vessel, int(ecc > 1)]
            if not np.isnan(leave_coi):

                # calculate vessel ea for next iteration
                if ecc < 1:
                    next_ma = self.ma[vessel] + self.n[vessel] * warp * dr
                    ea_vessel_2 = newton_root(keplers_eq, keplers_eq_derivative, ea_vessel_1, {'Ma': next_ma, 'e': ecc})
                else:
                    next_ma = self.ma[vessel] + self.n[vessel] * warp * dr * -1
                    ea_vessel_2 = newton_root(keplers_eq_hyp, keplers_eq_hyp_derivative, ea_vessel_1, {'Ma': next_ma, 'e': ecc})

                # checking if vessel will pass point in next iteration
                angle_1 = abs(ea_vessel_1 - leave_coi)
                angle_2 = abs(ea_vessel_1 - ea_vessel_2)
                if ea_vessel_1 > leave_coi:
                    angle_1 = 2*np.pi - angle_1
                if ea_vessel_1 > ea_vessel_2:
                    angle_2 = 2*np.pi - angle_2
                if dr < 0:   # if clockwsise
                    angle_1, angle_2 = angle_2, angle_1
                if angle_1 < angle_2:
                    ref = self.ref[vessel]
                    new_u = self.gc * self.body_mass[self.body_ref[ref]]
                    # calculate vessel and reference relative positions (to their references)
                    ves_abs_pos = self.ea2coord(vessel, leave_coi)
                    ref_abs_pos = self.body_pos[ref]
                    ves_rel_pos = ves_abs_pos - ref_abs_pos
                    ref_rel_pos = ref_abs_pos - self.body_pos[self.body_ref[ref]]
                    # calculate vessel and reference relative velocities (to their references)
                    ves_rel_vel = kepler_to_velocity(ves_rel_pos, self.a[vessel], ecc, self.pea[vessel], self.u[vessel], dr)
                    ref_rel_vel = kepler_to_velocity(ref_rel_pos, self.body_a[ref], self.body_ecc[ref], self.body_pea[ref], new_u, self.body_dr[ref])
                    # add vessels and its references relative: positions and velocities
                    new_ref_pos = ves_rel_pos + ref_rel_pos
                    new_ref_vel = ves_rel_vel + ref_rel_vel
                    # convert this position and absolute velocity to orbital parameters
                    self.a[vessel], self.ecc[vessel], self.pea[vessel], self.ma[vessel], self.dr[vessel] = velocity_to_kepler(new_ref_pos, new_ref_vel, new_u)
                    # set new reference
                    self.ref[vessel] = self.body_ref[ref]
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
