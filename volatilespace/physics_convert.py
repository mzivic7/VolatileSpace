import math
import numpy as np


def dot_2d(v1, v2):
    """Fastest 2D dot product. It is slightly faster than built in: v1 @ v2."""
    return v1[0]*v2[0] + v1[1]*v2[1]


def mag(vector):
    """Vector magnitude"""
    return math.sqrt(dot_2d(vector, vector))


def cross_2d(v1, v2):
    """Faster than numpy's"""
    return np.array([v1[0]*v2[1] - v1[1]*v2[0]])


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


def rot_ellipse_by_y(x, a, b, p):
    """Rotatted ellipse by y, but only positive half"""
    y = (math.sqrt(a**2 * b**2 * (a**2 * math.cos(p)**2 + b**2 * math.sin(p)**2 - x**2 * math.sin(p)**4 - x**2 * math.cos(p)**4 - 2 * x**2 * math.sin(p)**2 * math.cos(p)**2)) + a**2 * x * math.sin(p) * math.cos(p) - b**2 * x * math.sin(p) * math.cos(p)) / (a**2 * math.cos(p)**2 + b**2 * math.sin(p)**2)
    return y


def to_kepler(mass, orb_data, gc, coi_coef):
    """Converts form newtonian (position, velocity) values to keplerian orbit parameters"""
    pos = orb_data["pos"]
    vel = orb_data["vel"]

    coi = np.zeros([len(mass)])
    ref_l = np.zeros([len(mass)], dtype=int)
    semi_major_l = np.zeros([len(mass)])
    ecc_l = np.zeros([len(mass)])
    pe_arg_l = np.zeros([len(mass)])
    ma_l = np.zeros([len(mass)])
    direction_l = np.zeros([len(mass)])

    # calculate coi and find parents
    bodies_sorted = np.argsort(mass)[-1::-1]   # get indices for sort bodies by mass
    for body_s in range(len(mass)):
        body = np.where(bodies_sorted == body_s)[0][0]   # sorted body index
        ref = 0   # parent is root, until other is found
        for num_l in range(len(bodies_sorted[:body])):   # for previously calculated bodies:
            pot_parent = bodies_sorted[num_l]
            rel_pos = pos[body_s] - pos[pot_parent]
            if rel_pos[0]*rel_pos[0] + rel_pos[1]*rel_pos[1] < coi[pot_parent]*coi[pot_parent]:   # ultra fast check if point is inside circle - COI
                ref = pot_parent
                # loop continues until smallest parent body is found
        ref_l[body_s] = ref
        rel_pos = pos[ref] - pos[body]
        rel_vel = vel[ref] - vel[body]
        u = gc * mass[ref]   # standard gravitational parameter
        semi_major = -1 * u / (2*(dot_2d(rel_vel, rel_vel) / 2 - u / mag(rel_pos)))   # semi-major axis
        if semi_major > 0:   # if eccentricity is larger than 1, semi major will be negative
            coi[body] = semi_major * (mass[body] / mass[ref])**coi_coef   # calculate its COI and save to index
        else:
            coi[body] = 0   # if orbit is hyperbola or parabola, body has no COI, otherwise it would be infinite

    # calculate all other stuff
    for body in range(len(mass)):
        if body:   # skip root
            ref = ref_l[body]
            rel_pos = pos[body] - pos[ref]
            rel_vel = vel[body] - vel[ref]
            u = gc * mass[ref]
            semi_major = -1 * u / (2*(dot_2d(rel_vel, rel_vel) / 2 - u / mag(rel_pos)))
            momentum = cross_2d(rel_pos, rel_vel)
            # since this is 2d and momentum is scalar, cross product is not needed, so just multiply, swap axes and  negate y:
            rel_vel[0], rel_vel[1] = rel_vel[1], -rel_vel[0]
            ecc_v = (rel_vel * momentum / u) - rel_pos / mag(rel_pos)
            ecc = mag(ecc_v)
            pe_arg = ((3 * np.pi / 2) + math.atan2(-ecc_v[0], ecc_v[1])) % (2*np.pi)
            direction = int(math.copysign(1, momentum[0]))   # if moment is negative, rotation is clockwise (-1)

            ta = (pe_arg - (math.atan2(rel_pos[1], rel_pos[0]) - np.pi)) % (2*np.pi)
            if direction == -1:   # clockwise
                ta = 2*np.pi - ta   # invert Ta to be calculated in opposite direction
            if ecc < 1:
                ea = math.acos((ecc + math.cos(ta))/(1 + (ecc * math.cos(ta))))   # eccentric from true anomaly
                if np.pi < ta < 2*np.pi:
                    ea = 2*np.pi - ea   # quadrant problems
                ma = (ea - ecc * math.sin(ea)) % (2*np.pi)   # mean anomaly from Keplers equation
            else:
                ea = math.acosh((ecc + math.cos(ta))/(1 + (ecc * math.cos(ta))))
                ma = ecc * math.sinh(ea) - ea

            semi_major_l[body] = semi_major
            ecc_l[body] = ecc
            pe_arg_l[body] = pe_arg
            ma_l[body] = ma
            direction_l[body] = direction

    return {"kepler": True, "a": semi_major_l, "ecc": ecc_l, "pe_arg": pe_arg_l, "ma": ma_l, "ref": ref_l, "dir": direction_l}


def to_newton(mass, orb_data, gc, coi_coef):
    """Converts form keplerian orbit parameters values to newtonian (position, velocity) """
    semi_major_l = orb_data["a"]
    ecc_l = orb_data["ecc"]
    pe_arg_l = orb_data["pe_arg"]
    ma_l = orb_data["ma"]
    ref_l = orb_data["ref"]
    direction_l = orb_data["dir"]

    coi = np.zeros([len(mass)])
    pos = np.zeros((len(mass), 2), float)
    vel = np.zeros((len(mass), 2), float)

    # find coi sizes so bodies can be calculated in that order
    for body, _ in enumerate(mass):
        a = semi_major_l[body]
        ref = ref_l[body]
        coi[body] = a * (mass[body] / mass[ref])**(coi_coef)

    # calculate positions from largest coi to smallest
    # because parent position is needed to calculate correct position
    bodies_sorted = np.argsort(coi)[-1::-1]
    for body_s in bodies_sorted:
        body = np.where(bodies_sorted == body_s)[0][0]   # sorted body index
        if body:
            a = semi_major_l[body]
            ecc = ecc_l[body]
            pe_arg = pe_arg_l[body]
            ma = ma_l[body]
            dr = direction_l[body]
            ref = ref_l[body]
            u = gc * mass[ref]

            if dr > 0:
                ma = -ma

            if ecc == 0:   # to avoid division by zero
                ecc = 0.00001
            if ecc >= 1:   # limit to only ellipses
                ecc = 0.95

            b = a * math.sqrt(1 - ecc**2)
            f = math.sqrt(a**2 - b**2)
            f_rot = [f * math.cos(pe_arg), f * math.sin(pe_arg)]   # focus rotated by pe_arg
            ea = newton_root(keplers_eq, keplers_eq_derivative, 0.0, {'Ma': ma, 'e': ecc})

            # calculate position vector
            pr_x = a * math.cos(ea) - f
            pr_y = b * math.sin(ea)
            pr = np.array([pr_x * math.cos(pe_arg - np.pi) - pr_y * math.sin(pe_arg - np.pi),
                           pr_x * math.sin(pe_arg - np.pi) + pr_y * math.cos(pe_arg - np.pi)])   # rotate point by argument of Pe

            p_x, p_y = pr[0] - f * np.cos(pe_arg), pr[1] - f * np.sin(pe_arg)   # point on ellipse relative to its center
            # implicit derivative of rotated ellipse
            vr_angle = np.arctan(
                -(b**2 * p_x * math.cos(pe_arg)**2 + a**2 * p_x * math.sin(pe_arg)**2 +
                  b**2 * p_y * math.sin(pe_arg) * math.cos(pe_arg) - a**2 * p_y * math.sin(pe_arg) * math.cos(pe_arg)) /
                 (a**2 * p_y * math.cos(pe_arg)**2 + b**2 * p_y * math.sin(pe_arg)**2 +
                  b**2 * p_x * math.sin(pe_arg) * math.cos(pe_arg) - a**2 * p_x * math.sin(pe_arg) * math.cos(pe_arg)))

            # calcualte angle of velocity vector
            # calculate domain of function and subtract some small value (10**-6) so y can be calculated
            x_max = math.sqrt(a**2 * math.cos(2*pe_arg) + a**2 - b**2 * math.cos(2*pe_arg) + b**2)/math.sqrt(2) - 10**-6
            y_max = rot_ellipse_by_y(x_max, a, b, pe_arg)
            x_max1, y_max1 = x_max + f_rot[0], y_max + f_rot[1]   # add rotated focus since it is origin
            x_max2, y_max2 = -x_max + f_rot[0], -y_max + f_rot[1]   # function domain is symmetrical, so there are 2 points
            # same angle is calculated on positive and negative part of ellipse curve, so:
            if ((x_max2 - x_max1) * (pr[1] - y_max1)) - ((y_max2 - y_max1) * (pr[0] - x_max1)) < 0:   # when in positive part of curve:
                vr_angle += np.pi   # add pi to angle, put it in range (-1/2pi, 3/2pi) range
            vr_angle = vr_angle % (2*np.pi)   # put it in (0, 2pi) range

            prm = mag(pr)
            vrm = dr * math.sqrt((2 * a * u - prm * u) / (a * prm))   # velocity vector magnitude from semi-major axis equation

            vr_x = vrm * math.cos(vr_angle)
            vr_y = vrm * math.sin(vr_angle)
            vr = np.array([vr_x, vr_y])

            pos[body] = pos[ref] + pr
            vel[body] = vel[ref] + vr

    return {"kepler": False, "pos": pos, "vel": vel}
