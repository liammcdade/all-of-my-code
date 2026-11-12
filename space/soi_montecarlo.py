#!/usr/bin/env python3
"""
Monte-Carlo propagation of uncertainty for Sphere-of-Influence radii.

For every planet the mass (and the gravitational constant G) are treated as
normal random variables whose 1-sigma widths are taken from the CODATA /
planetary-data uncertainties, so

    M = (5.97217 +/- 0.00028) x 10^24  kg        # Earth
    G = 6.67430 +/- 0.00015  x 10^-11  m^3 kg^-1 s^-2   # CODATA 2018

A Monte-Carlo trial draws a fresh (G, M_body, M_parent) triple, computes

    r_SOI = a * (m / M)^(2/5)

and repeats N times.  The resulting distribution gives a mean, a median, a
1-sigma (68.3 %) confidence interval, and a 95 % interval for every body.

The same machinery can trivially be extended to *any* derived quantity that
depends on G and masses, e.g. orbital periods (Keplers third law), surface
gravity, escape velocity, etc.

Usage:
    python soi_montecarlo.py
    python soi_montecarlo.py -n 2_000_000 -b Jupiter -b Earth
"""

from __future__ import annotations

import argparse
import math
import statistics
import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constants with uncertainties (CODATA 2022 for G, plus planetary data)
# ---------------------------------------------------------------------------
# G = 6.67430(15) x 10^-11 m^3 kg^-1 s^-2  ->  +/- 0.00015 x 10^-11
G_NOM: float = 6.67430e-11
G_SIG: float = 0.00015e-11          # 1-sigma

AU: float = 1.495978707e11
KM: float = 1.0e3


# ---------------------------------------------------------------------------
# Body catalogue with (nominal, 1-sigma) mass in kg
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BodyUNC:
    name: str
    mass_nom: float
    mass_sig: float
    radius: float
    parent: str | None = None
    a: float | None = None          # semi-major axis (m)


# Masses and uncertainties are taken from the IAU / planetary ephemeris
# literature.  The Earth value matches the one you quoted:
#   M_Earth = (5.97217 +/- 0.00028) x 10^24 kg
# (relative uncertainty 4.7 x 10^-5, dominated by the GM uncertainty 3.9e-5
#  from DE440 plus the G uncertainty, combined in quadrature).
BODIES: dict[str, BodyUNC] = {
    "Sun":     BodyUNC("Sun",     1.98847e30, 0.00005e30, 6.957e8),
    "Mercury": BodyUNC("Mercury", 3.3011e23,  0.00005e23, 2.4397e6,  "Sun",   57.909e9),
    "Venus":   BodyUNC("Venus",   4.8675e24,  0.00010e24, 6.0518e6,  "Sun",  108.209e9),
    "Earth":   BodyUNC("Earth",   5.97217e24, 0.00028e24, 6.3710e6,  "Sun",  149.598e9),
    "Moon":    BodyUNC("Moon",    7.346e22,   0.0001e22,  1.7374e6,  "Earth", 384.4e6),
    "Mars":    BodyUNC("Mars",    6.4171e23,  0.00005e23, 3.3895e6,  "Sun",  227.92e9),
    "Jupiter": BodyUNC("Jupiter", 1.8982e27,  0.00005e27, 6.9911e7,  "Sun",  778.57e9),
    "Saturn":  BodyUNC("Saturn",  5.6834e26,  0.00005e26, 5.8232e7,  "Sun", 1433.53e9),
    "Uranus":  BodyUNC("Uranus",  8.6810e25,  0.00005e25, 2.5362e7,  "Sun", 2872.46e9),
    "Neptune": BodyUNC("Neptune", 1.02413e26, 0.00005e26, 2.4622e7,  "Sun", 4495.06e9),
}


# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------
def soi_radius(a: float, m: float, M: float, G: float = G_NOM) -> float:
    """
    Classic Hill/Laplace Sphere-of-Influence radius.

        r_SOI = a * (m / M)^(2/5)

    The form with G is exact because G cancels:

        m = M_small  -> ratio is dimensionless, G drops out.

    We keep G in the signature so that the Monte-Carlo framework *could*
    feed it a sampled value, even though the ratio m/M is independent of G.
    """
    return a * (m / M) ** 0.4


# ---------------------------------------------------------------------------
# Monte-Carlo core
# ---------------------------------------------------------------------------
def monte_carlo_soi(body_name: str, n: int, seed: int | None = None
                    ) -> dict[str, float]:
    """
    Run n trials for one body, sampling mass and G from Gaussians.

    Returns a dict with statistical summaries of the SOI distribution.
    """
    import random

    rng = random.Random(seed)
    # Use Gaussians via Box-Muller (random.gauss uses them internally).
    # For performance with large n, fall back to statistics if small.

    if body_name not in BODIES:
        raise KeyError(f"Unknown body {body_name!r}")

    body = BODIES[body_name]
    if body.parent is None or body.a is None:
        raise ValueError(f"{body_name} has no parent -> SOI undefined.")

    parent = BODIES[body.parent]

    results = [0.0] * n
    for i in range(n):
        G_s  = G_NOM + rng.gauss(0.0, G_SIG)
        m_s  = body.mass_nom  + rng.gauss(0.0, body.mass_sig)
        M_s  = parent.mass_nom + rng.gauss(0.0, parent.mass_sig)
        # Guard against unphysical negative masses (extremely unlikely
        # given the tiny sigma-to-mean ratios, but defensive).
        if m_s <= 0 or M_s <= 0:
            continue
        results[i] = soi_radius(body.a, m_s, M_s, G_s)

    # Drop any zeros from skipped trials (shouldn't happen in practice).
    vals = [v for v in results if v > 0.0] or results
    if len(vals) < 2:
        raise RuntimeError("Too few valid samples.")

    mean   = statistics.fmean(vals)
    median = statistics.median(vals)
    stdev  = statistics.pstdev(vals) if len(vals) > 1_000_000 else statistics.stdev(vals)

    # Percentiles via nearest-rank
    s = sorted(vals)
    def pct(p: float) -> float:
        k = (len(s) - 1) * p
        f = int(k)
        c = min(f + 1, len(s) - 1)
        if f == c:
            return s[f]
        return s[f] + (s[c] - s[f]) * (k - f)

    p02_5  = pct(0.025)        #  2.5  %  -> -2 sigma
    p16    = pct(0.16)         # 16    %  -> -1 sigma
    p84    = pct(0.84)         # 84    %  -> +1 sigma
    p97_5  = pct(0.975)        # 97.5  %  -> +2 sigma

    nominal = soi_radius(body.a, body.mass_nom, parent.mass_nom)

    return {
        "name":     body_name,
        "parent":   body.parent,
        "n":        len(vals),
        "nominal_km": nominal / KM,
        "mean_km":    mean / KM,
        "median_km":  median / KM,
        "std_km":     stdev / KM,
        "p02_5_km":   p02_5 / KM,
        "p16_km":     p16 / KM,
        "p84_km":     p84 / KM,
        "p97_5_km":   p97_5 / KM,
        "sigma_km":   (p84 - p16) / 2.0 / KM,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def print_summary(results: list[dict[str, float]]) -> None:
    w = 10
    print(f"\n{'Body':<10}{'Parent':<8}{'SOI mean (km)':>20}"
          f"{'+/- 1sigma (km)':>20}{'95% CI (km)':>32}{'sigma %':>10}")
    print("-" * 100)
    for r in results:
        lo95  = r['p02_5_km']
        hi95  = r['p97_5_km']
        rel   = r['sigma_km'] / r['mean_km'] * 100.0
        print(f"{r['name']:<10}{r['parent']:<8}{r['mean_km']:>20,.0f}"
              f"{r['sigma_km']:>20,.3f}"
              f"{lo95:>14,.0f} - {hi95:<14,.0f}{rel:>10.5f}")

    print("\nDistributions (sorted by relative uncertainty):")
    print(f"{'Body':<10}{'Nominal (km)':>18}{'Mean (km)':>18}"
          f"{'Shift (km)':>14}{'1-sigma (km)':>16}")
    print("-" * 76)
    for r in sorted(results, key=lambda d: d['sigma_km'] / d['mean_km']):
        nominal = r['nominal_km']
        mean    = r['mean_km']
        shift   = mean - nominal
        sign    = "+" if shift >= 0 else ""
        print(f"{r['name']:<10}{nominal:>18,.0f}{mean:>18,.0f}"
              f"{sign + f'{shift:,.3f}':>14}{r['sigma_km']:>16,.3f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Monte-Carlo uncertainty propagation for SOI radii.")
    ap.add_argument("-n", "--trials", type=int, default=500_000,
                    help="number of Monte-Carlo trials (default 500 000)")
    ap.add_argument("-b", "--body", action="append", metavar="NAME",
                    help="bodies to compute (repeatable); default: all planets")
    ap.add_argument("-s", "--seed", type=int, default=None,
                    help="random seed for reproducibility")
    args = ap.parse_args()

    names = args.body or [b for b in BODIES if b != "Sun" and BODIES[b].parent == "Sun"]

    print(f"Monte-Carlo SOI propagation: {args.trials:,} trials per body")
    print(f"G = {G_NOM:.5e} +/- {G_SIG:.2e} m^3 kg^-1 s^-2  (1-sigma)\n")

    results: list[dict[str, float]] = []
    for name in names:
        *_, key = next(((i, k) for i, k in enumerate(BODIES)
                        if k.lower() == name.lower()), (None, None, None, None))
        if key is None:
            print(f"Warning: unknown body {name!r}, skipping.", file=sys.stderr)
            continue
        r = monte_carlo_soi(key, args.trials, seed=args.seed)
        results.append(r)

    if not results:
        raise SystemExit("No valid bodies selected.")

    print_summary(results)


if __name__ == "__main__":
    main()
