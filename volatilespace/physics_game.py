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
        pass
    
    
    def reload_settings(self):
        self.curve_points = int(fileops.load_settings("graphics", "curve_points"))   # number of points from which curve is drawn
        # parameters
        self.ell_t = np.linspace(-np.pi, np.pi, self.curve_points)   # ellipse parameter
        self.par_t = np.linspace(- np.pi - 1, np.pi + 1, self.curve_points)   # parabola parameter
        hyp_t_1 = np.linspace(- np.pi, - np.pi/2 - 0.1, int(self.curve_points/2))   # (-pi, -pi/2]
        hyp_t_2 = np.linspace(np.pi/2 + 0.1, np.pi, int(self.curve_points/2))   # [pi/2, pi)
        self.hyp_t = np.concatenate([hyp_t_2, hyp_t_1])   # hyperbola parameter [pi/2, pi) U (-pi, -pi/2]
    
    
    def load_conf(self, conf):
        """Loads physics related config."""
        self.gc = conf["gc"]
        self.rad_mult = conf["rad_mult"]
        self.coi_coef = conf["coi_coef"]
    
    
    def load_system(self, conf, names, mass, density, color, orb_data):
        """Load new system."""
        self.load_conf(conf)
    
    
    def body(self):
        """Do all body related physics, this should be done only if something changed on body or it's orbit."""
        pass
    
    
    def body_move(self):
        """Move body with mean motion"""
        pass
    
