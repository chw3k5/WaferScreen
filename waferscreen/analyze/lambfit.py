import numpy as np
from numpy import pi
from scipy.optimize import fsolve

# Note: lambda is a reserved word, so lamb is used instead

Phi0 = 2.068e-15  # magnetic flux quantum


def phie_of_phi(phi, lamb):
    phie = phi + lamb * np.sin(phi)
    return phie


def phi_sum(phi, *args):
    phie, lamb = args
    return (phie_of_phi(phi, lamb) - phie)


def phi_of_phie(phie, lamb):
    phiguess = phie
    argvals = (phie, lamb)
    phi = fsolve(phi_sum, phiguess, args=argvals)
    return phi


def f0_of_phi(phi, f2, P, lamb):
    # Odd formulation hopefully makes variation in lamb not affect f2 or P
    f0 = f2 + (P / 2) * ((1 - lamb ** 2) / lamb) * (
                (lamb * np.cos(phi)) / (1 + lamb * np.cos(phi)) + (lamb ** 2) / (1 - lamb ** 2))
    return f0


def f0_of_phie(phie, f2, P, lamb):
    phi = phi_of_phie(phie, lamb)
    f0 = f0_of_phi(phi, f2, P, lamb)
    return f0


def f0_of_I(ramp_current_amps, ramp_current_amps_0, m, f2, P, lamb):
    phie = (ramp_current_amps - ramp_current_amps_0) * m
    f0 = f0_of_phie(phie, f2, P, lamb)
    return f0


def guess_lamb_fit_params(ramp_current_amps, f0):
    Pguess = np.max(f0) - np.min(f0)
    f2guess = (np.max(f0) + np.min(f0)) / 2.0
    I0guess = ramp_current_amps[np.argmax(f0)]
    mguess = pi / 90.0e-6  # np.abs( I[np.argmax(f0)] - I[np.argmin(f0)] ) # assumes 0.5 to 1.5 periods
    lambguess = 0.33
    return I0guess, mguess, f2guess, Pguess, lambguess