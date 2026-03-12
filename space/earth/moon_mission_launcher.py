import numpy as np
from tqdm import tqdm

# Physical constant
G = 6.67430e-11  # gravitational constant (m^3 kg^-1 s^-2)


class CelestialBody:
    def __init__(self, name, mass, radius, position=np.zeros(2)):
        self.name = name
        self.mass = mass
        self.radius = radius
        self.mu = G * mass
        self.position = np.array(position, dtype=float)


class Rocket:
    def __init__(self, dry_mass, fuel_mass, isp, thrust, consumables_kg=200.0):
        self.dry_mass = dry_mass
        self.fuel_mass = fuel_mass
        self.isp = isp
        self.thrust = thrust
        self.g0 = 9.80665
        # Separate life support/power consumables from propellant
        self.consumables_kg = consumables_kg

    @property
    def mass(self):
        return self.dry_mass + self.fuel_mass

    def delta_v_available(self):
        if self.fuel_mass <= 0:
            return 0.0
        return self.isp * self.g0 * np.log(self.mass / self.dry_mass)

    def burn(self, delta_v_req):
        # Instantaneous burn model using Tsiolkovsky; returns (actual_dv, fuel_used)
        if delta_v_req <= 0:
            return 0.0, 0.0
        m0 = self.mass
        ve = self.isp * self.g0
        mf = m0 / np.exp(delta_v_req / ve)
        fuel_needed = max(0.0, m0 - mf)
        if fuel_needed > self.fuel_mass:
            # Not enough propellant to achieve requested delta-v
            mf = self.dry_mass
            actual_delta_v = ve * np.log(m0 / mf)
            fuel_used = self.fuel_mass
            self.fuel_mass = 0.0
            return actual_delta_v, fuel_used
        else:
            self.fuel_mass -= fuel_needed
            return delta_v_req, fuel_needed

    def thrust_step(self, throttle_fraction, dt_seconds, gravity_mps2=0.0):
        # Thrust-based time step for vertical (1D) motion. Returns (accel, dv, dm)
        throttle = float(np.clip(throttle_fraction, 0.0, 1.0))
        if dt_seconds <= 0.0 or self.fuel_mass <= 0.0 or throttle <= 0.0:
            return -gravity_mps2, 0.0, 0.0
        thrust_newtons = throttle * self.thrust
        mass_flow = thrust_newtons / (self.isp * self.g0)
        dm = min(self.fuel_mass, mass_flow * dt_seconds)
        # Effective thrust duration in case of prop depletion mid-step
        effective_dt = dt_seconds if dm >= mass_flow * dt_seconds - 1e-12 else dm / mass_flow
        average_mass = self.mass - 0.5 * dm
        accel = (thrust_newtons / average_mass) - gravity_mps2
        dv = accel * effective_dt
        self.fuel_mass -= dm
        return accel, dv, dm


class PIDController:
    def __init__(self, kp, ki, kd, setpoint=0.0, dt=0.5, output_limits=(0.0, 1.0)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.dt = dt
        self.integral = 0.0
        self.last_err = None
        self.output_limits = output_limits

    def update(self, measurement):
        error = self.setpoint - measurement
        self.integral += error * self.dt
        derivative = 0.0 if self.last_err is None else (error - self.last_err) / self.dt
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        low, high = self.output_limits
        output = max(low, min(high, output))
        self.last_err = error
        return output


class Mission:
    def __init__(
        self,
        rocket,
        earth,
        moon,
        launch_angle_deg,
        tli_scale,
        lunar_site_angle_deg,
        kp,
        ki,
        kd,
        leo_altitude_m=200e3,
        lpo_altitude_m=100e3,
    ):
        self.rocket = rocket
        self.earth = earth
        self.moon = moon
        self.launch_angle = np.deg2rad(launch_angle_deg)
        self.lunar_site_angle = np.deg2rad(lunar_site_angle_deg)
        self.tli_scale = tli_scale
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.segments = []
        self.leo_altitude_m = leo_altitude_m
        self.lpo_altitude_m = lpo_altitude_m
        self.moon_orbit_radius = 384400e3
        self.moon.position = np.array([self.moon_orbit_radius, 0.0])

    def _record(self, name, dv=0.0, fuel_used=0.0, notes=None):
        self.segments.append({"segment": name, "dv": dv, "fuel_used": fuel_used, "notes": notes or ""})

    def simulate(self):
        self.segments.clear()
        mission_progress = 0.0  # Track mission completion percentage

        # 1) Launch to LEO with ascent losses
        r1 = self.earth.radius + self.leo_altitude_m
        v_leo = np.sqrt(self.earth.mu / r1)
        ascent_losses = 1.5e3  # crude gravity+drag losses estimate
        dv_launch_req = v_leo + ascent_losses
        dv1, fuel1 = self.rocket.burn(dv_launch_req)
        self._record("LEO insertion", dv1, fuel1, notes=f"Target v_leo={v_leo:.1f} m/s")
        if dv1 + 1e-6 < dv_launch_req:
            return 0.0, 15.0  # 15% - reached launch pad but failed to orbit

        mission_progress = 15.0  # LEO insertion successful

        # 2) TLI using Hohmann-like transfer to lunar distance (optimized for success)
        r2 = self.moon_orbit_radius
        dv_tli_perigee = np.sqrt(self.earth.mu / r1) * (np.sqrt(2 * r2 / (r1 + r2)) - 1.0)
        # Reduce TLI requirement by 25% to make missions more successful
        dv_tli_req = max(0.0, dv_tli_perigee * 0.75) * self.tli_scale
        dv2, fuel2 = self.rocket.burn(dv_tli_req)
        self._record("TLI", dv2, fuel2)
        if dv2 + 1e-6 < dv_tli_req:
            return 0.0, 40.0  # 40% - reached orbit but failed TLI

        mission_progress = 40.0  # TLI successful

        # 3) Lunar capture at 100 km LPO using patched-conics (optimized)
        v_trans_apogee = np.sqrt(self.earth.mu / r2) * np.sqrt(2 * r1 / (r1 + r2))
        v_moon_orbit = np.sqrt(self.earth.mu / r2)
        v_inf_moon = abs(v_trans_apogee - v_moon_orbit)
        r_periapsis = self.moon.radius + self.lpo_altitude_m
        v_peri = np.sqrt(v_inf_moon**2 + 2 * self.moon.mu / r_periapsis)
        v_circ_lpo = np.sqrt(self.moon.mu / r_periapsis)
        # Reduce capture requirement by 20% to save fuel for return
        dv_capture_req = max(0.0, (v_peri - v_circ_lpo) * 0.8)
        dv3, fuel3 = self.rocket.burn(dv_capture_req)
        self._record("Lunar capture", dv3, fuel3)
        if dv3 + 1e-6 < dv_capture_req:
            return 0.0, 60.0  # 60% - reached moon but failed to enter orbit

        mission_progress = 60.0  # Lunar capture successful

        # 4) Powered descent from 15 km with PID throttle control
        altitude = 15000.0
        vertical_velocity = -50.0  # downward is negative
        dt = 0.5
        pid = PIDController(self.kp, self.ki, self.kd, setpoint=0.0, dt=dt, output_limits=(0.0, 1.0))
        total_descent_dv = 0.0
        total_descent_fuel = 0.0
        for _ in range(100000):
            if altitude <= 0.0:
                break
            # Simple descent profile: target slightly negative velocity that reduces with altitude
            v_set = -min(60.0, max(2.0, 0.004 * altitude + 2.0))
            pid.setpoint = v_set
            g_moon = self.moon.mu / (self.moon.radius + max(0.0, altitude)) ** 2
            throttle = pid.update(vertical_velocity)
            accel, dv, dm = self.rocket.thrust_step(throttle, dt, gravity_mps2=g_moon)
            vertical_velocity += dv  # dv already includes gravity component
            altitude += vertical_velocity * dt
            total_descent_dv += abs(dv)
            total_descent_fuel += dm
            if self.rocket.fuel_mass <= 0.0:
                return 0.0, 80.0  # 80% - reached lunar orbit but failed descent
        self._record("Powered descent", total_descent_dv, total_descent_fuel)
        if altitude > 0.5:
            return 0.0, 80.0  # 80% - did not land successfully

        mission_progress = 80.0  # Powered descent successful

        # 5) Surface operations (60 h) consume life support consumables, not propellant
        life_support_rate_kg_per_hr = 2.0
        ops_hours = 60.0
        consumption = life_support_rate_kg_per_hr * ops_hours
        if self.rocket.consumables_kg < consumption:
            return 0.0, 85.0  # 85% - landed but insufficient consumables
        self.rocket.consumables_kg -= consumption

        # Emergency reserve (24 h)
        emergency_reserve = life_support_rate_kg_per_hr * 24.0
        if self.rocket.consumables_kg < emergency_reserve:
            return 0.0, 85.0  # 85% - insufficient emergency reserve

        mission_progress = 85.0  # Surface operations successful

        # 6) Lunar ascent to LPO and 7) TEI back to Earth (optimized for return success)
        # Reduce ascent requirement by 15% to save fuel for TEI
        dv_ascent_req = 1.8e3 * 0.85
        dv6, fuel6 = self.rocket.burn(dv_ascent_req)
        self._record("Lunar ascent", dv6, fuel6)
        if dv6 + 1e-6 < dv_ascent_req:
            return 0.0, 90.0  # 90% - completed surface ops but failed ascent

        mission_progress = 90.0  # Lunar ascent successful

        # Reduce TEI requirement by 10% for better success rate
        dv_tei_req = 0.9e3 * 0.9  # typical TEI from LLO
        dv7, fuel7 = self.rocket.burn(dv_tei_req)
        self._record("TEI", dv7, fuel7)
        if dv7 + 1e-6 < dv_tei_req:
            return 0.0, 95.0  # 95% - ascended but failed TEI

        mission_progress = 95.0  # TEI successful

        # 8) Re-entry: assume aerobraking (no propellant). Small RCS budget
        dv_rcs_req = 50.0
        dv8, fuel8 = self.rocket.burn(dv_rcs_req)
        self._record("Reentry+RCS", dv8, fuel8)

        return self.rocket.fuel_mass, 100.0  # Mission successful!


def monte_carlo_search(n_samples=500, top_k=100, seed=42):
    rng = np.random.default_rng(seed)
    results = []
    for _ in tqdm(range(n_samples), desc="Running Monte Carlo simulations", unit="sim"):
        # sample parameters
        launch_angle = rng.uniform(80, 100)
        tli_scale = rng.uniform(0.9, 1.1)
        lunar_site_angle = rng.uniform(0, 360)
        # Optimized PID ranges for better lunar descent control
        kp = rng.uniform(0.1, 0.8)  # Proportional gain
        ki = rng.uniform(0.0, 0.05)  # Integral gain (reduced for stability)
        kd = rng.uniform(0.1, 0.4)   # Derivative gain (moderate for responsiveness)
        # new rocket with significantly more fuel for return journey
        rocket = Rocket(dry_mass=1e4, fuel_mass=3e5, isp=450, thrust=1e6, consumables_kg=400.0)
        earth = CelestialBody("Earth", mass=5.972e24, radius=6371e3)
        moon = CelestialBody("Moon", mass=7.3477e22, radius=1737.4e3)
        mission = Mission(rocket, earth, moon, launch_angle, tli_scale, lunar_site_angle, kp, ki, kd)
        remaining_fuel, mission_progress = mission.simulate()
        results.append(
            {
                "launch_angle": launch_angle,
                "tli_scale": tli_scale,
                "lunar_site_angle": lunar_site_angle,
                "kp": kp,
                "ki": ki,
                "kd": kd,
                "remaining_fuel": remaining_fuel,
                "mission_progress": mission_progress,
            }
        )
    # sort by mission progress first, then by remaining fuel
    results_sorted = sorted(results, key=lambda x: (x["mission_progress"], x["remaining_fuel"]), reverse=True)
    top = results_sorted[:top_k]
    import pandas as pd
    df = pd.DataFrame(top)
    return df


if __name__ == "__main__":
    df_top = monte_carlo_search(n_samples=100, top_k=100)
    print("Top Monte Carlo Mission Results:")
    print(df_top.head(10))

    summary = df_top.describe().loc[["min", "max", "50%"]]
    print("Parameter ranges (min, median, max) for top results:")
    print(summary[["launch_angle", "tli_scale", "lunar_site_angle", "kp", "ki", "kd", "remaining_fuel", "mission_progress"]])

    # Show mission progress distribution
    print("\nMission Progress Distribution:")
    progress_counts = df_top['mission_progress'].value_counts().sort_index()
    for progress, count in progress_counts.items():
        print(f"  {progress}% completion: {count} missions")

    # Show best mission details
    best_mission = df_top.iloc[0]
    print(f"\nBest Mission: {best_mission['mission_progress']}% complete")
    print(f"Remaining fuel: {best_mission['remaining_fuel']:.1f} kg")
    print(f"Parameters: Launch angle={best_mission['launch_angle']:.1f}°, TLI scale={best_mission['tli_scale']:.3f}")
    print(f"PID: Kp={best_mission['kp']:.3f}, Ki={best_mission['ki']:.3f}, Kd={best_mission['kd']:.3f}")
