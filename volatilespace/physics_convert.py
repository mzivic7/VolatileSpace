import numpy as np
import math


def dot_2d(v1, v2):
    """Fastest 2D dot product. It is slightly faster than built in: v1 @ v2."""
    return v1[0]*v2[0] + v1[1]*v2[1]


def mag(vector):
    """Vector magnitude"""
    return math.sqrt(dot_2d(vector, vector))


def cross_2d(v1, v2):
    """Faster than numpy's"""
    return np.array([v1[0]*v2[1] - v1[1]*v2[0]])


def to_kepler(mass, orb_data, gc, coi_coef):
    """Converts form newtonian (position, velocity) values to keplerian orbit parameters"""
    pos = orb_data["pos"]
    vel = orb_data["vel"]
    
    coi = np.zeros([len(mass)])
    parents = np.zeros([len(mass)], dtype=int)
    semi_major_l = np.zeros([len(mass)])
    ecc_l = np.zeros([len(mass)])
    pe_arg_l = np.zeros([len(mass)])
    ma_l = np.zeros([len(mass)])
    direction_l = np.zeros([len(mass)])
    
    # calculate coi and find parents
    bodies_sorted = np.argsort(mass)[-1::-1]   # get indices for for sort bodies by mass
    for body_s in range(len(mass)):
        body = np.where(bodies_sorted == body_s)[0][0]   # sorted body index
        parent = 0   # parent is root, until other is found
        for numL in range(len(bodies_sorted[:body])):   # for previously calculated bodies:
            pot_parent = bodies_sorted[numL]   # potential parent index
            rel_pos = pos[body_s] - pos[pot_parent]
            if rel_pos[0]*rel_pos[0] + rel_pos[1]*rel_pos[1] < coi[pot_parent]*coi[pot_parent]:   # just ultra fast check if point is inside circle - COI
                parent = pot_parent   # this body is parent
                # loop continues until smallest parent body is found
        parents[body_s] = parent
        rel_pos = pos[parent] - pos[body]   # relative position
        rel_vel = vel[parent] - vel[body]   # relative velocity
        u = gc * mass[parent]   # standard gravitational parameter
        semi_major = -1 * u / (2*(dot_2d(rel_vel, rel_vel) / 2 - u / mag(rel_pos)))   # semi-major axis
        if semi_major > 0:   # if eccentricity is larger than 1, semi major will be negative
            coi[body] = semi_major * (mass[body] / mass[parent])**coi_coef   # calculate its COI and save to index
        else:
            coi[body] = 0   # if orbit is hyperbola or parabola, body has no COI, otherwise it would be infinite
    
    # calculate all other stuff
    for body in range(len(mass)):
        if body:   # skip calculation for root
            parent = parents[body]
            rel_pos = pos[body] - pos[parent]
            rel_vel = vel[body] - vel[parent]
            u = gc * mass[parent]   # standard gravitational parameter
            semi_major = -1 * u / (2*(dot_2d(rel_vel, rel_vel) / 2 - u / mag(rel_pos)))
            momentum = cross_2d(rel_pos, rel_vel)   # orbital momentum, since this is 2d, momentum is scalar
            # since this is 2d and momentum is scalar, cross product is not needed, so just multiply, swap axes and -y:
            rel_vel[0], rel_vel[1] = rel_vel[1], -rel_vel[0]
            ecc_v = (rel_vel * momentum / u) - rel_pos / mag(rel_pos)
            ecc = mag(ecc_v)
            pe_arg = ((3 * np.pi / 2) + math.atan2(-ecc_v[0], ecc_v[1])) % (2*np.pi)
            direction = int(math.copysign(1, momentum[0]))   # if moment is negative, rotation is clockwise (-1)
            
            ta = (pe_arg - (math.atan2(rel_pos[1], rel_pos[0]) - np.pi)) % (2*np.pi)
            if direction == -1:   # if direction is clockwise
                ta = 2*np.pi - ta   # invert Ta to be calculated in opposite direction
            if ecc < 1:
                ea = math.acos((ecc + math.cos(ta))/(1 + (ecc * math.cos(ta))))   # eccentric from true anomaly
                if np.pi < ta < 2*np.pi:
                    ea = 2*np.pi - ea   # quadrant problems
                ma = (ea - ecc * math.sin(ea)) % (2*np.pi)   # mean anomaly from Keplers equation
            else:
                ea = math.acosh((ecc + math.cos(ta))/(1 + (ecc * math.cos(ta))))   # eccentric from true anomaly
                ma = ecc * math.sinh(ea) - ea
            
            semi_major_l[body] = semi_major
            ecc_l[body] = ecc
            pe_arg_l[body] = pe_arg
            ma_l[body] = ma
            direction_l[body] = direction
            
        else:
            semi_major_l[body] = 0
            ecc_l[body] = 0
            pe_arg_l[body] = 0
            ma_l[body] = 0
            direction_l[body] = 1
    
    return {"kepler": True, "a": semi_major_l, "ecc": ecc_l, "pe_arg": pe_arg_l, "ma": ma_l, "ref": parents, "dir": direction_l}


def to_newton(mass, orb_data, gc, coi_coef):
    """Converts form keplerian orbit parameters values to newtonian (position, velocity) """
    return orb_data
