# moon_return_optimizer.py
# Physics-heavy patched-conics Moon mission optimizer using a (1+1)-ES.
# Run: python moon_return_optimizer.py
import math
import numpy as np
import time
# -----------------------
# Constants
# -----------------------
G = 6.67430e-11
M_earth = 5.97219e24
R_earth = 6371000.0
mu_earth = G * M_earth
M_moon = 7.342e22
R_moon = 1737000.0
mu_moon = G * M_moon
dist_earth_moon = 384400000.0  # mean distance (m)
g0 = 9.80665
# LEO altitude & circular orbit radius
LEO_alt = 200000.0
r_leo = R_earth + LEO_alt
# Mission tolerances
moon_orbit_alt = 100000.0  # 100 km lunar orbit target
r_lunar_orbit = R_moon + moon_orbit_alt
max_landing_v = 2.0  # m/s allowed vertical touchdown speed (soft)
max_surface_time = 23 * 3600.0  # 23 hours in seconds
# -----------------------
# Rocket / vehicle baseline (tweakable)
# -----------------------
dry_mass = 9000.0          # kg (structure + payload + command module)
initial_prop_mass = 240000.0  # kg propellant available (big, includes upper stages)
Isp = 450.0                # s (high-performance upper-stage / LH2 engines)
ve = Isp * g0
# Some fixed delta-v losses/assumptions
launch_dv = 9300.0  # m/s to reach LEO (including gravity/drag losses) - consumed as required
# -----------------------
# Orbital mechanics helpers
# -----------------------
def circular_velocity(mu, r):
    return math.sqrt(mu / r)
def hohmann_transfer_delta_v(mu, r1, r2):
    # Delta-v to go from circular r1 to transfer ellipse perigee at r1 and apogee at r2 (semi-major a)
    a = 0.5 * (r1 + r2)
    v1 = math.sqrt(mu / r1)
    vp = math.sqrt(mu * (2.0 / r1 - 1.0 / a))
    dv1 = vp - v1
    # At arrival (not used here), dv2 = v2 - va ...
    return dv1
def vis_viva_velocity(mu, r, a):
    # speed at radius r on orbit with semi-major a
    return math.sqrt(mu * (2.0 / r - 1.0 / a))
# -----------------------
# Mass utils
# -----------------------
def mass_after_dv(m0, dv, ve):
    # m_f = m0 * exp(-dv / ve)
    if dv <= 0:
        return m0, 0.0
    mf = m0 * math.exp(-dv / ve)
    fuel_used = m0 - mf
    return mf, fuel_used
# -----------------------
# Mission sim (patched-conics, instantaneous burns)
# Inputs (vector): [TLI_dv, LOI_dv, descent_dv, ascent_dv, TEI_dv] in m/s
# Returns: (success_flag, fuel_used_total, diagnostics_dict)
# -----------------------
def simulate_mission(burns, verbose=False):
    try:
        TLI_dv, LOI_dv, descent_dv, ascent_dv, TEI_dv = burns
        t = 0.0
        # Keep track of mass
        prop = initial_prop_mass
        m_total = dry_mass + prop
        diagnostics = {}
        fuel_used_total = 0.0
        # 0) Launch to LEO: consume launch_dv from prop (treated as required)
        m_after, fuel = mass_after_dv(m_total, launch_dv, ve)
        prop -= fuel
        if prop < 0:
            return False, 1e9, {"reason": "insufficient prop for launch"}
        m_total = m_after
        fuel_used_total += fuel
        diagnostics['after_LEO_mass'] = m_total
        # check LEO orbital speed
        v_leo = circular_velocity(mu_earth, r_leo)
        diagnostics['v_leo'] = v_leo
        # 1) TLI: compute required TLI for transfer approx (Hohmann-like to lunar distance)
        # Required per ideal: dv_needed = v_perigee - v_circ
        dv_ideal = hohmann_transfer_delta_v(mu_earth, r_leo, dist_earth_moon)
        # Agent provides TLI_dv; check whether it's enough
        if TLI_dv < 0:
            return False, 1e9, {"reason": "negative TLI dv"}
        # apply TLI burn
        m_after, fuel = mass_after_dv(m_total, TLI_dv, ve)
        prop -= fuel
        if prop < 0:
            return False, 1e9, {"reason": "insufficient prop at TLI"}
        m_total = m_after
        fuel_used_total += fuel
        diagnostics['after_TLI_mass'] = m_total
        diagnostics['TLI_dv'] = TLI_dv
        diagnostics['TLI_dv_ideal'] = dv_ideal
        # estimate hyperbolic excess at lunar distance (approx)
        # Simple patched-conic: velocity at far distance from Earth on transfer ellipse near lunar radius:
        a_transfer = 0.5 * (r_leo + dist_earth_moon)
        v_at_moon = vis_viva_velocity(mu_earth, dist_earth_moon, a_transfer)
        # Moon orbital velocity about Earth:
        v_moon = circular_velocity(mu_earth, dist_earth_moon)
        # relative v_inf when approaching moon (approx)
        v_inf = abs(v_at_moon - v_moon)
        diagnostics['v_inf_moon'] = v_inf
        # 2) LOI: to capture into lunar orbit. Required approx: reduce v by capture delta:
        # velocity for circular lunar orbit around Moon:
        v_circ_lunar = circular_velocity(mu_moon, r_lunar_orbit)
        # approach speed relative to moon frame is v_inf + moon orbital velocity effect -> simplified to v_inf
        # For capture, need delta-v roughly equal to hyperbolic excess to get circular orbit:
        # approximate LOI_ideal ~ sqrt(v_inf^2 + 2*mu_moon/r_peri) - v_circ_lunar (rough)
        # we'll approximate required LOI as function of v_inf
        LOI_ideal = max(0.0, math.sqrt(v_inf**2 + 2 * mu_moon / r_lunar_orbit) - v_circ_lunar)
        diagnostics['LOI_ideal'] = LOI_ideal
        if LOI_dv < 0:
            return False, 1e9, {"reason": "negative LOI dv"}
        # apply LOI burn
        m_after, fuel = mass_after_dv(m_total, LOI_dv, ve)
        prop -= fuel
        if prop < 0:
            return False, 1e9, {"reason": "insufficient prop at LOI"}
        m_total = m_after
        fuel_used_total += fuel
        diagnostics['after_LOI_mass'] = m_total
        diagnostics['LOI_dv'] = LOI_dv
        # check capture success: if LOI_dv >= LOI_ideal * (1 - tol), we capture.
        if LOI_dv + 2.0 < LOI_ideal:  # allow small margin
            return False, fuel_used_total, {"reason": "failed lunar capture", "LOI_ideal": LOI_ideal, "LOI_given": LOI_dv}
        # 3) Descent: burn from lunar circular orbit to landing (delta-v ideal empirical)
        # A rule-of-thumb descent delta-v needed ~ 1.6 km/s (as referenced). We'll compute approximate:
        descent_ideal = 1600.0  # m/s
        diagnostics['descent_ideal'] = descent_ideal
        if descent_dv < 0:
            return False, 1e9, {"reason": "negative descent dv"}
        # apply descent burn
        m_after, fuel = mass_after_dv(m_total, descent_dv, ve)
        prop -= fuel
        if prop < 0:
            return False, 1e9, {"reason": "insufficient prop at descent"}
        m_total = m_after
        fuel_used_total += fuel
        diagnostics['after_descent_mass'] = m_total
        diagnostics['descent_dv'] = descent_dv
        # touchdown check (if descent_dv >= descent_ideal within margin -> safe)
        if descent_dv + 5.0 < descent_ideal:
            return False, fuel_used_total, {"reason": "unsafe landing (too little descent dv)", "descent_ideal": descent_ideal, "descent_given": descent_dv}
        # 4) 23 hour stay (simulate time passing, no consumption besides life-support negligible)
        t += max_surface_time
        diagnostics['surface_time_s'] = max_surface_time
        # 5) Ascent: leave lunar surface to lunar orbit
        ascent_ideal = 1900.0  # m/s
        diagnostics['ascent_ideal'] = ascent_ideal
        if ascent_dv < 0:
            return False, 1e9, {"reason": "negative ascent dv"}
        m_after, fuel = mass_after_dv(m_total, ascent_dv, ve)
        prop -= fuel
        if prop < 0:
            return False, 1e9, {"reason": "insufficient prop at ascent"}
        m_total = m_after
        fuel_used_total += fuel
        diagnostics['after_ascent_mass'] = m_total
        diagnostics['ascent_dv'] = ascent_dv
        if ascent_dv + 5.0 < ascent_ideal:
            return False, fuel_used_total, {"reason": "failed ascent", "ascent_ideal": ascent_ideal, "ascent_given": ascent_dv}
        # 6) TEI: burn to set return trajectory to Earth
        TEI_ideal = 1000.0
        diagnostics['TEI_ideal'] = TEI_ideal
        if TEI_dv < 0:
            return False, 1e9, {"reason": "negative TEI dv"}
        m_after, fuel = mass_after_dv(m_total, TEI_dv, ve)
        prop -= fuel
        if prop < 0:
            return False, 1e9, {"reason": "insufficient prop at TEI"}
        m_total = m_after
        fuel_used_total += fuel
        diagnostics['after_TEI_mass'] = m_total
        diagnostics['TEI_dv'] = TEI_dv
        if TEI_dv + 5.0 < TEI_ideal:
            return False, fuel_used_total, {"reason": "missed TEI", "TEI_ideal": TEI_ideal, "TEI_given": TEI_dv}
        # Re-entry: assume passive and success if we had enough mass for heatshield etc (we keep dry_mass inclusive)
        diagnostics['final_mass'] = m_total
        # Success
        return True, fuel_used_total, diagnostics
    except Exception as e:
        print(f"Error in simulate_mission: {e}")
        return False, 1e9, {"reason": "simulation error"}
# -----------------------
# Objective / scoring
# We want to (primary) succeed mission and (secondary) minimize fuel used.
# We return a scalar cost: lower is better. Large penalty for failure.
# -----------------------
def mission_cost(burns):
    ok, fuel_used, diag = simulate_mission(burns)
    if not ok:
        # penalise by fuel used if returned, else huge penalty
        reason = diag.get('reason', '')
        # larger penalty for failure
        penalty = 1e9
        if isinstance(fuel_used, float) and fuel_used < 1e8:
            penalty = 1e8 + fuel_used * 2.0
        return penalty
    # if success, cost = fuel_used (we want to minimise)
    return fuel_used
# -----------------------
# (1+1)-ES optimizer (adaptive sigma)
# - start from an initial guess (near realistic ideals)
# - mutate by Gaussian noise with adaptive sigma
# - accept if cost improves
# -----------------------
def optimize(start, iterations=8000, init_sigma=200.0, seed=42):
    rng = np.random.default_rng(seed)
    x = np.array(start, dtype=float)
    best = x.copy()
    best_cost = mission_cost(best)
    sigma = float(init_sigma)
    success_streak = 0
    hist = []
    start_time = time.time()
    # Define minimum delta-v values based on theoretical calculations
    dv_ideal_tli = start[0]
    LOI_ideal = start[1]
    min_dv = np.array([dv_ideal_tli * 0.5, LOI_ideal * 0.5, 1600.0 * 0.5, 1900.0 * 0.5, 1000.0 * 0.5])  # Adjust as needed
    for i in range(iterations):
        # mutate
        cand = best + rng.normal(0, sigma, size=best.shape)
        # enforce non-negative dv and minimum dv values
        cand = np.maximum(cand, min_dv)
        c_cost = mission_cost(cand)
        if c_cost < best_cost:
            best = cand
            best_cost = c_cost
            success_streak += 1
            # reduce sigma slightly when improvement
            sigma *= 0.95
        else:
            success_streak = 0
            # increase sigma slowly to explore if no improvement
            sigma *= 1.0005
        # occasional larger random restart nudges if stuck
        if i % 800 == 0 and i > 0 and success_streak == 0:
            best = best + rng.normal(0, sigma * 5.0, size=best.shape)
            best = np.maximum(best, min_dv)  # Ensure minimum dv values
            best_cost = mission_cost(best)
        hist.append((i, best_cost, best.copy(), sigma))
        # quick progress log
        if i % 200 == 0:
            elapsed = time.time() - start_time
            print(f"[{i}] best_cost={best_cost:.1f} kg fuel, sigma={sigma:.1f}, elapsed={elapsed:.1f}s")
        # early exit if very good cost found
        if best_cost < 20000.0:  # arbitrary threshold: mission success with <=20 t fuel
            break
    return best, best_cost, hist
# -----------------------
# Initial guess near reference values (m/s)
# -----------------------
dv_ideal_tli = hohmann_transfer_delta_v(mu_earth, r_leo, dist_earth_moon)
# Calculate v_inf for LOI ideal
a_transfer = 0.5 * (r_leo + dist_earth_moon)
v_at_moon = vis_viva_velocity(mu_earth, dist_earth_moon, a_transfer)
v_moon = circular_velocity(mu_earth, dist_earth_moon)
v_inf = abs(v_at_moon - v_moon)
v_circ_lunar = circular_velocity(mu_moon, r_lunar_orbit)
LOI_ideal = max(0.0, math.sqrt(v_inf**2 + 2 * mu_moon / r_lunar_orbit) - v_circ_lunar)
initial_guess = np.array([
    dv_ideal_tli,  # TLI
    LOI_ideal,      # LOI
    1600.0,         # descent
    1900.0,         # ascent
    1000.0          # TEI
])
if __name__ == "__main__":
    print("Starting Moon-return optimizer (physics-heavy patched-conics approximation)")
    best, cost, history = optimize(initial_guess, iterations=5000, init_sigma=250.0)
    print("\nOptimization complete.")
    print(f"Best cost (fuel kg): {cost:.1f}")
    print("Best burn plan (m/s):")
    names = ["TLI", "LOI", "Descent", "Ascent", "TEI"]
    for n, v in zip(names, best):
        print(f"  {n:7s}: {v:.1f} m/s")
    ok, fuel_used, diag = simulate_mission(best, verbose=True)
    print("\nFinal simulation diagnostics:")
    for k, val in diag.items():
        print(f"  {k}: {val}")
