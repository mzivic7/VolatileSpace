import math
import numpy as np
from volatilespace.physics.phys_shared import \
    rot_hyperbola_by_y, rot_ellipse_by_y, \
    impl_derivative_rot_ell, impl_derivative_rot_hyp, \
    newton_root_kepler_ell, newton_root_kepler_hyp, \
    mag, dot_2d, cross_2d, compare_coord, orb2xy


def kepler_to_velocity(rel_pos, a, ecc, pe_arg, u, dr):
    """Converts from keplerian parameters to relative velocity vector, given that relative position vector is known.
    True anomaly can be inverted for ellipse and hyperbola separately, if needed."""
    if ecc < 1:   # ellipse
        b = a * math.sqrt(1 - ecc**2)
        f = math.sqrt(a**2 - b**2)
        f_rot = [f * math.cos(pe_arg), f * math.sin(pe_arg)]    # focus rotated by pe_arg
        # calculate position vector
        p_x, p_y = rel_pos[0] - f * np.cos(pe_arg), rel_pos[1] - f * np.sin(pe_arg)   # point on ellipse relative to its center
        # implicit derivative of rotated ellipse
        rel_vel_angle = impl_derivative_rot_ell(p_x, p_y, a, b, pe_arg)
        # calcualte angle of velocity vector
        # calculate domain of function and subtract some small value (10**-6) so y can be calculated
        x_max = math.sqrt(a**2 * math.cos(2*pe_arg) + a**2 - b**2 * math.cos(2*pe_arg) + b**2)/math.sqrt(2) - 10**-6
        y_max = rot_ellipse_by_y(x_max, a, b, pe_arg)
        x_max1, y_max1 = x_max + f_rot[0], y_max + f_rot[1]   # add rotated focus since it is origin
        x_max2, y_max2 = -x_max + f_rot[0], -y_max + f_rot[1]   # function domain is symmetrical, so there are 2 points
        # same angle is calculated on positive and negative part of ellipse curve, so:
        if ((x_max2 - x_max1) * (rel_pos[1] - y_max1)) - ((y_max2 - y_max1) * (rel_pos[0] - x_max1)) < 0:   # when in positive part of curve:
            rel_vel_angle += np.pi   # add pi to angle, put it in range (-1/2pi, 3/2pi) range
    else:   # hyperbola
        # note: a is negative
        f = a * ecc
        f_rot = [f * math.cos(pe_arg), f * math.sin(pe_arg)]
        b = math.sqrt(f**2 - a**2)
        p_x, p_y = rel_pos[0] - f * np.cosh(pe_arg), rel_pos[1] - f * np.sinh(pe_arg)
        rel_vel_angle = impl_derivative_rot_hyp(p_x, p_y, a, b, pe_arg)
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
    rel_vel_angle = rel_vel_angle % (2*np.pi)   # put it in (0, 2pi) range
    distance = mag(rel_pos)
    rel_speed = dr * math.sqrt(u * ((2 / distance) - (1 / a)))   # velocity magnitude from vis-viva eq
    rel_vel_x = rel_speed * math.cos(rel_vel_angle)
    rel_vel_y = rel_speed * math.sin(rel_vel_angle)
    return np.array([rel_vel_x, rel_vel_y])


def velocity_to_kepler(rel_pos, rel_vel, u, failsafe=0):
    """Converts from relative velocity vector to keplerian parameters, given that relative position vector is known.
    failsafe=1 option will check if new position is same as before, because newton root may fail
    failsafe=2 will apply failsafe=1 and will check if body velocity is pointing towrards reference.
    This is happening because of orbital model simplification, when entering COI."""
    a = -1 * u / (2*(dot_2d(rel_vel, rel_vel) / 2 - u / mag(rel_pos)))   # mag(x)^2 = x dot x
    momentum = cross_2d(rel_pos, rel_vel)    # orbital momentum, since this is 2d, momentum is scalar
    rel_vel[0], rel_vel[1] = rel_vel[1], -rel_vel[0]
    ecc_v = (rel_vel * momentum / u) - rel_pos / mag(rel_pos)
    ecc = mag(ecc_v)
    pe_arg = ((3 * np.pi / 2) + math.atan2(-ecc_v[0], ecc_v[1])) % (2*np.pi)
    dr = int(math.copysign(1, momentum[0]))   # if momentum is negative, rotation is clockwise (-1)
    ta = (pe_arg - (math.atan2(rel_pos[1], rel_pos[0]) - np.pi)) % (2*np.pi)
    if dr > 0:
        ta = 2*np.pi - ta   # invert Ta to be calculated in opposite direction !? WHY ?!

    if ecc < 1:
        ea = math.acos((ecc + math.cos(ta))/(1 + (ecc * math.cos(ta))))
        if np.pi < ta < 2*np.pi:   # quadrant problems
            ea = 2*np.pi - ea
        ma = (ea - ecc * math.sin(ea)) % (2*np.pi)
        # firsf failsafe if position is wrong due to wrong ma calculation in newton root
        if failsafe:
            new_ea = newton_root_kepler_ell(ecc, ma, ma)
            f = a * ecc
            b = math.sqrt(abs(f**2 - a**2))
            new_pos = orb2xy(a, b, f, ecc, pe_arg, [0, 0], new_ea)
            if compare_coord(rel_pos, new_pos) > 1:
                ea = 2*np.pi - ea
                ma = (ea - ecc * math.sin(ea)) % (2*np.pi)

    else:
        ea = math.acosh((ecc + math.cos(ta))/(1 + (ecc * math.cos(ta))))
        ma = ecc * math.sinh(ea) - ea
        if failsafe:
            new_ea = newton_root_kepler_hyp(ecc, ma, ma)
            f = a * ecc
            b = math.sqrt(abs(f**2 - a**2))
            new_pos = orb2xy(a, b, f, ecc, pe_arg, [0, 0], new_ea)
            if compare_coord(rel_pos, new_pos) > 1:
                ea = -ea
                ma = -ma

    # second failsafe for when entering-coi direction is outwards coi
    if failsafe == 2:
        rel_vel[0], rel_vel[1] = -rel_vel[1], rel_vel[0]   # undoing rel_vel change used for ecc_v
        velocity_angle = math.atan2(rel_vel[1], rel_vel[0]) % (2*np.pi)
        position_angle = math.atan2(rel_pos[1], rel_pos[0]) % (2*np.pi)
        if math.sin(3*np.pi/2 + velocity_angle - position_angle) < 0:
            if ecc < 1:
                ea = 2*np.pi - ea
                ma = (ea - ecc * math.sin(ea)) % (2*np.pi)
            else:
                ea = -ea
                ma = -ma
            pe_arg = (pe_arg + np.pi) % (2*np.pi)
            new_pos = orb2xy(a, b, f, ecc, pe_arg, [0, 0], ea)
            new_position_angle = math.atan2(new_pos[1], new_pos[0]) % (2*math.pi)
            correction_angle = new_position_angle - position_angle
            pe_arg = pe_arg - correction_angle
    return a, ecc, pe_arg, ma, dr


def to_newton(mass, orb_data, gc, coi_coef):
    """Converts form keplerian orbit parameters to newtonian (position, velocity)."""
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
            if ecc == 1:   # to avoid parabola
                ecc = 1.00001

            b = a * math.sqrt(1 - ecc**2)
            f = math.sqrt(a**2 - b**2)
            if ecc < 1:
                ea = newton_root_kepler_ell(ecc, ma, 0.0)
                rel_pos_x = a * math.cos(ea) - f
                rel_pos_y = b * math.sin(ea)
            else:
                ea = newton_root_kepler_hyp(ecc, ma, 0.0)
                rel_pos_x = a * math.cosh(ea) - f
                rel_pos_y = b * math.sinh(ea)
            rel_pos = np.array([rel_pos_x * math.cos(pe_arg - np.pi) - rel_pos_y * math.sin(pe_arg - np.pi),
                                rel_pos_x * math.sin(pe_arg - np.pi) + rel_pos_y * math.cos(pe_arg - np.pi)])
            rel_vel = kepler_to_velocity(rel_pos, a, ecc, pe_arg, u, dr)

            pos[body] = pos[ref] + rel_pos
            vel[body] = vel[ref] + rel_vel

    return {"kepler": False, "pos": pos, "vel": vel}


def to_kepler(mass, orb_data, gc, coi_coef):
    """Converts form newtonian (position, velocity) orbit parameters to keplerian"""
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
        if semi_major > 0:
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
            # since this is 2d and momentum is scalar, cross product is not needed, so just multiply, swap axes and negate y:
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
