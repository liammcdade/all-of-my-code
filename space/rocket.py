import numpy as np
from scipy.integrate import quad

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
c_km_s = 299792.458
Mpc_to_ly = 3.26156e6
ly_to_m = 9.4607304725808e15

# ----------------------------------------------------------------------
# Planck 2018 parameters
# ----------------------------------------------------------------------
H0 = 67.4
Omega_m = 0.315
Omega_r = 9.2e-5
Omega_K_central = 0.0007
Omega_K_err = 0.0019   # 95% CL

# ----------------------------------------------------------------------
# Cosmology helpers
# ----------------------------------------------------------------------
def E(z, Omega_K):
    Omega_Lambda = 1.0 - Omega_m - Omega_r - Omega_K
    return np.sqrt(
        Omega_m * (1 + z)**3 +
        Omega_r * (1 + z)**4 +
        Omega_K * (1 + z)**2 +
        Omega_Lambda
    )

def horizon_geometry(Omega_K):
    """Returns (radius, surface_area, volume) in Mpc units."""
    I, _ = quad(lambda z: 1.0 / E(z, Omega_K), 0, np.inf)

    if abs(Omega_K) < 1e-12:
        chi = c_km_s / H0 * I
        area = 4 * np.pi * chi**2
        volume = (4/3) * np.pi * chi**3
        return chi, area, volume

    R_curv = c_km_s / (H0 * np.sqrt(abs(Omega_K)))
    x = np.sqrt(abs(Omega_K)) * I

    if Omega_K > 0:  # open
        chi = R_curv * np.sinh(x)
        area = 4 * np.pi * R_curv**2 * np.sinh(x)**2
        volume = np.pi * R_curv**3 * (np.sinh(2*x) - 2*x)
    else:            # closed
        chi = R_curv * np.sin(x)
        area = 4 * np.pi * R_curv**2 * np.sin(x)**2
        volume = 2 * np.pi * R_curv**3 * (x - np.sin(2*x)/2)

    return chi, area, volume

# ----------------------------------------------------------------------
# Average across the curvature uncertainty band
# ----------------------------------------------------------------------
def averaged_geometry():
    # Sample Omega_K across the 95% CL range
    Omegas = np.linspace(
        Omega_K_central - Omega_K_err,
        Omega_K_central + Omega_K_err,
        101
    )
    radii, areas, volumes = [], [], []
    for Ok in Omegas:
        r, a, v = horizon_geometry(Ok)
        radii.append(r)
        areas.append(a)
        volumes.append(v)
    return (np.mean(radii), np.mean(areas), np.mean(volumes),
            np.std(radii),  np.std(areas),  np.std(volumes))

# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------
R_mean, A_mean, V_mean, R_std, A_std, V_std = averaged_geometry()

# Convert to light-years
R_ly  = R_mean * Mpc_to_ly
A_ly2 = A_mean * Mpc_to_ly**2
V_ly3 = V_mean * Mpc_to_ly**3

# Dimensions in x, y, z
diameter_ly = 2 * R_ly              # sphere diameter (same in x, y, z)
bbox_ly     = 2 * R_ly              # bounding cube side

# ----------------------------------------------------------------------
# Single-number output
# ----------------------------------------------------------------------
print("Observable universe (averaged over Omega_K 95% CL band)")
print("=" * 60)
print(f"Radius                  : {R_ly/1e9:.3f} billion ly")
print(f"Diameter (x = y = z)    : {diameter_ly/1e9:.3f} billion ly")
print()
print(f"Surface area            : {A_ly2:.3e} ly^2")
print(f"Volume                  : {V_ly3:.3e} ly^3")
print()
print("One-line summary")
print("-" * 60)
print(f"Volume ≈ {V_ly3:.3e} cubic light-years")
print(f"Dimensions ≈ {diameter_ly/1e9:.3f} × "
      f"{diameter_ly/1e9:.3f} × {diameter_ly/1e9:.3f} billion light-years")