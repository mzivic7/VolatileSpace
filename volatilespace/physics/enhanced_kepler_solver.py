"""
Enhanced Newton-Rhapson Kepler Equation (ENRKE) solver algorithm from:
D. Tommasini, D. N. Olivieri, Two fast and accurate routines for solving the elliptic Kepler equation for all values of the eccentricity and mean anomaly. Astronomy &amp; Astrophysics. 658 (2022), doi:10.1051/0004-6361/202141423
https://www.aanda.org/articles/aa/full_html/2022/02/aa41423-21/aa41423-21.html
Adapted to python with numba
"""


import math

try:
    from numba import float64, njit
    numba_avail = True
except ImportError:
    numba_avail = False


def solve_kepler_ell(ecc, ma, tol):
    """
    Numerically finds root of keplers equaion:
    ma = ea - e * sin(ea)
    Using enhanced Newton-Rhapson root solver for Keplr Equation (ERNKE).
    With provided minimal tolerance.
    """
    # mr = ma % (6.2831853071795864779)   # more turns
    mr = ma   # one turn

    if mr > math.pi:
        mr = 2 * math.pi - mr
        flip = 1
    else:
        flip = -1

    if (ecc > 0.99 and mr < 0.0045):
        al = tol / 1e7
        be = tol / 0.3
        fp = 2.7 * mr
        fpp = 0.301
        f = 0.154
        i = 0
        for i in range(1000):   # failsafe
            if (fpp - fp) <= (al + be * f):
                break
            if (f - ecc * math.sin(f) - mr) > 0:
                fpp = f
            else:
                fp = f
        f = 0.5 * (fp + fpp)
        return ma + flip * (mr - f)

    tol2s = 2 * tol / (ecc + 2.2e-16)
    eapp = mr + 0.999999 * mr * (math.pi - mr)/(2.*mr + ecc - math.pi + 2.4674011002723395 / (ecc + 2.2e-16))
    fpp = ecc * math.sin(eapp)
    fppp = ecc * math.cos(eapp)
    fp = 1 - fppp
    f = eapp - fpp - mr
    delta = - f / fp
    fp3 = fp * fp * fp
    ffpfpp = f * fp * fpp
    f2fppp = f * f * fppp
    delta = delta * (fp3 - 0.5 * ffpfpp + f2fppp / 3) / (fp3 - ffpfpp + 0.5 * f2fppp)
    for i in range(30):   # prevent infinite loops
        if delta * delta < fp * tol2s:
            break
        eapp = eapp + delta
        fp = 1 - ecc * math.cos(eapp)
        delta = (mr - eapp + ecc * math.sin(eapp)) / fp
    eapp = eapp + delta
    return ma + flip * (mr - eapp)


# if numba is available, compile functions ahead of time
if numba_avail:
    jitkw = {"cache": True}
    solve_kepler_ell = njit(float64(float64, float64, float64), **jitkw)(solve_kepler_ell)
