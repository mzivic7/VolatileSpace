import numpy as np
import math
from itertools import repeat

from volatilespace import fileops
from volatilespace import defaults


###### --Constants-- ######
c = 299792458   # speed of light in vacuum
k = 1.381 * 10**-23   # boltzman constant
m_h = 1.674 * 10**-27    # hydrogen atom mass in kg
m_he = 6.646 * 10**-27   # helimum atom mass in kg
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


def mag(vector):
    """Vector magnitude"""
    return math.sqrt(vector.dot(vector))


def orbit_time_to(mean_anomaly, target_angle, period):
    """Time to point on orbit"""
    return period - (mean_anomaly + target_angle)*(period / (2 * np.pi)) % period


def rot_ellipse_by_y(x, a, b, p):
    """Rotatted ellipse by y, but only positive half"""
    y = (math.sqrt(a**2 * b**2 * (a**2 * math.cos(p)**2 + b**2 * math.sin(p)**2 - x**2 * math.sin(p)**4 - x**2 * math.cos(p)**4 - 2 * x**2 * math.sin(p)**2 * math.cos(p)**2)) + a**2 * x * math.sin(p) * math.cos(p) - b**2 * x * math.sin(p) * math.cos(p)) / (a**2 * math.cos(p)**2 + b**2 * math.sin(p)**2)
    return y


def swap_with_first(list_in, n):
    """Swaps first element of list with n element."""
    if list_in.ndim == 1:
        list_in[0], list_in[n] = list_in[n], list_in[0]
    elif list_in.ndim == 2:
        list_in[[0, n]] = list_in[[n, 0]]
    return list_in


def find_parent_one(body_s, bodies_sorted, pos, coi):
    """Finds parent for one body"""
    if body_s:
        body = np.where(bodies_sorted==body_s)[0][0]   # unsorted body index
        parent = 0   # parent is root, until other is found
        for numL in range(len(bodies_sorted[:body])):   # for previously calculated bodies:
            pot_parent = bodies_sorted[numL]   # potential parent index
            rel_pos = pos[body_s] - pos[pot_parent]
            if sum([i*i for i in rel_pos]) < (coi[pot_parent])**2:   # just ultra fast check if point is inside circle - COI
                parent = pot_parent   # this body is parent
                # loop continues until smallest parent body is found
        return parent
    else:
        return 0


def gravity_one(body, parent, mass, pos, gc):
    """Calculates acceleration for one body in simplified n-body problem."""
    if body:   # skip calculation for root
        rel_pos = pos[parent] - pos[body]
        distance = math.dist([0, 0], rel_pos)
        force = gc * mass[body] * mass[parent] / distance**2   # Newton's law of universal gravitation
        # calculate angle between 2 bodies and horizon
        angle = math.atan2(rel_pos[1], rel_pos[0])
        acc = force / mass[body]   # calculate acceleration
        acc_v = np.array([acc * math.cos(angle), acc * math.sin(angle)])   # acceleration vector
        return acc_v
    else:
        return [0, 0]


def kepler_basic_one(body, parent, mass, pos, vel, gc):
    """Basic keplerian orbit for one body."""
    if body:   # skip calculation for root
        rel_pos = pos[body] - pos[parent]
        rel_vel = vel[body] - vel[parent]
        u = gc * mass[parent]   # standard gravitational parameter
        semi_major = -1 * u / (2*(rel_vel.dot(rel_vel) / 2 - u / mag(rel_pos)))
        momentum = np.cross(rel_pos, rel_vel)   # orbital momentum, since this is 2d, momentum is scalar
        # since this is 2d and momentum is scalar, cross product is not needed, so just multiply, swap axes and -y:
        ecc_v = ([rel_vel[1], -rel_vel[0]] * momentum / u) - rel_pos / mag(rel_pos)
        ecc = mag(ecc_v)
        periapsis_arg = ((3 * np.pi / 2) + math.atan2(-ecc_v[0], ecc_v[1])) % (2*np.pi)
        focus = semi_major * ecc
        semi_minor = math.sqrt(abs(focus**2 - semi_major**2))
        coi = semi_major * (mass[body] / mass[parent])**(2/5)
        return focus, ecc_v, semi_major, semi_minor, periapsis_arg, coi
    else:
        return 0, np.zeros(2), 0, 0, 0, 0


def check_collision_one(body1, mass, pos, rad):
    """Check for collisions between one body and other bodies."""
    for body2 in range(len(mass[body1+1:])):   # repeat between this and every other body:
        body2 += body1 + 1
        distance = math.dist((pos[body1, 0], pos[body1, 1]), (pos[body2, 0], pos[body2, 1]))
        if distance <= rad[body1] + rad[body2]:   # if bodies collide
            mass1 = mass[body1]
            mass2 = mass[body2]
            if mass1 <= mass2:   # set smaller object to be deleted
                return body1, body2
            else:
                return body2, body1



class Physics():
    def __init__(self):
        # body
        self.names = np.array([])   # body names
        self.mass = np.array([])  # mass
        self.den = np.array([])  # density
        self.temp = np.array([])  # temperature
        self.color = np.empty((0, 3), int)   # dynamic color
        self.base_color = np.empty((0, 3), int)   # base color (original color unaffected by temperature)
        self.rad = np.array([])  # radius
        self.rad_sc = np.array([])  # Schwarzschild radius
        self.types = np.array([])  # what is this body
        # orbit:
        self.pos = np.empty((0, 2), int)   # position
        self.vel = np.empty((0, 2), int)   # velocity
        self.rel_vel = np.empty((0, 2), int)   # relative velocity
        self.coi = np.array([])   # circle of influence
        self.parents = np.array([], dtype=int)   # parents indices
        self.largest = 0   # most massive body (root)
        self.focus = np.array([])   # focus distance from center of ellipse
        self.semi_major = np.array([])   # ellipse semi major axis
        self.semi_minor = np.array([])   # ellipse semi minor axis
        self.periapsis_arg = np.array([])   # curve periapsis argument
        self.ecc_v = np.empty((0, 2), int)   # curve eccentricity vector
        self.gc = defaults.sim_config["gc"]   # newtonian constant of gravitation
        self.rad_mult = defaults.sim_config["rad_mult"]
        self.reload_settings()
    
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
    
    def load_system(self, conf, names, mass, density, position, velocity, color):
        """Load new system."""
        self.load_conf(conf)
        self.names = names
        self.mass = mass
        self.den = density
        self.temp = np.zeros(len(mass))   # reset values
        self.color = np.zeros((len(color), 3), int)
        self.base_color = color
        volume = self.mass / self.den   # volume from mass and density
        self.rad = self.rad_mult * np.cbrt(3 * volume / (4 * np.pi))   # calculate radius from volume
        self.rad_sc = np.array([])
        self.types = np.array([])
        self.pos = position
        self.vel = velocity
        self.parents = np.array([0, 0, 1], dtype=int)   # parents indices
        self.simplified_orbit_coi()   # calculate COIs
        self.find_parents()   # find parents for all bodies
        self.rel_vel = velocity - velocity[self.parents]
        self.focus = np.zeros(len(mass))
        self.semi_major = np.zeros(len(mass))
        self.semi_minor = np.zeros(len(mass))
        self.periapsis_arg = np.zeros(len(mass))
        self.ecc_v = np.zeros([len(mass), 2])
        self.body()   # re-calculate body related physics
    
    def add_body(self, data):
        """Add body to simulation."""
        old_largest = int(self.largest)
        self.names = np.append(self.names, data["name"])
        self.mass = np.append(self.mass, data["mass"])
        self.den = np.append(self.den, data["density"])
        self.temp = np.append(self.temp, 0)
        self.color = np.vstack((self.color, (0, 0, 0)))
        self.base_color = np.vstack((self.base_color, data["color"]))
        volume = self.mass / self.den   # volume from mass and density
        self.rad = self.rad_mult * np.cbrt(3 * volume / (4 * np.pi))   # calculate radius from volume
        self.pos = np.vstack((self.pos, data["position"]))
        self.vel = np.vstack((self.vel, [0, 0]))   # just add placeholder as [0, 0], since vel is calculated later in gravity()
        self.parents = np.append(self.parents, 0)
        self.simplified_orbit_coi()   # re-calculate COIs
        self.find_parents()   # find parents for all bodies
        self.rel_vel = np.vstack((self.rel_vel, data["velocity"]))   # add new body velocity as relative velocyty
        self.focus = np.append(self.focus, 0)
        self.semi_major = np.append(self.semi_major, 0)
        self.semi_minor = np.append(self.semi_minor, 0)
        self.periapsis_arg = np.append(self.periapsis_arg, 0)
        self.ecc_v = np.vstack((self.ecc_v, [0, 0]))
        # if this body is new root
        if data["mass"] > self.mass[old_largest]:
            self.largest = len(self.mass) - 1
            diff = list(self.pos[self.largest])
            for body in range(len(self.mass)):
                self.pos[body] -= diff
            self.rel_vel[old_largest] = self.rel_vel[self.largest] * -1
            self.vel[self.largest] = [0, 0]
            if self.largest != 0:   # make sure largest body is first
                self.set_root(self.largest)
    
    def del_body(self, delete):
        """Remove body from simulation."""
        if len(self.mass) > 1:   # there must be at lest one body in simulation
            self.names = np.delete(self.names, delete)
            self.mass = np.delete(self.mass, delete)
            self.den = np.delete(self.den, delete)
            self.temp = np.delete(self.temp, delete)
            self.color = np.delete(self.color, delete, axis=0)
            self.base_color = np.delete(self.base_color, delete, axis=0)
            self.rad = np.delete(self.rad, delete)
            self.pos = np.delete(self.pos, delete, axis=0)
            self.vel = np.delete(self.vel, delete, axis=0)
            self.rel_vel = np.delete(self.rel_vel, delete, axis=0)
            self.parents = np.delete(self.parents, delete)
            self.simplified_orbit_coi()   # re-calculate COIs
            self.find_parents()   # find parents for all bodies
            self.focus = np.delete(self.focus, delete)
            self.semi_major = np.delete(self.semi_major, delete)
            self.semi_minor = np.delete(self.semi_minor, delete)
            self.periapsis_arg = np.delete(self.periapsis_arg, delete)
            self.ecc_v = np.delete(self.ecc_v, delete, axis=0)
            if self.largest == delete:
                self.find_parents()   # if root is deleted, we need new one asap
                self.simplified_orbit_coi()   # root is identified by coi=0
                # move new root to (0, 0) and translate all other bodies
                diff = list(self.pos[self.largest])
                for body in range(len(self.mass)):
                    self.pos[body] -= diff
                self.vel[self.largest] = [0, 0]
                if self.largest != 0:   # make sure largest body is first
                    self.set_root(self.largest)
            return 0
        else:
            return 1
        
    def set_root(self, body):
        """Make first body be root by swapping it with current first body. 
        BAD things happen if root is not first"""
        swap_with_first(self.names, body)
        swap_with_first(self.mass, body)
        swap_with_first(self.den, body)
        swap_with_first(self.temp, body)
        swap_with_first(self.color, body)
        swap_with_first(self.base_color, body)
        swap_with_first(self.rad, body)
        swap_with_first(self.pos, body)
        swap_with_first(self.vel, body)
        swap_with_first(self.rel_vel, body)
        swap_with_first(self.parents, body)
        self.simplified_orbit_coi()   # re-calculate COIs
        self.find_parents()   # find parents for all bodies
        self.largest = 0
    
    def move_parent(self, body, position):
        """Moves body with all bodies orbiting it, if any."""
        movement = position - self.pos[body]
        self.pos[body] = position
        children = np.where(self.parents == body)[0]   # find all bodies orbiting this
        for child in children:   # update their position by movement
            self.pos[child] += movement
        
    
    def simplified_orbit_coi(self):
        """Calculate COI for simplified gravity model. Root has COI=0."""
        self.largest = np.argmax(self.mass)   # find root
        self.coi = np.zeros([len(self.mass)])
        bodies_sorted = np.sort(self.mass)[-1::-1]   # reverse sort
        body_indices = np.argsort(self.mass)[-1::-1]   # get sorted indices
        for num, body_mass in enumerate(bodies_sorted[1:]):   # for all sorted bodies except first one
            body = body_indices[num+1]   # get this body index
            # find its parent body:
            parent = self.largest   # parent is root, until other is found
            for numL in range(len(bodies_sorted[:num+1])):   # for previously calculated bodies (skip all smaller than this body):
                pot_parent = body_indices[numL]   # potential parent index
                # if this body is inside potential parents COI:
                if (self.pos[body, 0] - self.pos[pot_parent, 0])**2 + (self.pos[body, 1] - self.pos[pot_parent, 1])**2 < (self.coi[pot_parent])**2:
                    parent = pot_parent   # this body is parent
                    # loop continues until smallest parent body is found
            rel_pos = self.pos[parent] - self.pos[body]   # relative position
            rel_vel = self.vel[parent] - self.vel[body]   # relative velocity
            u = self.gc * self.mass[parent]   # standard gravitational parameter
            semi_major = -1 * u / (2*(rel_vel.dot(rel_vel) / 2 - u / mag(rel_pos)))   # semi-major axis
            self.coi[body] = semi_major * (body_mass / self.mass[parent])**(2/5)   # calculate its COI and save to index
    
    
    def find_parents(self):
        """For each body find its parent body, except for root."""
        self.parents = np.zeros([len(self.coi)], dtype=int)
        bodies_sorted = np.argsort(self.mass)[-1::-1]   # get indices for for sort bodies by mass
        self.parents = np.array(list(map(find_parent_one, list(range(len(bodies_sorted))), repeat(bodies_sorted), repeat(self.pos), repeat(self.coi))))
    
    
    def gravity(self):
        """Newtonian simplified n-body orbital physics model."""
        parents_old = self.parents   # parent memory from last iteration
        self.find_parents()   # find parents for all bodies
        acc_v = list(map(gravity_one, list(range(len(self.mass))), self.parents, repeat(self.mass), repeat(self.pos), repeat(self.gc)))
        self.rel_vel += acc_v
        
        # when body is leaving/entering COI
        for body in range(len(self.mass)):
            if body != 0:   # skip root
                if self.parents[body] != parents_old[body]:    # if parent for this body changed since last iteration:
                    parent = self.parents[body]
                    if self.mass[parent] > self.mass[parents_old[body]]:   # if body is leaving orbit:
                        self.rel_vel[body] += self.rel_vel[parents_old[body]]   # add velocity of previous parent to body relative velocity
                    if self.mass[parent] < self.mass[parents_old[body]]:   # if body is entering orbit:
                        self.rel_vel[body] -= self.rel_vel[parent]   # subtract velocity of new parent to body relative velocity
        
        bodies_sorted = np.argsort(self.mass)[-1::-1]   # get indices from above sort
        for body in bodies_sorted[1:]:   # for sorted bodies by mass except first one (root)
            self.vel[body] = self.rel_vel[body] + self.vel[self.parents[body]]   # absolute vel from relative and parents absolute
        self.pos += self.vel   # update positions
    
    
    def kepler_basic(self):
        """Basic keplerian orbit (only used in drawing orbit line)."""
        values = list(map(kepler_basic_one, list(range(len(self.mass))), self.parents, repeat(self.mass), repeat(self.pos), repeat(self.vel), repeat(self.gc)))
        self.focus, self.ecc_v, self.semi_major, self.semi_minor, self.periapsis_arg, self.coi = list(map(np.array, zip(*values)))
    
    
    def kepler_advanced(self, selected):
        """Advanced keplerian orbit parameters, only for selected body."""
        parent = self.parents[selected]  # get parent body
        # calculate additional orbit parameters
        rel_pos = self.pos[selected] - self.pos[parent]   # relative position
        rel_vel = self.vel[selected] - self.vel[parent]   # relative velocity
        semi_major = self.semi_major[selected]   # get semi-major axis of selected body
        periapsis_arg = self.periapsis_arg[selected]   # get periapsis argument of selected body
        ecc = mag(self.ecc_v[selected])   # eccentricity
        u = self.gc * self.mass[parent]   # standard gravitational parameter
        distance = mag(rel_pos)   # distance to parent
        speed_orb = mag(rel_vel)   # orbit speed
        true_anomaly = (periapsis_arg - (math.atan2(rel_pos[1], rel_pos[0]) - np.pi)) % (2*np.pi)  # true anomaly from relative position
        moment = np.cross(rel_pos, rel_vel)   # rotation moment
        direction = -1 * int(math.copysign(1, moment))   # if moment is negative, rotation is clockwise (-1)
        if direction == -1:   # if direction is clockwise
            true_anomaly = 2*np.pi - true_anomaly   # invert Ta to be calculated in opposite directio
        speed_vert = (rel_vel[0] * math.cos(true_anomaly) + rel_vel[1] * math.sin(true_anomaly))   # vertical speed
        speed_hor = abs(rel_vel[0] * math.sin(true_anomaly) - rel_vel[1] * math.cos(true_anomaly))   # horizontal speed
        
        if ecc != 0:   # if orbit is not circle
            pe_d = semi_major * (1 - ecc)   # periapsis distance and coordinate:
            periapsis = np.array([pe_d * math.cos(periapsis_arg - np.pi), pe_d * math.sin(periapsis_arg - np.pi)]) + self.pos[parent]
            if ecc < 1:   # if orbit is ellipse
                ecc_anomaly = (2 * np.arctan(math.sqrt((1 - ecc)/(1 + ecc)) * math.tan(true_anomaly / 2))) % (2*np.pi)   # eccentric from true anomaly
                mean_anomaly = (ecc_anomaly - ecc * math.sin(ecc_anomaly)) % (2*np.pi)   # mean anomaly from Keplers equation
                period = (2 * np.pi * math.sqrt(semi_major**3 / u))   # orbital period
                pe_t = orbit_time_to(mean_anomaly, 0, period)  # time to periapsis
                ap_d = semi_major * (1 + ecc)   # apoapsis distance
                apoapsis = np.array([ap_d * math.cos(periapsis_arg), ap_d * math.sin(periapsis_arg)]) + self.pos[parent]   # coordinates
                ap_t = orbit_time_to(mean_anomaly, np.pi, period)  # time to apoapsi
                
            else:   # parabola and hyperbola
                pe_t = 0
                apoapsis = np.array([0, 0])
                ap_d = 0
                ap_t = 0
                mean_anomaly = 0
                period = 0
        else:   # circle
            mean_anomaly = 0
            periapsis = np.array([0, 0])
            pe_d = 0
            pe_t = 0
            apoapsis = np.array([0, 0])
            ap_d = 0
            ap_t = 0
            period = (2 * np.pi * math.sqrt(semi_major**3 / u)) / 10   # orbital period
        omega_deg = periapsis_arg * 180 / np.pi
        ma_deg = mean_anomaly * 180 / np.pi
        ta_deg = true_anomaly * 180 / np.pi
        return ecc, periapsis, pe_d, pe_t, apoapsis, ap_d, ap_t, omega_deg, ma_deg, ta_deg, direction, distance, period, speed_orb, speed_hor, speed_vert
    
    
    def kepler_inverse(self, body, ecc, omega_deg, pe_d, mean_anomaly_deg, true_anomaly_deg, ap_d, direction):
        """Inverse kepler equations."""
        parent = self.parents[body]  # get parent body
        u = self.gc * self.mass[parent]   # standard gravitational parameter
        omega = omega_deg * np.pi / 180   # periapsis argument from deg to rad
        mean_anomaly = mean_anomaly_deg * np.pi / 180
        if ecc == 0:   # to avoid division by zero
            ecc = 0.00001
        if ecc >= 1:   # ### TODO ### for now limited on ecc < 1
            ecc = 0.95
        
        if ap_d:   # if there is value for appapsis distance:
            a = (pe_d + ap_d) / 2   # semi-major axis from periapsis and apoapsis
            ecc = (ap_d / a) - 1   # eccentricity from apoapsis
        else:
            a = - pe_d / (ecc - 1)   # semi-major axis from periapsis
        b = a * math.sqrt(1 - ecc**2)   # semi minor axis
        f = math.sqrt(a**2 - b**2)   # focus distance from center of ellipse
        f_rot = [f * math.cos(omega), f * math.sin(omega)]   # focus rotated by omega
        if true_anomaly_deg:   # if there is value for ta
            ta = true_anomaly_deg * np.pi / 180   # use it
        else:
            ea = newton_root(keplers_eq, keplers_eq_derivative, 0.0, {'Ma': mean_anomaly, 'e': ecc})   # newton root for keplers equation
            ta = 2 * math.atan(math.sqrt((1+ecc) / (1-ecc)) * math.tan(ea/2)) % (2*np.pi)   # true anomaly from eccentric anomaly
        
        k = math.tan(ta)   # line at angle Ta (y = kx + n)
        n = -(k * f)   # line at angle Ta containing focus point
        # Solve system for this line and orbit ellipse to get intercept points:
        d = math.sqrt(a**2 * k**2 + b**2 - n**2)   # discriminant
        if ta < np.pi/2 or ta > 3*np.pi/2:   # there are 2 points, pick one at correct angle Ta
            pr_x = (-a**2 * k * n + a * b * d) / (a**2 * k**2 + b**2) - f   # intersect point coordinates of line and ellipse
            pr_y = direction * (-b**2 * n - a * b * k * d) / (a**2 * k**2 + b**2)   # if direction is clockwise invert y axis
        else:
            pr_x = (-a**2 * k * n - a * b * d) / (a**2 * k**2 + b**2) - f
            pr_y = direction * (-b**2 * n + a * b * k * d) / (a**2 * k**2 + b**2)
        pr = np.array([pr_x * math.cos(omega - np.pi) - pr_y * math.sin(omega - np.pi),
                       pr_x * math.sin(omega - np.pi) + pr_y * math.cos(omega - np.pi)])   # rotate point by argument of Pe
        
        p_x, p_y = pr[0] - f * np.cos(omega), pr[1] - f * np.sin(omega)   # point on ellipse relative to its center
        vr_angle = np.arctan(   # implicit derivative of rotated ellipse
            -(b**2 * p_x * math.cos(omega)**2 + a**2 * p_x * math.sin(omega)**2 +
              b**2 * p_y * math.sin(omega) * math.cos(omega) - a**2 * p_y * math.sin(omega) * math.cos(omega)) /
             (a**2 * p_y * math.cos(omega)**2 + b**2 * p_y * math.sin(omega)**2 +
              b**2 * p_x * math.sin(omega) * math.cos(omega) - a**2 * p_x * math.sin(omega) * math.cos(omega)))
        
        # calculate domain of function and substract some small value (10**-6) so y can be calculated
        x_max = math.sqrt(a**2 * math.cos(2*omega) + a**2 - b**2 * math.cos(2*omega) + b**2)/math.sqrt(2) - 10**-6
        y_max = rot_ellipse_by_y(x_max, a, b, omega)   # calculate y
        x_max1, y_max1 = x_max + f_rot[0], y_max + f_rot[1]   # add rotated focus since it is origin
        x_max2, y_max2 = -x_max + f_rot[0], -y_max + f_rot[1]   # functon domain is symetrical, so there are 2 points
        # same angle is calculated on positive and negative part of ellipse curve, so:
        if ((x_max2 - x_max1) * (pr[1] - y_max1)) - ((y_max2 - y_max1) * (pr[0] - x_max1)) < 0:   # when in positive part of curve:
            vr_angle += np.pi   # add pi to angle, put it in range (-1/2pi, 3/2pi) range
        vr_angle = vr_angle % (2*np.pi)   # put it in (0, 2pi) range
        
        prm = mag(pr)   # relative position vector magnitude
        vrm = -direction * math.sqrt((2 * a * u - prm * u) / (a * prm))   # velocity vector from semi-major axis equation
        
        vr_x = vrm * math.cos(vr_angle)   # eccentricity vector from angle of velocity
        vr_y = vrm * math.sin(vr_angle)
        vr = [vr_x, vr_y]
        abs_pos = self.pos[parent] + pr
        self.move_parent(body, self.pos[parent] + pr)   # move thiss body and all bodies orbiting it
        self.rel_vel[body] = vr   # update relative velocity vector
        # this is copied from simplified_orbit_coi end, to allow changes to take effect smoothly, in this iteration, even if paused
        bodies_sorted = np.argsort(self.mass)[-1::-1]
        for body in bodies_sorted[1:]:
            self.vel[body] = self.rel_vel[body] + self.vel[self.parents[body]]
    
    
    def curve(self):
        """Calculate all conic curves line coordinates."""
        focus_x = self.focus * np.cos(self.periapsis_arg)   # focus coords from focus magnitude and angle
        focus_y = self.focus * np.sin(self.periapsis_arg)
        # 2D rotation matrix # rot[rotation, rotation, body]
        rot = np.array([[np.cos(self.periapsis_arg), - np.sin(self.periapsis_arg)], [np.sin(self.periapsis_arg), np.cos(self.periapsis_arg)]])
        
        # calculate curves points # curve[axis, body, point]
        curves = np.zeros((2, len(self.ecc_v), self.curve_points))
        for num in range(len(self.ecc_v)):
            ecc = np.sqrt(self.ecc_v[num].dot(self.ecc_v[num]))   # eccentricity
            if ecc < 1:   # ellipse
                curves[:, num, :] = np.array([self.semi_major[num] * np.cos(self.ell_t), self.semi_minor[num] * np.sin(self.ell_t)])   # raw ellipses
            else:
                if ecc == 1:   # parabola
                    curves[:, num, :] = np.array([self.semi_major[num] * self.par_t**2, 2 * self.semi_major[num] * self.par_t])   # raw parabolas
                    curves[0, num, :] = curves[0, num, :] - self.semi_major[num, np.newaxis]   # translate parabola by semi_major, since its center is not in 0,0
                if ecc > 1:   # hyperbola
                    curves[:, num, :] = np.array([self.semi_major[num] * 1/np.cos(self.hyp_t), self.semi_minor[num] * np.tan(self.hyp_t)])   # raw hyperbolas
                # parametric equation for circle is same as for ellipse, just semi_major = semi_minor, thus it is not required
        
        curves_rot = np.zeros((2, curves.shape[1], curves.shape[2]))   # empty array for new rotated curve
        for body in range(curves.shape[1]):   # for each body
            curves_rot[:, body, :] = np.dot(rot[:, :, body], curves[:, body, :])   # apply rotation matrix to all curve points
        curves_x = curves_rot[0, :, :] + focus_x[:, np.newaxis] + self.pos[self.parents, 0, np.newaxis]   # translate to align focus and parent
        curves_y = curves_rot[1, :, :] + focus_y[:, np.newaxis] + self.pos[self.parents, 1, np.newaxis]
        return np.stack([curves_x, curves_y])
    
    
    def check_collision(self):
        """Check for collisions between all bodies."""
        value = list(map(check_collision_one, list(range(len(self.mass[:-1]))), repeat(self.mass), repeat(self.pos), repeat(self.rad)))
        body1, body2 = next((item for item in value if item is not None), (None, None))
        return body1, body2
    
    
    def inelastic_collision(self):
        """Inelastic collision - two bodies collide, merging into third, with sum of mass and velocity."""
        body_del, body_add = self.check_collision()   # check for collisions
        if body_del is not None:   # if there is collision:
            mass_r = self.mass[body_del] + self.mass[body_add]   # resulting mass
            mom1 = self.vel[body_add] * self.mass[body_add]   # first body moment vector
            mom2 = self.vel[body_del] * self.mass[body_del]   # second body moment vector
            velr = (mom1 + mom2) / mass_r   # resulting velocity vector
            self.rel_vel[body_add] = velr - self.rel_vel[self.parents[body_add]]   # set resulting velocity to larger body
            self.set_body_mass(body_add, mass_r)   # add mass to larger collided body
            self.del_body(body_del)   # delete smaller collided body
        return body_del   # return information if some body is deleted
    
    
    def destructive_collision(self):
        """Destructive collision - 2 bodies collide, both are deleted."""
        body1, body2 = self.check_collision()   # check for collisions
        if body1 is not False:   # if there is collision:
            self.del_body(body1)   # delete both bodies
            self.del_body(body2)
            return body1, body2
    
    
    def body(self):
        """Body related physics (size, thermal, bh...)"""
        # radius
        volume = self.mass / self.den   # volume from mass and density
        self.rad = self.rad_mult * np.cbrt(3 * volume / (4 * np.pi))   # calculate radius from volume
        
        # thermal
        core_temp = (self.gc * mp * self.mass * mass_sim_mult) / ((3/2) * k * self.rad * rad_sim_mult)   # core temperature
        self.temp = 0 / core_temp   # surface temperature # ### temporarily ###
        
        # black hole
        self.rad_sc = 2 * self.mass * mass_sim_mult * self.gc / c**2   # Schwarzschild radius
    
    
    def body_color(self):
        """Set color depending on temperature."""
        # temperature to 1000 - BASE
        # temperature from 1000 to 3000 - RED
        self.color[:, 0] = np.where(self.temp > 1000, self.base_color[:, 0] + ((255 - self.base_color[:, 0]) * (self.temp - 1000)) / 2000, self.base_color[:, 0])   # transition from base red to full red
        self.color[:, 1] = np.where(self.temp > 1000, self.base_color[:, 1] - ((self.base_color[:, 1]) * (self.temp - 1000)) / 2000, self.base_color[:, 1])   # transition from base green to no green
        self.color[:, 2] = np.where(self.temp > 1000, self.base_color[:, 2] - ((self.base_color[:, 2]) * (self.temp - 1000)) / 2000, self.base_color[:, 2])   # transition from base blue to no blue
        # temperature from 3000 to 6000 - YELLOW
        self.color[:, 1] = np.where(self.temp > 3000, (255 * (self.temp - 3000)) / 3000, self.color[:, 1])   # transition from no green to full green
        # temperature from 6000 to 10000 - WHITE
        self.color[:, 2] = np.where(self.temp > 6000, (255 * (self.temp - 6000)) / 4000, self.color[:, 2])   # transition from no blue to full blue
        # temperature from 10000 to 30000 - BLUE
        self.color[:, 0] = np.where(self.temp > 10000, 255 - ((255 * (self.temp - 10000) / 10000)), self.color[:, 0])   # transition from full red to no red
        self.color[:, 1] = np.where(self.temp > 10000, 255 - ((135 * (self.temp - 10000) / 20000)), self.color[:, 1])   # transition from full green to 120 green
        self.color = np.where(self.color > 255, 255, self.color)   # limit values to be max 255
        self.color = np.where(self.color < 0, 0, self.color)   # limit values to be min 0
        return self.color   # return calculated color
    
    
    def classify(self):
        """Body classification."""
        self.types = np.zeros(len(self.mass))  # it is moon
        self.types = np.where(self.mass > 200, 1, self.types)    # if it has high enough mass: it is solid planet
        self.types = np.where(self.den < 1, 2, self.types)    # if it is not dense enough: it is gas planet
        self.types = np.where(self.mass > 5000, 3, self.types)   # ### temporarily ###
        # self.types = np.where(self.temp > 1000, 3, self.types)    # if temperature is over 1000 degrees: it is a star
        # self.types = np.where(self.rad_sc > self.rad, 4, self.types)   # if schwarzschild radius is greater than radius: it is black hole
    
    
    def precalculate(self, body_data):
        """Calculate body related values without it being added to simulation."""
        # radius
        mass = body_data["mass"]
        density = body_data["density"]
        base_color = body_data["color"]
        
        volume = mass / density
        radius = self.rad_mult * np.cbrt(3 * volume / (4 * np.pi))
        
        # thermal
        core_temp = (self.gc * mp * mass * mass_sim_mult) / ((3/2) * k * radius * rad_sim_mult)   # core temperature
        temp = 0 / core_temp   # surface temperature # ### temporarily ###
        
        # bh
        rad_sc = 2 * mass * mass_sim_mult * self.gc / c**2   # Schwarzschild radius
        
        # classify
        body_type = 0  # it is moon
        if mass > 200:
            body_type = 1   # soid planet
        if density < 1:
            body_type = 2   # gas planet
        if mass > 5000:   # ### temporarily ###
            body_type = 3   # star
        # if temp > 1000:
        #     body_type = 3   # star
        # if rad_sc > rad:
        #     body_type = 4   # bh
        
        # star color
        color = list(base_color)
        if temp > 1000:
            color[:, 0] = base_color[:, 0] + ((255 - base_color[:, 0]) * (temp - 1000)) / 2000   # transition from base red to full red
            color[:, 1] = base_color[:, 1] - ((base_color[:, 1]) * (temp - 1000)) / 2000   # transition from base green to no green
            color[:, 2] = base_color[:, 2] - ((base_color[:, 2]) * (temp - 1000)) / 2000   # transition from base blue to no blue
        if temp > 3000:
            color[:, 1] = (255 * (temp - 3000)) / 3000   # transition from no green to full green
        if temp > 6000:
            color[:, 2] = (255 * (temp - 6000)) / 4000   # transition from no blue to full blue
        if temp > 10000:
            color[:, 0] = 255 - ((255 * (temp - 10000) / 10000))   # transition from full red to no red
            color[:, 1] = 255 - ((135 * (temp - 10000) / 20000))   # transition from full green to 120 green
        for num, value in enumerate(color):   # limit color from 0 to 255
            if value < 0:
                color[num] = 0
            if value > 255:
                color[num] = 255
        
        precalculated_data = {"radius": radius, "type": body_type, "temp": temp, "real_color": color, "rad_sc": rad_sc}
        return precalculated_data
    
    
    def precalc_curve(self, pos, vel):
        """Calculate body orbit values without it being added to simulation."""
        
        # same as in find_parents, but only for one body
        mass_sorted = np.sort(self.mass)[-1::-1]
        bodies_sorted = np.argsort(self.mass)[-1::-1]
        parent = self.largest
        for num, body_mass in enumerate(mass_sorted):
            pot_parent = bodies_sorted[num]
            if (pos[0] - self.pos[pot_parent, 0])**2 + (pos[1] - self.pos[pot_parent, 1])**2 < (self.coi[pot_parent])**2:
                parent = pot_parent
        
        rel_pos = pos - self.pos[parent]
        rel_vel = np.array(vel)
        u = self.gc * self.mass[parent]   # standard gravitational parameter
        semi_major = -1 * u / (2*(rel_vel.dot(rel_vel) / 2 - u / mag(rel_pos)))   # semi-major axis
        momentum = np.cross(rel_pos, rel_vel)   # orbital momentum, since this is 2d, momentum is scalar
        ecc_v = ([rel_vel[1], -rel_vel[0]] * momentum / u) - rel_pos / mag(rel_pos)   # eccentricity vector
        ecc = mag(ecc_v)   # eccentricity
        periapsis_arg = ((3 * np.pi / 2) + math.atan2(-ecc_v[0], ecc_v[1])) % (2*np.pi)   # argument of periapsis
        focus = semi_major * ecc   # focus
        semi_minor = math.sqrt(abs(focus**2 - semi_major**2))   # semi-minor axis
        
        focus_x = focus * np.cos(periapsis_arg)
        focus_y = focus * np.sin(periapsis_arg)
        rot = np.array([[np.cos(periapsis_arg), - np.sin(periapsis_arg)],
                        [np.sin(periapsis_arg), np.cos(periapsis_arg)]])
        
        # curve[axis, point]
        curve = np.zeros((2, self.curve_points))
        ecc = np.sqrt(ecc_v.dot(ecc_v))
        if ecc < 1:
            curve[:, :] = np.array([semi_major * np.cos(self.ell_t), semi_minor * np.sin(self.ell_t)])   # raw ellipse
        else:
            if ecc == 1:
                curve[:, :] = np.array([semi_major * self.par_t**2, 2 * semi_major * self.par_t])   # raw parabola
                curve[0, :] = curve[0, :] - semi_major[np.newaxis]
            if ecc > 1:
                curve[:, :] = np.array([semi_major * 1/np.cos(self.hyp_t), semi_minor * np.tan(self.hyp_t)])   # raw hyperbola
        
        curve_rot = np.zeros((2, curve.shape[1]))   # empty array for new rotated curve
        curve_rot[:, :] = np.dot(rot[:, :], curve[:, :])   # apply rotation matrix to all curve points
        curve_x = curve_rot[0, :] + focus_x + self.pos[parent, 0]   # translate to align focus and parent
        curve_y = curve_rot[1, :] + focus_y + self.pos[parent, 1]
        return np.stack([curve_x, curve_y])
    
    
    def get_bodies(self):
        """Get bodies information."""
        return self.names, self.types, self.mass, self.den, self.temp, self.pos, self.vel, self.color, self.rad, self.rad_sc
    
    def get_base_color(self):
        """Get base color (original color unaffected by temperature)."""
        return self.base_color
      
    def get_body_orbits(self):
        """Get keplerian body orbit information."""
        return self.semi_major, self.semi_minor, self.coi, self.parents
    
    
    def set_body_name(self, body, name):
        """Change body name."""
        self.names[body] = name
    
    def set_body_mass(self, body, mass):
        """Change body mass and change root if necessary."""
        self.mass[body] = mass
        old_largest = int(self.largest)
        self.find_parents()   # if root has changed, we need new one asap
        self.simplified_orbit_coi()   # root is identified by coi=0
        if self.largest != old_largest:
            diff = list(self.pos[self.largest])
            for body in range(len(self.mass)):
                self.pos[body] -= diff
            self.rel_vel[old_largest] = self.rel_vel[self.largest] * -1
            self.vel[self.largest] = [0, 0]
            if self.largest != 0:   # make sure largest body is first
                self.set_root(self.largest)
    
    def set_body_den(self, body, density):
        """Change body density."""
        if density < 0.05:
            density = 0.05
        self.den[body] = density
        self.simplified_orbit_coi()
    
    def set_body_pos(self, body, position):
        """Change body position."""
        self.pos[body] = position
        self.simplified_orbit_coi()
    
    def set_body_vel(self, body, velocity):
        """Change body velocity."""
        self.rel_vel[body] = velocity - self.vel[self.parents[body]]  # update body relative velocity
        self.simplified_orbit_coi()
    
    def set_body_color(self, body, color):   # set body base color
        """Change body base color (original color unaffected by temperature)."""
        self.base_color[body] = color
