from ast import literal_eval as leval
import math
from itertools import repeat
import numpy as np
try:   # to allow building without numba
    from numba import njit, types, int32, int64, float64
    numba_avail = True
except ImportError:
    numba_avail = False
    
from volatilespace import fileops
from volatilespace import defaults


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


def calc_orb_one(vessel, ref, body_mass, gc, a, ecc):
    """Additional vessel orbital parameters."""
    if vessel:   # skip root
        u = gc * body_mass[ref]   # standard gravitational parameter
        f = a * ecc
        b = math.sqrt(abs(f**2 - a**2))
        
        if ecc != 0:   # if orbit is not circle
            pe_d = a * (1 - ecc)
            if ecc < 1:   # if orbit is ellipse
                period = 2 * np.pi * math.sqrt(a**3 / u)
                ap_d = a * (1 + ecc)
            else:
                if ecc > 1:   # hyperbola
                    pe_d = a * (1 - ecc)
                else:   # parabola
                    pe_d = a
                period = 0   # period is undefined
                # there is no apoapsis
                ap_d = 0
        else:   # circle
            period = (2 * np.pi * math.sqrt(a**3 / u)) / 10
            pe_d = a * (1 - ecc)
            # there is no apoapsis
            ap_d = 0
        n = 2*np.pi / period
        return b, f, pe_d, ap_d, period, n, u
    else:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


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
        self.curves_rot = np.array([])
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
        # parameters
        self.ell_t = np.linspace(-np.pi, np.pi, self.curve_points)   # ellipse parameter
        self.par_t = np.linspace(- np.pi - 1, np.pi + 1, self.curve_points)   # parabola parameter
    
    
    def load_conf(self, conf):
        """Loads physics related config."""
        self.gc = conf["gc"]
        self.rad_mult = conf["rad_mult"]
        self.coi_coef = conf["coi_coef"]
    
    
    def load(self, conf, vessel_data, vessel_orb_data):
        """Load vessels."""
        self.load_conf(conf)
        self.names = vessel_data["name"]
        # vessel orbit
        self.a = vessel_orb_data["a"]
        self.ecc = vessel_orb_data["ecc"]
        self.pea = vessel_orb_data["pe_arg"]
        self.ma = vessel_orb_data["ma"]
        self.ref = vessel_orb_data["ref"]
        self.dr = vessel_orb_data["dir"]
        self.main()
        self.pos = np.zeros([len(self.names), 2])   # position will be updated later
        self.ea = np.zeros(len(self.names))
    
    
    def main(self):
        """Do all vessel related physics. This should be done only if something changed on vessel or it's orbit."""
        
        # VESSEL DATA #
        vessel_data = {"name": self.names
                       }
        
        # ORBIT DATA #
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
        
        return vessel_data, vessel_orb
    
    
    def curve(self):
        """Calculate all RELATIVE conic curves line points coordinates. This should be done only if something changed on vessel or it's orbit."""
        
        # calculate curves points # curve[axis, vessel, point]
        curves = np.zeros((2, len(self.names), self.curve_points))
        for num in range(len(self.names)):
            ecc = self.ecc[num]
            if ecc < 1:   # ellipse
                curves[:, num, :] = np.array([self.a[num] * np.cos(self.ell_t), self.b[num] * np.sin(self.ell_t)])   # raw ellipses
            else:
                if ecc == 1:   # parabola
                    curves[:, num, :] = np.array([self.a[num] * self.par_t**2, 2 * self.a[num] * self.par_t])   # raw parabolas
                    curves[0, num, :] = curves[0, num, :] - self.a[num, np.newaxis]   # translate parabola by semi_major, since its center is not in 0,0
                elif ecc > 1:   # hyperbola
                    curves[:, num, :] = np.array([-self.a[num] * np.cosh(self.ell_t), self.a[num] * np.sinh(self.ell_t)])   # raw hyperbolas
                # parametric equation for circle is same as for ellipse, just semi_major = semi_minor, thus it is not required
        
        # 2D rotation matrix # rot[rotation, rotation, vessel]
        rot = np.array([[np.cos(self.pea), - np.sin(self.pea)], [np.sin(self.pea), np.cos(self.pea)]])
        self.curves_rot = np.zeros((2, curves.shape[1], curves.shape[2]))
        for vessel in range(curves.shape[1]):
            self.curves_rot[:, vessel, :] = np.dot(rot[:, :, vessel], curves[:, vessel, :])   # apply rotation matrix to all curve points
    
    
    def move(self, warp):
        """Move vessel with mean motion."""
        self.ma += self.dr * self.n * warp
        self.ma = np.where(self.ma > 2*np.pi, self.ma - 2*np.pi, self.ma)
        self.ma = np.where(self.ma < 0, self.ma + 2*np.pi, self.ma)
        bodies_sorted = np.argsort(self.coi)[-1::-1]
        for vessel in bodies_sorted:
            ea = newton_root(keplers_eq, keplers_eq_derivative, 0.0, {'Ma': self.ma[vessel], 'e': self.ecc[vessel]})
            pea = self.pea[vessel]
            ecc = self.ecc[vessel]
            a = self.a[vessel]
            b = self.b[vessel]
            if ecc < 1:
                pr_x = a * math.cos(ea) - self.f[vessel]
                pr_y = b * math.sin(ea)
            elif ecc > 1:
                pass
            elif ecc == 1:
                pass
            pr = np.array([pr_x * math.cos(pea - np.pi) - pr_y * math.sin(pea - np.pi),
                           pr_x * math.sin(pea - np.pi) + pr_y * math.cos(pea - np.pi)])
            self.pos[vessel] = self.pos[self.ref[vessel]] + pr
            self.ea[vessel] = ea
        
        return self.pos, self.ma
    
    
    def selected(self, vessel):
        """Do physics for selected vessel. This should be done every tick after vessel_move()."""
        if vessel:
            pos_ref = self.pos[self.ref[vessel]]
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
            ta = math.acos((math.cos(ea) - ecc)/(1 - ecc * math. cos(ea)))  # true anomaly from eccentric anomaly
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
        """Move all orbit curves to parent position. This should be done every tick after vessel_move()."""
        focus_x = self.f * np.cos(self.pea)   # focus coords from focus magnitude and angle
        focus_y = self.f * np.sin(self.pea)
        curves_x = self.curves_rot[0, :, :] + focus_x[:, np.newaxis] + self.pos[self.ref, 0, np.newaxis]   # translate to align focus and parent
        curves_y = self.curves_rot[1, :, :] + focus_y[:, np.newaxis] + self.pos[self.ref, 1, np.newaxis]
        curves = np.stack([curves_x, curves_y])
        return curves
