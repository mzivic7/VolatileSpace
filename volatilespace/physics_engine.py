import numpy as np
import math

from volatilespace import fileops


###### --Constants-- ######
c = 299792458   # speed of light in vacuum
k = 1.381 * 10**-23   # boltzman constant
gc = 1   # newtonian constant of gravitation
m_h = 1.674 * 10**-27    # hydrogen atom mass in kg
m_he = 6.646 * 10**-27   # helimum atom mass in kg
mp = (m_h * 99 + m_he * 1) / 100   # average particle mass   # depends on star age
mass_sim_mult = 10**24  # mass simulation multiplyer, since real values are needed in core temperature equation
rad_sim_mult = 10**6   # radius sim multiplyer
rad_mult = 10   # radius multiplyer to make bodies larger 
curve_points = int(fileops.load_settings("graphics", "curve_points"))   # number of points from which curve is drawn



###### --Parameters-- ######
ell_t = np.linspace(-np.pi, np.pi, curve_points)   # ellipse parameter
par_t = np.linspace(- np.pi - 1, np.pi + 1, curve_points)   # parabola parameter
hyp_t_1 = np.linspace(- np.pi, - np.pi/2 -0.1, int(curve_points/2))   # (-pi, -pi/2]
hyp_t_2 = np.linspace(np.pi/2 + 0.1, np.pi, int(curve_points/2))   # [pi/2, pi)
hyp_t = np.concatenate([hyp_t_2, hyp_t_1])   # hyperbola parameter [pi/2, pi) U (-pi, -pi/2]



###### --Functions-- ######
def newton_root(function, derivative, root_guess, vars = {}):
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
def keplers_eq_derivative(E, vars ):
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
    return period - (mean_anomaly + target_angle)*(period / (2 * np.pi))%period

def rot_ellipse_by_y(x, a, b, p):
    """Rotatted ellipse by y, but only positive half"""
    y = (math.sqrt(a**2 * b**2 * (a**2 * math.cos(p)**2 + b**2 * math.sin(p)**2 - x**2 * math.sin(p)**4 - x**2 * math.cos(p)**4 - 2 * x**2 * math.sin(p)**2 * math.cos(p)**2)) + a**2 * x * math.sin(p) * math.cos(p) - b**2 * x * math.sin(p) * math.cos(p)) / (a**2 * math.cos(p)**2 + b**2 * math.sin(p)**2)
    return y



class Physics():
    def __init__(self):
        # body
        self.mass = np.array([])  # mass
        self.den = np.array([])  # density
        self.temp = np.array([])  # temperature
        self.color = np.empty((0, 3), int)   # dynamic color
        self.base_color = np.empty((0, 3), int)   # base color (original color unaffected by temperature)
        self.rad = np.array([])  # radius
        self.rad_sc = np.array([])  # Schwarzschild radius
        self.type = np.array([])  # what is this body
        # orbit:
        self.pos = np.empty((0, 2), int)   # position
        self.vel = np.empty((0, 2), int)   # velocity
        self.rel_vel = np.empty((0, 2), int)   # relative velocity
        self.coi = np.array([])   # circle of influence
        self.parents = np.array([], dtype=int)   # parents indexes
        self.largest = 0   # most massive body
        self.focus = np.array([])   # focus distance from center of ellipse
        self.semi_major = np.array([])   # ellipse semi major axis
        self.semi_minor = np.array([])   # ellipse semi minor axis
        self.periapsis_arg = np.array([])   # curve periapsis argument
        self.ecc_v = np.empty((0, 2), int)   # curve eccentricity vector
    
    # load new system
    def load_system(self, mass, density, position, velocity, color):
        self.mass = mass
        self.den = density
        self.temp = np.zeros(len(mass))   # reset values
        self.color = np.zeros((len(color), 3), int)
        self.base_color = color
        volume = self.mass / self.den   # volume from mass and density
        self.rad = rad_mult * np.cbrt(3 * volume / (4 * np.pi))   # calculate radius from volume
        self.rad_sc = np.array([])
        self.type = np.array([])
        self.pos = position
        self.vel = velocity
        self.parents = np.array([0,0,1], dtype=int)   # parents indexes
        self.simplified_orbit_coi()   # calculate COIs
        self.find_parents()   # find parents for all bodies
        self.rel_vel = velocity - velocity[self.parents]
        self.focus = np.zeros(len(mass))
        self.semi_major = np.zeros(len(mass))
        self.semi_minor = np.zeros(len(mass))
        self.periapsis_arg = np.zeros(len(mass))
        self.ecc_v = np.zeros([len(mass), 2])
        self.body_size()   # re-calculate body size
        self.black_hole()  # re-calculate black holes
    
    # add body to simulation
    def add_body(self, mass, density, position, velocity, color):
        self.mass = np.append(self.mass, mass)
        self.den = np.append(self.den, density)
        self.temp = np.append(self.temp, 0)
        self.color = np.vstack((self.color, (0, 0, 0)))
        self.base_color = np.vstack((self.base_color, color))
        volume = self.mass / self.den   # volume from mass and density
        self.rad = rad_mult * np.cbrt(3 * volume / (4 * np.pi))   # calculate radius from volume
        self.pos = np.vstack((self.pos, position))
        self.vel = np.vstack((self.vel, [0,0]))   # just add placeholder as [0, 0], since vel is calculated later in gravity()
        self.parents = np.append(self.parents, 0)
        self.simplified_orbit_coi()   # re-calculate COIs
        self.find_parents()   # find parents for all bodies
        self.rel_vel = np.vstack((self.rel_vel, velocity))   # add new body velocity as relative velocyty
        self.focus = np.append(self.focus, 0)
        self.semi_major = np.append(self.semi_major, 0)
        self.semi_minor = np.append(self.semi_minor, 0)
        self.periapsis_arg = np.append(self.periapsis_arg, 0)
        self.ecc_v = np.vstack((self.ecc_v, [0, 0]))
    
    # remove body from simulation
    def del_body(self, delete):
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
    
    
    # calculate COI for simplified gravity model
    def simplified_orbit_coi(self):
        self.largest = np.argmax(self.mass)   # find most massive body
        self.coi = np.zeros([len(self.mass)])   # fill array with zeros
        bodies_sorted = np.sort(self.mass)[-1::-1]   # reverse sort
        body_indexes = np.argsort(self.mass)[-1::-1]   # get sorted indexes
        for num, body_mass in enumerate(bodies_sorted[1:]):   # for all sorted bodies except first one
            body = body_indexes[num+1]   # get this body index
            # find its parent body:
            parent = self.largest   # parent is most massive body, until other is found
            for numL in range(len(bodies_sorted[:num+1])):   # for previously calculated bodies (skip all smaller than this body):
                pot_parent = body_indexes[numL]   # potential parent index
                # if this body is inside potential parents COI:
                if (self.pos[body, 0] -  self.pos[pot_parent, 0])**2 + (self.pos[body, 1] - self.pos[pot_parent, 1])**2 < (self.coi[pot_parent])**2:
                    parent = pot_parent   # this body is parent
                    # loop continues until smallest parent body is found
            rel_pos = self.pos[parent] - self.pos[body]   # relative position
            rel_vel = self.vel[parent] - self.vel[body]   # relative velocity
            u = gc * self.mass[parent]   # standard gravitational parameter
            semi_major = -1 * u / (2*(rel_vel.dot(rel_vel) / 2 - u / mag(rel_pos)))   # semi-major axis
            self.coi[body] = semi_major * (body_mass / self.mass[parent])**(2/5)   # calculate its COI and save to index
    
    
    def find_parents(self):
        self.parents = np.zeros([len(self.coi)], dtype=int)   # fill array with zeros
        mass_sorted = np.sort(self.mass)[-1::-1]   # sort bodies by mass from largest to smallest
        bodies_sorted = np.argsort(self.mass)[-1::-1]   # get indexes from above sort
        for num, body_mass in enumerate(mass_sorted[1:]):   # for all sorted bodies except first one (most massive)
            body = bodies_sorted[num+1]   # get this body index
            # find its parent body:
            parent = self.largest   # parent is most massive body, until other is found
            for numL in range(len(mass_sorted[:num+1])):   # for previously calculated bodies:
                pot_parent = bodies_sorted[numL]   # potential parent index
                # if this body is inside potential parents COI:
                if (self.pos[body, 0] -  self.pos[pot_parent, 0])**2 + (self.pos[body, 1] - self.pos[pot_parent, 1])**2 < (self.coi[pot_parent])**2:
                    parent = pot_parent   # this body is parent
                    # loop continues until smallest parent body is found
            self.parents[body] = parent   # add it to array
    
    
    # Newtonian simplified n-body orbital physics model
    def gravity(self):
        parents_old = self.parents   # parent memory from last iteration
        self.find_parents()   # find parents for all bodies
        for body, mass in enumerate(self.mass):   # for every body:
            if self.coi[body] != 0:   # skip most massive body
                parent = self.parents[body]   # get parent for this body
                distance = math.dist((self.pos[body, 0], self.pos[body, 1]), (self.pos[parent, 0], self.pos[parent, 1]))
                force = gc * mass * self.mass[parent] / distance**2   # Newton's law of universal gravitation
                # calculate angle between 2 bodies and horizon
                angle = math.atan2(self.pos[parent, 1] - self.pos[body, 1], self.pos[parent, 0] - self.pos[body, 0])
                acc = force / mass   # calculate acceleration
                accv = np.array([acc * math.cos(angle), acc * math.sin(angle)])   # acceleration vector
                self.rel_vel[body] += accv   # add acceleration to velocity vector
                if parent != parents_old[body]:    # if parent for this body changed since last iteration:
                    if self.mass[parent] > self.mass[parents_old[body]]:   # if body is leaving orbit:
                        self.rel_vel[body] += self.rel_vel[parents_old[body]]   # add velocity of previous parent to body relative velocity
                    if self.mass[parent] < self.mass[parents_old[body]]:   # if body is entering orbit:
                        self.rel_vel[body] -= self.rel_vel[parent]   # subtract velocity of new parent to body relative velocity
        bodies_sorted = np.argsort(self.mass)[-1::-1]   # get indexes from above sort
        for body in bodies_sorted[1:]:   # for sorted bodies by mass except first one (most massive)
            self.vel[body] = self.rel_vel[body] + self.vel[self.parents[body]]   # absolute vel from relative and parents absolute
        self.pos += self.vel   # update positions
    
    
    # basic Keplerian orbit (only used in drawing orbit line)
    def kepler_basic(self):
        for body in range(len(self.mass)):   # for every body:
            if self.coi[body] != 0:   # skip most massive body
                parent = self.parents[body]   # get parent body
                # calculate basic keplerian orbit physics
                rel_pos = self.pos[body] - self.pos[parent]   # relative position
                rel_vel = self.vel[body] - self.vel[parent]   # relative velocity
                u = gc * self.mass[parent]   # standard gravitational parameter
                semi_major = -1 * u / (2*(rel_vel.dot(rel_vel) / 2 - u / mag(rel_pos)))   # semi-major axis
                momentum = np.cross(rel_pos, rel_vel)   # orbital momentum, since this is 2d, momentum is scalar
                # since this is 2d and momentum is scalar, cross product is not needed, so just multiply, swap axes and -y:
                ecc_v = ([rel_vel[1], -rel_vel[0]] * momentum / u) - rel_pos / mag(rel_pos)   # eccentricity vector
                ecc = mag(ecc_v)   # eccentricity
                self.periapsis_arg[body] = (3 * np.pi / 2) + math.atan2(-ecc_v[0], ecc_v[1])   # argument of periapsis
                focus = semi_major * ecc   # focus
                self.semi_minor[body] = math.sqrt(abs(focus**2 - semi_major**2))   # semi-minor axis
                self.coi[body] = semi_major * (self.mass[body] / self.mass[parent])**(2/5)   # calculate its COI and save to index
                self.focus[body] = focus   # save data to array
                self.semi_major[body] = semi_major
                self.ecc_v[body] = ecc_v
    
    
    # advanced Keplerian orbit parameters, only for selected body
    def kepler_advanced(self, selected):
        parent = self.parents[selected]  # get parent body
        # calculate additional orbit parameters
        rel_pos = self.pos[selected] - self.pos[parent]   # relative position
        rel_vel = self.vel[selected] - self.vel[parent]   # relative velocity
        semi_major = self.semi_major[selected]   # get semi-major axis of selected body
        periapsis_arg = self.periapsis_arg[selected]   # get periapsis argument of selected body
        ecc = mag(self.ecc_v[selected])   # eccentricity
        u = gc * self.mass[parent]   # standard gravitational parameter
        distance = mag(rel_pos)   # distance to parent
        speed_orb = mag(rel_vel)   # orbit speed
        true_anomaly = (periapsis_arg - (math.atan2(rel_pos[1], rel_pos[0])- np.pi))%(2*np.pi)  # true anomaly from relative position
        moment = np.cross(rel_pos, rel_vel)   # rotation moment
        direction = -1 * int(math.copysign(1, moment))   # if moment is negative, rotation is clockwise (-1)
        if direction == -1:   # if direction is clockwise
            true_anomaly = 2*np.pi - true_anomaly   # invert Ta to be calculated in opposite direction
        speed_vert = (rel_vel[0] * math.cos(true_anomaly) + rel_vel[1] * math.sin(true_anomaly))   # vertical speed
        speed_hor = abs(rel_vel[0] * math.sin(true_anomaly) - rel_vel[1] * math.cos(true_anomaly))   # horizontal speed
        
        if ecc != 0:   # if orbit is not circle
            pe_d = semi_major * (1 - ecc)   # periapsis distance and coordinate:
            periapsis = np.array([pe_d * math.cos(periapsis_arg - np.pi), pe_d * math.sin(periapsis_arg - np.pi)]) + self.pos[parent]
            if ecc < 1:   # if orbit is ellipse
                ecc_anomaly = (2 * np.arctan(math.sqrt((1 - ecc)/(1 + ecc)) * math.tan(true_anomaly / 2)))%(2*np.pi)   # eccentric from true anomaly
                mean_anomaly = (ecc_anomaly - ecc * math.sin(ecc_anomaly))%(2*np.pi)   # mean anomaly from Keplers equation
                period = (2 * np.pi * math.sqrt(semi_major**3 / u))   # orbital period
                pe_t = orbit_time_to(mean_anomaly, 0, period)  # time to periapsis
                orb_angle = (abs(true_anomaly - periapsis_arg)) * 180 / np.pi   # angular displacement from argument of periapsis
                ap_d = semi_major * (1 + ecc)   # apoapsis distance
                apoapsis = np.array([ap_d * math.cos(periapsis_arg), ap_d * math.sin(periapsis_arg)]) + self.pos[parent]   # coordinates
                ap_t = orbit_time_to(mean_anomaly, np.pi, period)  # time to apoapsi
                
            else:   # parabola and hyperbola
                pe_t = 0
                apoapsis = np.array([0, 0])
                ap_d = 0
                ap_t = 0
                period = 0
                orb_angle = 0
        else:   # circle
            periapsis = np.array([0, 0])
            pe_d = 0
            pe_t = 0
            apoapsis = np.array([0, 0])
            ap_d = 0
            ap_t = 0
            period = (2 * np.pi * math.sqrt(semi_major**3 / u)) / 10   # orbital period
            orb_angle = 0
        
        return ecc, periapsis, apoapsis, pe_d, ap_d, distance, period, pe_t, ap_t, orb_angle, speed_orb, speed_hor, speed_vert
    
    
    # inverse kepler equations
    def kepler_inverse(self, body, ecc, omega_deg, pe_d, mean_anomaly, ap_d, direction):
        parent = self.parents[body]  # get parent body
        u = gc * self.mass[parent]   # standard gravitational parameter
        omega = omega_deg * np.pi / 180   # periapsis argument from deg to rad
        a = - pe_d / (ecc - 1)   # semi-major axis from periapsis
        if ap_d != "NaN":   # if there is value for appapsis distance:
            ap_d = float(ap_d)   # convert it to float
            ecc = (ap_d / a) - 1   # eccentricity from apoapsis
        b = a * math.sqrt(1 - ecc**2)   # semi minor axis
        f = math.sqrt(a**2 - b**2)   # focus distance from center of ellipse
        f_rot = [f * math.cos(omega), f * math.sin(omega)]   # focus rotated by omega
        
        ea = newton_root( keplers_eq, keplers_eq_derivative, 0.0, {'Ma': mean_anomaly, 'e': ecc})   # newton root for keplers equation
        ta = 2 * math.atan(math.sqrt((1+ecc) / (1-ecc)) * math.tan(ea/2))%(2*np.pi)   # true anomaly from eccentric anomaly
        
        k = math.tan(ta)   # line at angle Ta (y = kx + n)
        n = -(k * f)   # line at angle Ta containing focus point
        # Solve system for this line and orbit ellipse to get intercet points:
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
        vr_angle = vr_angle%(2*np.pi)   # put it in (0, 2pi) range
        
        prm = mag(pr)   # relative position vector magnitude
        vrm = -direction * math.sqrt((2 * a * u - prm * u) / (a * prm))   # velocity vector from semi-major axis equation
        
        vr_x = 50 * vrm * math.cos(vr_angle)   # eccentricity vector from angle of velocity
        vr_y = 50 * vrm * math.sin(vr_angle)
        vr = [vr_x, vr_y]
        self.pos[body] = self.pos[parent] + pr   # update absolute position vector
        self.rel_vel[body] = vr   # update relative velocity vector
    
    
    # calculate all curves line coordinates
    def curve(self):
        focus_x = self.focus * np.cos(self.periapsis_arg)   # focus coords from focus magnitude and angle
        focus_y = self.focus * np.sin(self.periapsis_arg)
        #2D rotation matrix # rot[rotation, rotation, body]
        rot = np.array([[np.cos(self.periapsis_arg) , - np.sin(self.periapsis_arg)], [np.sin(self.periapsis_arg) , np.cos(self.periapsis_arg)]])
        
        # calculate curves points # curve[axis, body, point]
        curves = np.zeros((2, len(self.ecc_v), curve_points))
        for num in range(len(self.ecc_v)):
            ecc = np.sqrt(self.ecc_v[num].dot(self.ecc_v[num]))   # eccentricity
            if ecc < 1:   # ellipse
                curves[:, num, :] = np.array([self.semi_major[num] * np.cos(ell_t), self.semi_minor[num] * np.sin(ell_t)])   # raw ellipses
            else:
                if ecc == 1:   # parabola
                    curves[:, num, :] = np.array([self.semi_major[num] * par_t**2, 2 * self.semi_major[num] * par_t])   # raw parabolas
                    curves[0, num, :] = curves[0, num, :] - self.semi_major[num, np.newaxis]   # translate parabola by semi_major, since its center is not in 0,0
                if ecc > 1:   # hyperbola
                    curves[:, num, :] = np.array([self.semi_major[num] * 1/np.cos(hyp_t), self.semi_minor[num] * np.tan(hyp_t)])   # raw hyperbolas
                # parametric equation for circle is same as for sphere, just semi_major = semi_minor, thus it is not required
        
        curves_rot = np.zeros((2, curves.shape[1], curves.shape[2]))   # empty array for new rotaded curve
        for body in range(curves.shape[1]):   # for each body
            curves_rot[:, body, :] = np.dot(rot[:, :, body], curves[:, body, :])   # apply rotation matrix to all curve points
        curves_x = curves_rot[0, :, :] + focus_x[:, np.newaxis] + self.pos[self.parents, 0, np.newaxis]   # translate to align focus and parent
        curves_y = curves_rot[1, :, :] + focus_y[:, np.newaxis] + self.pos[self.parents, 1, np.newaxis]
        return curves_x, curves_y
    
    
    # check for collisions in simulation
    def check_collision(self):
        for body1, mass1 in enumerate(self.mass):   # for every body:
            for body2, mass2 in enumerate(self.mass[body1+1:], body1+1):   # repeat between this and every other body:
                distance = math.dist((self.pos[body1, 0], self.pos[body1, 1]), (self.pos[body2, 0], self.pos[body2, 1]))
                if distance <= self.rad[body1] + self.rad[body2]:   # if bodies collide
                    if mass1 <= mass2: return body1, body2   # set smaller object to be deleted
                    else: return body2, body1
        return False, False   # return none if there are no collisions
    
    
    # inelastic collision
    def inelastic_collision(self):
        body_del, body_add = self.check_collision()   # check for collisions
        if body_del is not False:   # if there is collision:
            mass_r = self.mass[body_del] + self.mass[body_add]   # resulting mass
            mom1 = self.vel[body_add] * self.mass[body_add]   # first body moment vector
            mom2 = self.vel[body_del] * self.mass[body_del]   # second body moment vector
            velr = (mom1 + mom2) / mass_r   # resulting velocity vector
            self.mass[body_add] = mass_r   # add mass to larger collided body
            self.rel_vel[body_add] = velr - self.rel_vel[self.parents[body_add]]   # set resulting velocity to larger body
            self.del_body(body_del)   # delete smaller collided body
        return body_del   # return information if some body is deleted
    
    
    # destructive collision
    def destructive_collision(self):
        body1, body2 = self.check_collision()   # check for collisions
        if body1 is not False:   # if there is collision:
            self.del_body(body1)   # delete both bodies
            self.del_body(body2)
            return body1, body2
    
    
    # calculate bodies size from mass and density
    def body_size(self):
        volume = self.mass / self.den   # volume from mass and density
        self.rad = rad_mult * np.cbrt(3 * volume / (4 * np.pi))   # calculate radius from volume
        
    
    # termal calculations
    def body_temp(self):
        core_temp = (gc * mp * self.mass * mass_sim_mult) / ((3/2) * k * self.rad * rad_sim_mult)   # core temperature
        self.temp = 0 / core_temp   # surface temperature ### remove when fixed
    
    
    # set color depending on temperature
    def body_color(self):
        # temperature to 1000 - BASE
        # temperature from 1000 to 3000 - RED
        self.color[:,0] = np.where(self.temp > 1000, self.base_color[:,0] + ((255 - self.base_color[:,0]) * (self.temp - 1000)) / 2000, self.base_color[:,0])   # transition from base red to full red
        self.color[:,1] = np.where(self.temp > 1000, self.base_color[:,1] - ((self.base_color[:,1]) * (self.temp - 1000)) / 2000, self.base_color[:,1])   # transition from base green to no green
        self.color[:,2] = np.where(self.temp > 1000, self.base_color[:,2] - ((self.base_color[:,2]) * (self.temp - 1000)) / 2000, self.base_color[:,2])   # transition from base blue to no blue
        # temperature from 3000 to 6000 - YELLOW
        self.color[:,1] = np.where(self.temp > 3000, (255 * (self.temp - 3000)) / 3000, self.color[:,1])   # transition from no green to full green
        # temperature from 6000 to 10000 - WHITE
        self.color[:,2] = np.where(self.temp > 6000, (255 * (self.temp - 6000)) / 4000, self.color[:,2])   # transition from no blue to full blue
        # temperature from 10000 to 30000 - BLUE
        self.color[:,0] = np.where(self.temp > 10000, 255 - ((255 * (self.temp - 10000) /10000)), self.color[:,0])   # transition from full red to no red
        self.color[:,1] = np.where(self.temp > 10000, 255 - ((135 * (self.temp - 10000) / 20000)), self.color[:,1])   # transition from full green to 120 green
        self.color = np.where(self.color > 220, 220, self.color)   # limit values to be max 255
        self.color = np.where(self.color < 0, 0, self.color)   # limit values to be min 0
        return self.color   # return calculated color
    
    
    # define black hole bodies
    def black_hole(self):
        self.rad_sc = 2 * self.mass * mass_sim_mult * gc / c**2   # Schwarzschild radius
    
    
    # body classification:
    def classify(self):
        if self.temp > 1000:   # if temperature is over 1000 degrees:
            self.type = "Star"   # it is a star
        if self.rad_sc >= self.rad:   # if schwarzschild radius is greater than radius:
            self.type = "BH"   # it is black hole
    
    
    # get bodies information
    def get_bodies(self):
        return self.mass, self.den, self.temp, self.pos, self.vel, self.color, self.rad, self.rad_sc
    
    # get base color  (original color unaffected by temperature)
    def get_base_color(self):
        return self.base_color
    
    # get keplerian body orbit information
    def get_body_orbits(self):
        return self.semi_major, self.semi_minor, self.coi, self.parents


    # change body parameters
    def set_body_mass(self, body, mass):
        self.mass[body] = mass
        self.simplified_orbit_coi()   # re-calculate COIs
    
    def set_body_den(self, body, density):
        self.den[body] = density
    
    def set_body_pos(self, body, position):
        self.pos[body] = position
        self.simplified_orbit_coi()   # re-calculate COIs
    
    def set_body_vel(self, body, velocity):
        self.rel_vel[body] = velocity - self.vel[self.parents[body]]  # update body relative velovity
        self.simplified_orbit_coi()   # re-calculate COIs
    
    def set_body_color(self, body, color):   # set body base color
        self.base_color[body] = color

