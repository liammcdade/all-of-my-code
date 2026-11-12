"""
planet_gravity.py
=================
Surface gravity on any planet at any coordinate, computed from
mass, shape, rotation, and mass-distribution moments -- never from
a plugged-in "g = 9.81 m/s^2".

Levels of fidelity (all take only physical inputs, not measured g):
   1. point_mass_g              - sphere, no rotation              (M, r)
   2. latitude_g                - sphere + rotation                (M, r, omega)
   3. j2_g                      - oblate body (J2) + rotation      (M, a, b, J2, omega)
   4. normal_g / somigliana_g   - reference ellipsoid              (a, b, g_eq, g_pole)
        ... but g_eq, g_pole are computed by derive_g_equator_pole
   5. SphericalHarmonicGravity  - full field, latitude AND longitude

Key helpers that replace "putting gravity in":
   derive_g_equator_pole   - g_eq, g_pole from (M, a, b, J2, omega)
   j2_hydrostatic          - J2 from flattening + rotation (Darwin-Radau)

Units: SI (m, kg, s, rad internally; degrees at the API).
"""

import math

G = 6.67430e-11  # gravitational constant [m^3 kg^-1 s^-2]


# ---------------------------------------------------------------------------
# 1. Simplest: spherical, non-rotating planet
# ---------------------------------------------------------------------------
def point_mass_g(M, r, G=G):
    """g = GM / r^2   (r = distance from planet centre)."""
    return G * M / r**2


# ---------------------------------------------------------------------------
# 2. Sphere + rotation (latitude dependence only)
# ---------------------------------------------------------------------------
def latitude_g(M, r, omega, lat_deg, G=G):
    """
    Effective gravity on a rotating sphere.

        g_r  = GM/r^2 - omega^2 r cos^2(lat)      (inward, positive)
        g_ph = -omega^2 r sin(lat) cos(lat)        (toward equator in N. hemisphere)

    Returns (|g|, g_r_inward, g_ph_northward).
    """
    phi = math.radians(lat_deg)
    s, c = math.sin(phi), math.cos(phi)

    g_r = G * M / r**2 - omega**2 * r * c**2
    g_ph = -omega**2 * r * s * c
    return math.hypot(g_r, g_ph), g_r, g_ph


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def ellipsoid_radius(a, b, lat_deg):
    """Geocentric radius of the ellipsoid at geodetic latitude (exact)."""
    phi = math.radians(lat_deg)
    s2, c2 = math.sin(phi)**2, math.cos(phi)**2
    num = a**4 * c2 + b**4 * s2
    den = a**2 * c2 + b**2 * s2
    return math.sqrt(num / den)


def geodetic_to_ecef(lat_deg, lon_deg, h, a, b):
    """Geodetic (lat, lon, height) -> Earth-centred Cartesian (x, y, z)."""
    phi, lam = math.radians(lat_deg), math.radians(lon_deg)
    e2 = 1.0 - (b / a)**2
    N = a / math.sqrt(1.0 - e2 * math.sin(phi)**2)
    x = (N + h) * math.cos(phi) * math.cos(lam)
    y = (N + h) * math.cos(phi) * math.sin(lam)
    z = (N * (1.0 - e2) + h) * math.sin(phi)
    return x, y, z


# ---------------------------------------------------------------------------
# THE KEY STEP: derive g_equator and g_pole from (M, a, b, J2, omega).
# No gravity value goes in.
# ---------------------------------------------------------------------------
def derive_g_equator_pole(M, a, b, J2, omega, G=G):
    """
    Surface gravity at the equator and pole of an oblate rotating body,
    computed from mass, shape, quadrupole moment J2, and spin rate.

    Starting from the standard external potential

        V(r, phi) = GM/r * [1 - J2 (a/r)^2 P2(sin phi)],   P2(x) = (3x^2 - 1)/2

    the inward gravitational acceleration is

        g_grav(r, phi) = GM/r^2 * [1 - 3 J2 (a/r)^2 P2(sin phi)]

    and the rotation adds -omega^2 r cos^2(phi) to the inward direction.

        g_pole    = GM/b^2 * [1 - 3 J2 (a/b)^2]
        g_equator = GM/a^2 * [1 + (3/2) J2]  -  omega^2 a

    Returns (g_equator, g_pole) in m/s^2.
    """
    mu = G * M
    g_pole    = mu / b**2 * (1.0 - 3.0 * J2 * (a / b)**2)
    g_equator = mu / a**2 * (1.0 + 1.5 * J2) - omega**2 * a
    return g_equator, g_pole


def j2_hydrostatic(f, m):
    """
    Darwin-Radau: for a body in hydrostatic equilibrium,

        J2 = (2/3) f [ 1 - (2/5) sqrt( 5m/(2f) - 1 ) ]

    where f = (a-b)/a is the flattening and m = omega^2 a^3 / (GM).
    Accurate for gas giants and (within a few %) for Earth-like planets.
    Raises if the body cannot be hydrostatic at these (f, m).
    """
    val = 5.0 * m / (2.0 * f) - 1.0
    if val < 0.0:
        raise ValueError(
            "Body cannot be in hydrostatic equilibrium with "
            f"f = {f:.3e}, m = {m:.3e} (would need J2 < 0)."
        )
    return (2.0 / 3.0) * f * (1.0 - (2.0 / 5.0) * math.sqrt(val))


# ---------------------------------------------------------------------------
# 3. Oblate planet: J2 + rotation
# ---------------------------------------------------------------------------
def j2_g(M, a, J2, omega, lat_deg, b=None, G=G):
    """
    Effective surface gravity on an oblate, rotating body. Returns
        (|g|, g_r_inward, g_phi_northward, r_surface).
    Sign convention: g_r_inward > 0 means gravity points toward the centre;
    g_phi_northward > 0 means the tangential component points toward the pole.
    """
    r = ellipsoid_radius(a, b, lat_deg) if b else a
    phi = math.radians(lat_deg)
    s, c = math.sin(phi), math.cos(phi)
    mu = G * M

    P2 = 0.5 * (3.0 * s * s - 1.0)
    j2 = 3.0 * mu * a**2 * J2 / r**4          # helper: 3 GM a^2 J2 / r^4

    g_r  = mu / r**2 - j2 * P2 - omega**2 * r * c * c
    g_ph = -(j2 + omega**2 * r) * s * c

    return math.hypot(g_r, g_ph), g_r, g_ph, r


# ---------------------------------------------------------------------------
# 4. Somigliana normal gravity (now fed by *derived* g_eq, g_pole)
# ---------------------------------------------------------------------------
def somigliana_g(a, b, g_equator, g_pole, lat_deg):
    """
    Normal gravity on the reference ellipsoid (geodetic latitude):
        g(lat) = (a g_e cos^2 + b g_p sin^2) / sqrt(a^2 cos^2 + b^2 sin^2)
    """
    phi = math.radians(lat_deg)
    s2, c2 = math.sin(phi)**2, math.cos(phi)**2
    num = a * g_equator * c2 + b * g_pole * s2
    den = math.sqrt(a**2 * c2 + b**2 * s2)
    return num / den


def normal_g(lat_deg, M, a, b, J2, omega, G=G):
    """Convenience: Somigliana gravity at geodetic latitude with g_eq/g_pole derived."""
    g_eq, g_pole = derive_g_equator_pole(M, a, b, J2, omega, G)
    return somigliana_g(a, b, g_eq, g_pole, lat_deg)


def somigliana_height_g(a, b, g_equator, g_pole, omega, lat_deg, h):
    """Somigliana continued to height h above the ellipsoid."""
    phi = math.radians(lat_deg)
    f = (a - b) / a
    m = omega**2 * a / g_equator
    g0 = somigliana_g(a, b, g_equator, g_pole, lat_deg)
    return (g0
            - (2.0 * g_equator / a) * (1.0 + f + m - 2.0 * f * math.sin(phi)**2) * h
            + (3.0 * g_equator / a**2) * h**2)


# ---------------------------------------------------------------------------
# 5. Full spherical-harmonic gravity field (latitude AND longitude)
# ---------------------------------------------------------------------------
def _legendre_norm(nmax, theta):
    """
    Fully normalised associated Legendre functions P̄_nm(cos theta),
    no Condon-Shortley phase (matches EGM/GMM/GRAIL coefficient files).
    Returns 2-D list P[n][m].
    """
    x, s = math.cos(theta), math.sin(theta)
    P = [[0.0] * (nmax + 1) for _ in range(nmax + 1)]
    P[0][0] = 1.0
    if nmax >= 1:
        P[1][0] = math.sqrt(3.0) * x
        P[1][1] = math.sqrt(3.0) * s
    for n in range(2, nmax + 1):
        P[n][n] = math.sqrt((2 * n + 1) / (2 * n)) * s * P[n - 1][n - 1]
        for m in range(n):
            a_nm = math.sqrt((2 * n - 1) * (2 * n + 1) / ((n - m) * (n + m)))
            if n - 2 >= m:
                b_nm = math.sqrt((2 * n + 1) * (n + m - 1) * (n - m - 1)
                                 / ((n - m) * (n + m) * (2 * n - 3)))
                P[n][m] = a_nm * x * P[n - 1][m] - b_nm * P[n - 2][m]
            else:
                P[n][m] = a_nm * x * P[n - 1][m]
    return P


class SphericalHarmonicGravity:
    """
    Force function (so g = grad U, inward radial is negative dU/dr):

        U = GM/r * [ 1 + sum_{n>=2} (a/r)^n sum_{m=0..n} P̄_nm(cos theta)
                     (C_nm cos(m lam) + S_nm sin(m lam)) ]
            + 1/2 omega^2 r^2 sin^2(theta)                <- centrifugal

    Coefficients are fully normalised, dimensionless, planet-specific.
    Convention: C[2,0] = -J2.
    """

    def __init__(self, M, a, omega, C, S, nmax=4, G=G):
        self.M, self.a, self.omega = M, a, omega
        self.C, self.S, self.nmax = C, S, nmax
        self.G = G

    def potential(self, r, theta, lam):
        mu, a, om = self.G * self.M, self.a, self.omega
        P = _legendre_norm(self.nmax, theta)

        acc = 0.0
        for n in range(2, self.nmax + 1):
            ar = (a / r) ** n
            for m in range(n + 1):
                C = self.C.get((n, m), 0.0)
                S = self.S.get((n, m), 0.0)
                if C == 0.0 and S == 0.0:
                    continue
                acc += ar * P[n][m] * (C * math.cos(m * lam) + S * math.sin(m * lam))

        return mu / r * (1.0 + acc) + 0.5 * om * om * r * r * math.sin(theta) ** 2

    def potential_xyz(self, x, y, z):
        r = math.sqrt(x * x + y * y + z * z)
        theta = math.acos(max(-1.0, min(1.0, z / r)))
        lam = math.atan2(y, x)
        return self.potential(r, theta, lam)

    def gravity_ecef(self, x, y, z, step=None):
        """Gravity vector (gx, gy, gz) and magnitude at (x, y, z)."""
        r = math.sqrt(x * x + y * y + z * z)
        h = step if step is not None else max(1.0, 1e-5 * r)

        gx = (self.potential_xyz(x + h, y, z) - self.potential_xyz(x - h, y, z)) / (2 * h)
        gy = (self.potential_xyz(x, y + h, z) - self.potential_xyz(x, y - h, z)) / (2 * h)
        gz = (self.potential_xyz(x, y, z + h) - self.potential_xyz(x, y, z - h)) / (2 * h)

        return (gx, gy, gz), math.sqrt(gx * gx + gy * gy + gz * gz)

    def surface_gravity(self, lat_deg, lon_deg, h=0.0, b=None):
        b = b if b is not None else self.a * (1.0 - 1.0 / 298.257223563)
        x, y, z = geodetic_to_ecef(lat_deg, lon_deg, h, self.a, b)
        return self.gravity_ecef(x, y, z)


# ---------------------------------------------------------------------------
# Planet presets -- NOTE: no g values. Only mass, shape, spin, and J2.
# (J2 is a dimensionless shape/mass-distribution number obtained from orbit
#  tracking; if you want to avoid even that, use j2_hydrostatic for bodies
#  that are fluid-like. The Moon is NOT hydrostatic, so it must supply J2.)
# ---------------------------------------------------------------------------
EARTH = dict(
    M=5.972168e24,           # kg
    a=6378137.0,             # m  equatorial radius
    b=6356752.314245,        # m  polar radius
    omega=7.2921150e-5,      # rad/s
    J2=1.08262668e-3,
)
MARS = dict(
    M=6.4171e23,
    a=3396190.0,
    b=3376200.0,
    omega=7.088218e-5,
    J2=1.96045e-3,
)
MOON = dict(
    M=7.346e22,              # kg  (0.0123 Earth)
    a=1738.1e3,              # m   equatorial radius
    b=1736.0e3,              # m   polar radius
    R_mean=1737.4e3,         # m
    omega=2.6617e-6,         # rad/s sidereal
    J2=2.03e-4,
    C22=2.24e-5,             # tidal bulge toward Earth
)


# ---------------------------------------------------------------------------
# Demo / verification
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    M = MOON
    moon_sh = SphericalHarmonicGravity(
        M['M'], M['a'], M['omega'],
        {(2, 0): -M['J2'], (2, 2): M['C22']}, {(2, 2): 0.0}, nmax=2)

    from tqdm import tqdm
    from numpy import linspace, meshgrid

    n_lat, n_lon = 224, 224
    lats = linspace(-90.0, 90.0, n_lat)
    lons = linspace(-180.0, 180.0, n_lon)
    lat_grid, lon_grid = meshgrid(lats, lons, indexing="ij")
    lat_flat = lat_grid.ravel()
    lon_flat = lon_grid.ravel()
    n = lat_flat.size

    gees = []
    for i in tqdm(range(n), desc="Sampling Moon gravity", unit="coord"):
        _, gmag = moon_sh.surface_gravity(lat_flat[i], lon_flat[i], b=M['b'])
        gees.append(gmag)

    total = sum(gees)
    avg = total / n
    n_above = sum(1 for g in gees if g > avg)
    n_below = n - n_above
    pct_above = 100.0 * n_above / n
    pct_below = 100.0 * n_below / n
    max_dev = max(abs(g - avg) for g in gees)
    pct_max_change = 100.0 * max_dev / avg

    print(f"  Moon mean surface gravity over {n} equally-spaced coordinates: "
          f"{avg:.5f} m/s^2")
    print(f"  Coordinates above average: {pct_above:.2f}%")
    print(f"  Coordinates below average: {pct_below:.2f}%")
    print(f"  Max deviation from average: {pct_max_change:.4f}%  ({max_dev:.5g} m/s^2)")