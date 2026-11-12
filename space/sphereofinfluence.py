#!/usr/bin/env python3
"""
Sphere of Influence (SOI) calculator for the planets and the Moon.

Formula (Hill / Laplace "gravisphere"):

    r_SOI = a * (m / M) ** (2/5)

    a : semi-major axis of the small body's orbit around its parent
    m : mass of the small body
    M : mass of the parent body

A more accurate, direction-dependent form is also implemented:

    r_SOI(theta) = a * (m/M)**(2/5) / (1 + 3*cos(theta)**2 / 10)

where theta is the angle measured from the direction of the massive body.

Usage:
    python soi.py                 # table for all bodies
    python soi.py -b Jupiter      # details for one body
    python soi.py -b Moon -b Mars # details for several bodies
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
AU = 1.495978707e11          # m
KM = 1.0e3                   # m
KM_PER_AU = AU / KM
MI_PER_KM = 0.621371192


# --------------------------------------------------------------------------
# Solar-system data (SI units)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Body:
    name: str
    mass: float                    # kg
    radius: float                  # m (mean radius)
    parent: str | None = None      # name of the body it orbits
    a: float | None = None         # m, semi-major axis w.r.t. `parent`
    soi_ref: float | None = None   # m, value quoted in the reference table


BODIES: dict[str, Body] = {
    "Sun":     Body("Sun",     1.98847e30, 6.957e8),
    "Mercury": Body("Mercury", 3.3011e23,  2.4397e6, "Sun",   57.909e9,  0.117e9),
    "Venus":   Body("Venus",   4.8675e24,  6.0518e6, "Sun",  108.209e9,  0.616e9),
    "Earth":   Body("Earth",   5.97237e24, 6.3710e6, "Sun",  149.598e9,  0.929e9),
    "Moon":    Body("Moon",    7.346e22,   1.7374e6, "Earth", 384.4e6,   0.0643e9),
    "Mars":    Body("Mars",    6.4171e23,  3.3895e6, "Sun",  227.92e9,   0.578e9),
    "Jupiter": Body("Jupiter", 1.8982e27,  6.9911e7, "Sun",  778.57e9,   48.2e9),
    "Saturn":  Body("Saturn",  5.6834e26,  5.8232e7, "Sun", 1433.53e9,   54.5e9),
    "Uranus":  Body("Uranus",  8.6810e25,  2.5362e7, "Sun", 2872.46e9,   51.9e9),
    "Neptune": Body("Neptune", 1.02413e26, 2.4622e7, "Sun", 4495.06e9,   86.2e9),
}


# --------------------------------------------------------------------------
# Core physics
# --------------------------------------------------------------------------
def soi_radius(a: float, m: float, M: float) -> float:
    """Classic SOI radius r = a (m/M)^(2/5).  All SI, returns metres."""
    return a * (m / M) ** 0.4


def soi_angular(a: float, m: float, M: float, theta: float) -> float:
    """Direction-dependent SOI radius.

    `theta` (radians) is measured from the direction of the massive body.
    """
    return soi_radius(a, m, M) / (1.0 + 0.3 * math.cos(theta) ** 2)


def soi_mean_numeric(a: float, m: float, M: float, n: int = 20001) -> float:
    """SOI radius averaged over all directions (numerical integration)."""
    base = soi_radius(a, m, M)
    dtheta = math.pi / (n - 1)
    total = 0.0
    for i in range(n):
        th = i * dtheta
        w = 0.5 if i in (0, n - 1) else 1.0          # trapezoidal rule
        total += w * math.sin(th) / (1.0 + 0.3 * math.cos(th) ** 2)
    return base * 0.5 * total * dtheta


def soi(body: "Body | str") -> float:
    """SOI radius (metres) of a named body, relative to its parent."""
    if isinstance(body, str):
        try:
            body = BODIES[body]
        except KeyError:
            raise SystemExit(f"Unknown body {body!r}. "
                             f"Known: {', '.join(BODIES)}") from None
    if body.parent is None:
        raise ValueError(f"{body.name} has no parent body - SOI is undefined.")
    parent = BODIES[body.parent]
    return soi_radius(body.a, body.mass, parent.mass)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def print_table() -> None:
    hdr = (f"{'Body':<9}{'Parent':<8}{'SOI (km)':>15}{'SOI (mi)':>15}"
           f"{'SOI (AU)':>11}{'SOI (R)':>10}{'ref (km)':>14}{'err %':>9}")
    print(hdr)
    print("-" * len(hdr))
    for b in BODIES.values():
        if b.parent is None:
            continue
        r = soi(b)
        r_km, r_mi = r / KM, r / KM * MI_PER_KM
        ref = b.soi_ref
        err = f"{(r - ref) / ref * 100:+.1f}" if ref else "-"
        ref_s = f"{ref / KM:,.0f}" if ref else "-"
        print(f"{b.name:<9}{b.parent:<8}{r_km:>15,.0f}{r_mi:>15,.0f}"
              f"{r / AU:>11.4f}{r / b.radius:>10.1f}{ref_s:>14}{err:>9}")
    print("\nSOI (R) = SOI expressed in mean radii of the body itself.")


def print_details(name: str) -> None:
    b = BODIES[name]
    if b.parent is None:
        print(f"\n{name}: no parent body -> SOI undefined.")
        return
    p = BODIES[b.parent]
    r = soi(b)

    print(f"\n=== {b.name} (relative to {p.name}) ===")
    print(f"  semi-major axis a : {b.a / KM:>18,.1f} km  "
          f"({b.a / AU:.4f} AU)")
    print(f"  mass m            : {b.mass:>18.5e} kg")
    print(f"  parent mass M     : {p.mass:>18.5e} kg")
    print(f"  mass ratio m/M    : {b.mass / p.mass:>18.5e}")
    print(f"  (m/M)^(2/5)       : {(b.mass / p.mass) ** 0.4:>18.6f}")
    print(f"  --> r_SOI         : {r / KM:>18,.1f} km")
    print(f"                      {r / KM * MI_PER_KM:>18,.1f} mi")
    print(f"                      {r / AU:>18.6f} AU")
    print(f"                      {r / b.radius:>18,.1f} body radii")

    if b.soi_ref:
        print(f"  reference value   : {b.soi_ref / KM:>18,.1f} km "
              f"({(r - b.soi_ref) / b.soi_ref * 100:+.1f} %)")

    print(f"\n  {'theta (deg)':>12}{'r_SOI (km)':>16}{'r_SOI (R)':>12}")
    for deg in range(0, 91, 15):
        th = math.radians(deg)
        ra = soi_angular(b.a, b.mass, p.mass, th)
        print(f"  {deg:>12}{ra / KM:>16,.1f}{ra / b.radius:>12,.1f}")

    mean = soi_mean_numeric(b.a, b.mass, p.mass)
    print(f"\n  mean over all directions: {mean / KM:,.1f} km "
          f"= {mean / r:.4f} x classic value")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Sphere of Influence (SOI) calculator.")
    ap.add_argument("-b", "--body", action="append", metavar="NAME",
                    help="show detailed output for NAME (repeatable)")
    args = ap.parse_args()

    if args.body:
        for name in args.body:
            key = next((k for k in BODIES if k.lower() == name.lower()), None)
            if key is None:
                raise SystemExit(f"Unknown body {name!r}. "
                                 f"Known: {', '.join(BODIES)}")
            print_details(key)
    else:
        print_table()


if __name__ == "__main__":
    main()