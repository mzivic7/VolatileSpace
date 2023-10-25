import numpy as np
import math
from itertools import repeat
from ast import literal_eval as leval
try:   # to allow building without numba
    from numba import njit, types, int32, int64, float64
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
mass_sim_mult = 10**24  # mass simulation multiplier, since real values are needed in core temperature equation
rad_sim_mult = 10**6   # radius sim multiplier


###### --Functions-- ######
def newton_root(function, derivative, root_guess, vars={}):
    """Newton root solver"""
    root = root_guess   # take guessed root input
    for num in range(50):
        delta_x = function(root, vars) / derivative(root, vars)   # guess correction
        root -= delta_x   # better guess
        if abs(delta_x) < 1e-10:   # if correction is small enough:
            return root   # return root
    return root   # if it is not returned above (it has too high deviation) return it anyway


def keplers_eq(E, vars):
    """Keplers equation"""
    return E - vars['e'] * np.sin(E) - vars['Ma']


def keplers_eq_derivative(E, vars):
    """Derivative of keplers equation"""
    return 1.0 - vars['e'] * np.cos(E)


def get_angle(a, b, c):
    """Angle between 3 points in 2D or 3D"""
    ba = a - b   # get 2 vectors from 3 points
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))   # angle brtween 2 vectors
    return np.arccos(cosine_angle)


def orbit_time_to(mean_anomaly, target_angle, period):
    """Time to point on orbit"""
    return period - (mean_anomaly + target_angle)*(period / (2 * np.pi)) % period


def dot_2d(v1, v2):
    """Fastest 2D dot product. It is slightly faster than built in: v1 @ v2."""
    return v1[0]*v2[0] + v1[1]*v2[1]


def mag(vector):
    """Vector magnitude"""
    return math.sqrt(dot_2d(vector, vector))


def cross_2d(v1, v2):
    """Faster than numpy's"""
    return np.array([v1[0]*v2[1] - v1[1]*v2[0]])


def calc_body_orb_one(body, ref, mass, gc, coi_coef, a, ecc, pea):
    """Additional body orbital parameters."""
    if body:   # skip calculation for root
        u = gc * mass[ref]   # standard gravitational parameter
        f = a * ecc
        b = math.sqrt(abs(f**2 - a**2))
        if a > 0:   # if eccentricity is larger than 1, semi major will be negative
            coi = a * (mass[body] / mass[ref])**(coi_coef)
        else:
            coi = 0
        
        if ecc != 0:   # if orbit is not circle
            pe_d = a * (1 - ecc)   # periapsis distance and coordinate:
            if ecc < 1:   # if orbit is ellipse
                period = (2 * np.pi * math.sqrt(a**3 / u))   # orbital period
                ap_d = a * (1 + ecc)   # apoapsis distance
            else:
                if ecc > 1:   # hyperbola
                    pe_d = a * (1 - ecc)
                else:   # parabola
                    pe_d = a
                period = 0   # period is undefined
                # there is no apoapsis
                ap_d = 0
        else:   # circle
            period = (2 * np.pi * math.sqrt(a**3 / u)) / 10   # orbital period
            pe_d = a * (1 - ecc)   # periapsis distance and coordinate:
            # there is no apoapsis
            ap_d = 0
        n = 2*np.pi / period
        # pe = np.array([pe_d * math.cos(pea - np.pi), pe_d * math.sin(pea - np.pi)]) + pos[ref]
        # if ecc != 0 and ecc < 1:
        #     ap = np.array([ap_d * math.cos(pea), ap_d * math.sin(pea)]) + pos[ref]
        # else:
        #     ap = np.array([0, 0])
        return b, f, coi, pe_d, ap_d, period, n, u
    else:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


def body_color(temp, base_color):
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
    color = np.clip(color, 0, 255)   # limit values to be 0 - 255
    return color


# if numba is enabled, compile functions ahead of time
use_numba = leval(fileops.load_settings("game", "numba"))
if numba_avail and use_numba:
    enable_fastmath = leval(fileops.load_settings("game", "fastmath"))
    jitkw = {"cache": True, "fastmath": enable_fastmath}   # numba JIT setings
    dot_2d = njit(float64(float64[:], float64[:]), **jitkw)(dot_2d)
    mag = njit(float64(float64[:]), **jitkw)(mag)
    cross_2d = njit(float64[:](float64[:], float64[:]), **jitkw)(cross_2d)



class Physics():
    def __init__(self):
        # body internal
        self.names = np.array([])
        self.mass = np.array([])
        self.den = np.array([])
        self.base_color = np.empty((0, 3), int)   # base color (original color unaffected by temperature)
        self.types = np.array([])  # what is this body
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
        self.ped_d = np.array([])
        self.ap_d = np.array([])
        self.period = np.array([])
        self.n = np.array([])
        self.coi = np.array([])
        self.curves_rot = np.array([])
        self.pos = np.array([])
        self.ea = np.array([])
        self.u = np.array([])
        self.reload_settings()
    
    
    def reload_settings(self):
        self.curve_points = int(fileops.load_settings("graphics", "curve_points"))   # number of points from which curve is drawn
        # parameters
        self.ell_t = np.linspace(-np.pi, np.pi, self.curve_points)   # ellipse parameter
        self.par_t = np.linspace(- np.pi - 1, np.pi + 1, self.curve_points)   # parabola parameter
    
    
    def load_conf(self, conf):
        """Loads physics related config."""
        self.gc = conf["gc"]
        self.rad_mult = conf["rad_mult"]
        self.coi_coef = conf["coi_coef"]
    
    
    def load_system(self, conf, names, mass, density, color, orb_data):
        """Load new system."""
        self.load_conf(conf)
        self.names = names
        self.mass = mass
        self.den = density
        self.base_color = color
        # body orbit
        self.a = orb_data["a"]
        self.ecc = orb_data["ecc"]
        self.pea = orb_data["pe_arg"]
        self.ma = orb_data["ma"]
        self.ref = orb_data["ref"]
        self.dr = orb_data["dir"]
        self.body()
        self.pos = np.zeros([len(mass), 2])   # position will be updated later
        self.ea = np.zeros(len(mass))
    
    
    def body(self):
        """Do all body related physics. This should be done only if something changed on body or it's orbit."""
        
        # BODY DATA #
        volume = self.mass / self.den   # volume from mass and density
        size = self.rad_mult * np.cbrt(3 * volume / (4 * np.pi))   # calculate radius from volume
        core_temp = (self.gc * mp * self.mass * mass_sim_mult) / ((3/2) * k * size * rad_sim_mult)   # core temperature
        temp = 0 / core_temp   # surface temperature # ### temporarily ###
        rad_sc = 2 * self.mass * mass_sim_mult * self.gc / c**2   # Schwarzschild radius
        color = body_color(temp, self.base_color)
        body_data = {"name": self.names,
                     "type": self.types,
                     "mass": self.mass,
                     "den": self.den,
                     "temp": temp,
                     "color_b": self.base_color,
                     "color": color,
                     "size": size,
                     "rad_sc": rad_sc}
        
        
        # ORBIT DATA #
        values = list(map(calc_body_orb_one, list(range(len(self.mass))), self.ref, repeat(self.mass), repeat(self.gc), repeat(self.coi_coef), self.a, self.ecc, self.pea))
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
        
        return body_data, body_orb
    
    
    def body_curve(self):
        """Calculate all RELATIVE conic curves line points coordinates. This should be done only if something changed on body or it's orbit."""
        
        # calculate curves points # curve[axis, body, point]
        curves = np.zeros((2, len(self.mass), self.curve_points))
        for num in range(len(self.mass)):
            ecc = self.ecc[num]
            if ecc < 1:   # ellipse
                curves[:, num, :] = np.array([self.a[num] * np.cos(self.ell_t), self.b[num] * np.sin(self.ell_t)])   # raw ellipses
            else:
                if ecc == 1:   # parabola
                    curves[:, num, :] = np.array([self.a[num] * self.par_t**2, 2 * self.a[num] * self.par_t])   # raw parabolas
                    curves[0, num, :] = curves[0, num, :] - self.a[num, np.newaxis]   # translate parabola by semi_major, since its center is not in 0,0
                elif ecc > 1:   # hyperbola
                    curves[:, num, :] = np.array([-self.semi_major[num] * np.cosh(self.ell_t), self.semi_minor[num] * np.sinh(self.ell_t)])   # raw hyperbolas
                # parametric equation for circle is same as for ellipse, just semi_major = semi_minor, thus it is not required
        
        # 2D rotation matrix # rot[rotation, rotation, body]
        rot = np.array([[np.cos(self.pea), - np.sin(self.pea)], [np.sin(self.pea), np.cos(self.pea)]])
        self.curves_rot = np.zeros((2, curves.shape[1], curves.shape[2]))   # empty array for new rotated curve
        for body in range(curves.shape[1]):   # for each body
            self.curves_rot[:, body, :] = np.dot(rot[:, :, body], curves[:, body, :])   # apply rotation matrix to all curve points
    
    
    def body_move(self):
        """Move body with mean motion."""
        self.ma += self.n
        bodies_sorted = np.argsort(self.coi)[-1::-1]
        for body in bodies_sorted[1:]:
            ea = newton_root(keplers_eq, keplers_eq_derivative, 0.0, {'Ma': self.ma[body], 'e': self.ecc[body]})
            pea = self.pea[body]
            ecc = self.ecc[body]
            a = self.a[body]
            b = self.b[body]
            if ecc < 1:
                pr_x = a * math.cos(ea) - self.f[body]
                pr_y = b * math.sin(ea)
            elif ecc > 1:
                pass
            elif ecc == 1:
                pass
            pr = np.array([pr_x * math.cos(pea - np.pi) - pr_y * math.sin(pea - np.pi),
                           pr_x * math.sin(pea - np.pi) + pr_y * math.cos(pea - np.pi)])
            self.pos[body] = self.pos[self.ref[body]] + pr
            self.ea[body] = ea
        
        return self.pos
    
    
    def body_selected(self, body):
        """Do physics for selected body. This should be done every tick after body_move()."""
        ref = self.ref[body]  # get parent body
        periapsis_arg = self.pea[body]
        a = self.a[body]
        ecc = self.ecc[body]
        ea = self.ea[body]
        ma = self.ma[body]
        period = self.period[body]
        u = self.u[body]
        ap_d = self.ap_d[body]
        pe_d = self.pe_d[body]
        
        rel_pos = self.pos[body] - self.pos[ref]
        distance = mag(rel_pos)   # distance to parent
        speed_orb = self.dr * math.sqrt((2 * a * u - distance * u) / (a * distance))   # velocity vector magnitude from semi-major axis equation
        ta = (periapsis_arg - (math.atan2(rel_pos[1], rel_pos[0]) - np.pi)) % (2*np.pi)  # true anomaly from relative position
        angle = 2*np.pi - ta + periapsis_arg
        speed_vert = 0
        speed_hor = 0
        
        if ecc != 0:   # if orbit is not circle
            if ecc < 1:   # if orbit is ellipse
                if np.pi < ta < 2*np.pi:
                    ea = 2*np.pi - ea   # quadrant problems
                pe_t = orbit_time_to(ma, 0, period)   # time to periapsis
                ap = np.array([ap_d * math.cos(periapsis_arg), ap_d * math.sin(periapsis_arg)]) + self.pos[ref]   # coordinates
                ap_t = orbit_time_to(ma, np.pi, period)   # time to apoapsis
            else:
                if ecc > 1:   # hyperbola
                    pe_t = math.sqrt((-a)**3 / u) * ma
                else:   # parabola
                    pe_t = math.sqrt(2(a/2)**3) * ma
                period = 0   # period is undefined
                # there is no apoapsis
                ap = np.array([0, 0])
                ap_t = 0
        else:   # circle
            ma = ta
            period = (2 * np.pi * math.sqrt(a**3 / u)) / 10   # orbital periodp
            pe_t = orbit_time_to(ma, 0, period)   # time to periapsis
            # there is no apoapsis
            ap = np.array([0, 0])
            ap_t = 0
        pe = np.array([pe_d * math.cos(periapsis_arg - np.pi), pe_d * math.sin(periapsis_arg - np.pi)]) + self.pos[ref]
        
        return pe, pe_t, ap, ap_t, distance, speed_orb, speed_hor, speed_vert
    
    
    def body_curve_move(self):
        """Move all orbit curves to parent position. This should be done every tick after body_move()."""
        focus_x = self.f * np.cos(self.pea)   # focus coords from focus magnitude and angle
        focus_y = self.f * np.sin(self.pea)
        curves_x = self.curves_rot[0, :, :] + focus_x[:, np.newaxis] + self.pos[self.ref, 0, np.newaxis]   # translate to align focus and parent
        curves_y = self.curves_rot[1, :, :] + focus_y[:, np.newaxis] + self.pos[self.ref, 1, np.newaxis]
        curves = np.stack([curves_x, curves_y])
        return curves
