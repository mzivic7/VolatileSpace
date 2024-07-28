import math
import cmath
try:
    from numba import njit, float64, complex128
    from numba.types import UniTuple
    numba_avail = True
except ImportError:
    numba_avail = False


def solve_cubic_one(a, b, c):
    """Calculates only one real root for depressed cubic equation.
    z^3 + az^2 + bz + c = 0
    Uses modified Cardano's method from 'Numerical Recipes' and Viète’s trigonometric method to avoid large error in ceratin cases.
    https://quarticequations.com/Cubic.pdf"""

    q = b/3 - a**2/9
    r = (b*a-3*c)/6 - a**3/27
    rq = r**2 + q**3
    if rq > 0:
        # Numerical Recipes algorithm
        aa = (abs(r) + math.sqrt(rq))**(1/3)
        if r >= 0:
            t = aa - q/aa
        else:
            t = q/aa - aa
        z1 = t - a/3
    else:
        # Viete algorithm
        if q == 0:
            theta = 0
        elif q < 0:
            theta = math.acos(r/(-q)**(3/2))
        fi = theta/3
        z1 = 2 * math.sqrt(-q) * math.cos(fi) - a/3
    return z1


def solve_quartic(a, b, c, d, e):
    """Solves quartic equation with modified Ferrari's method.
    az^4 + bz^3 + cz^2 + dz + e = 0
    https://quarticequations.com/Quartic2.pdf"""

    # convert to depressed form
    a3, a2, a1, a0 = b/a, c/a, d/a, e/a

    cc = a3/4
    b2 = a2 - 6*cc**2
    b1 = a1 - 2*a2*cc + 8*cc**3
    b0 = a0 - a1*cc + a2*cc**2 - 3*cc**4

    # one real root of Ferrari's resolvent cubic
    y = solve_cubic_one(b2, b2**2/4 - b0, -b1**2/8)
    if y < 0:
        y = 0

    s = y**2 + b2*y + b2**2/4 - b0
    if s > 0:   # compatibility for no-numba mode
        if b1 < 0:
            r = -math.sqrt(s)
        else:
            r = math.sqrt(s)
    else:
        r = float("nan")

    # repeating stuff
    p = cmath.sqrt(y/2) - cc
    p1 = -cmath.sqrt(y/2) - cc
    q = -y/2 - b2/2

    # solutions to depressed quartic equation
    z1 = p + cmath.sqrt(q - r)
    z2 = p - cmath.sqrt(q - r)
    z3 = p1 + cmath.sqrt(q + r)
    z4 = p1 - cmath.sqrt(q + r)
    return (z1, z2, z3, z4)


# if numba is available, compile functions ahead of time
if numba_avail:
    jitkw = {"cache": True}
    solve_cubic_one = njit(float64(float64, float64, float64), **jitkw)(solve_cubic_one)
    solve_quartic = njit(UniTuple(complex128, 4)(float64, float64, float64, float64, float64), **jitkw)(solve_quartic)
