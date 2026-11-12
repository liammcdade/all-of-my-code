"""
IAU 2003 working definition of an extrasolar "planet".

An object counts as an exoplanet if ALL of the following hold:

  1. True mass < limiting mass for thermonuclear fusion of deuterium
     (~13 M_Jup for solar-metallicity objects).
  2. It orbits a star, a brown dwarf, or a stellar remnant.
  3. Its mass ratio with the central object is below the L4/L5
     stability threshold:  M / M_central  <  2 / (25 + sqrt(621))  ~= 0.04006

Formation mechanism is irrelevant under this definition.

The report now leads with the exoplanet verdict — i.e. the answer to
"would this object count as an exoplanet if it were NOT in the Solar
System?" — and, for solar-system objects, adds a note that their local
designation (planet / dwarf planet / small body) follows the separate
IAU 2006 definition, not these criteria.

Masses can be supplied in Jupiter, Earth, Solar, kilogram, or Pluto units,
and are always also reported in Pluto masses (M_Pluto = 1.303e22 kg).
"""

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Physical constants (SI)
# ---------------------------------------------------------------------------
M_JUP_KG   = 1.89813e27     # Jupiter mass
M_SUN_KG   = 1.98892e30     # Solar mass
M_EARTH_KG = 5.9722e24      # Earth mass
M_PLUTO_KG = 1.303e22       # Pluto mass  ( ~0.00218 M_Earth )

# ---------------------------------------------------------------------------
# Definition constants
# ---------------------------------------------------------------------------
DEUTERIUM_BURNING_LIMIT_MJUP = 13.0                 # for solar metallicity
L4_L5_THRESHOLD = 2.0 / (25.0 + math.sqrt(621.0))   # ≈ 0.040064

VALID_PRIMARY_TYPES = {"star", "brown_dwarf", "stellar_remnant"}


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------
def to_kg(mass, unit="mjup"):
    """Convert a mass in the given unit to kilograms."""
    unit = unit.lower()
    factors = {
        "kg":      1.0,
        "mjup":    M_JUP_KG,
        "jupiter": M_JUP_KG,
        "mearth":  M_EARTH_KG,
        "earth":   M_EARTH_KG,
        "msun":    M_SUN_KG,
        "solar":   M_SUN_KG,
        "mpluto":  M_PLUTO_KG,
        "pluto":   M_PLUTO_KG,
    }
    if unit not in factors:
        raise ValueError(f"Unknown mass unit: {unit!r}")
    return mass * factors[unit]


def to_mjup(mass, unit="mjup"):
    return to_kg(mass, unit) / M_JUP_KG


def to_mpluto(mass, unit="mjup"):
    return to_kg(mass, unit) / M_PLUTO_KG


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------
@dataclass
class Classification:
    name: str
    is_exoplanet: bool
    mass_mjup: float
    mass_mpluto: float
    central_mass_msun: float
    central_mass_mpluto: float
    mass_ratio: float
    deuterium_limit_mjup: float
    deuterium_limit_mpluto: float
    in_solar_system: bool
    reasons: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core classifier
# ---------------------------------------------------------------------------
def classify_object(
    name,
    mass,
    central_mass,
    central_type,
    mass_unit="mjup",
    central_mass_unit="msun",
    deuterium_limit_mjup=DEUTERIUM_BURNING_LIMIT_MJUP,
    in_solar_system=False,
):
    """
    Classify an object under the IAU 2003 working definition of an exoplanet.

    Parameters
    ----------
    name : str
        Label for the object.
    mass : float
        True mass of the candidate (in `mass_unit`).
    central_mass : float
        Mass of the central object (in `central_mass_unit`).
    central_type : str
        One of "star", "brown_dwarf", "stellar_remnant" (or "none" for a
        free-floating object).
    mass_unit, central_mass_unit : str
        "mjup", "mearth", "msun", "mpluto", or "kg".
    deuterium_limit_mjup : float
        D-burning limit. 13 M_Jup for solar metallicity; override for other
        metallicities.
    in_solar_system : bool
        If True, the object is actually a Solar-System body, and the report
        adds a note clarifying that its local designation (planet / dwarf
        planet / small body) follows the separate IAU 2006 definition.
    """
    mass_kg = to_kg(mass, mass_unit)
    central_kg = to_kg(central_mass, central_mass_unit)

    mass_mjup = mass_kg / M_JUP_KG
    mass_mpluto = mass_kg / M_PLUTO_KG
    central_msun = central_kg / M_SUN_KG
    central_mpluto = central_kg / M_PLUTO_KG
    limit_mpluto = deuterium_limit_mjup * (M_JUP_KG / M_PLUTO_KG)

    reasons = []
    is_exoplanet = True

    # Criterion 1 — below the deuterium-burning limit
    if mass_mjup < deuterium_limit_mjup:
        reasons.append(
            f"PASS mass: {mass_mjup:.4g} M_Jup "
            f"({mass_mpluto:.3g} M_Pluto) < {deuterium_limit_mjup:.4g} M_Jup "
            f"({limit_mpluto:.3g} M_Pluto) D-burning limit"
        )
    else:
        is_exoplanet = False
        reasons.append(
            f"FAIL mass: {mass_mjup:.4g} M_Jup "
            f"({mass_mpluto:.3g} M_Pluto) >= {deuterium_limit_mjup:.4g} M_Jup "
            f"({limit_mpluto:.3g} M_Pluto) D-burning limit "
            f"(object is a brown dwarf / star)"
        )

    # Criterion 2 — orbits a star, brown dwarf, or stellar remnant
    if central_type in VALID_PRIMARY_TYPES:
        reasons.append(f"PASS primary: orbits a {central_type}")
    else:
        is_exoplanet = False
        reasons.append(
            f"FAIL primary: central object type {central_type!r} is not "
            f"one of {sorted(VALID_PRIMARY_TYPES)} (free-floating objects "
            f"are not exoplanets under this definition)"
        )

    # Criterion 3 — mass ratio below the L4/L5 instability threshold
    if central_kg > 0:
        ratio = mass_kg / central_kg
        if ratio < L4_L5_THRESHOLD:
            reasons.append(
                f"PASS mass ratio: {ratio:.4g} < {L4_L5_THRESHOLD:.6g} "
                f"(L4/L5 instability)"
            )
        else:
            is_exoplanet = False
            reasons.append(
                f"FAIL mass ratio: {ratio:.4g} >= {L4_L5_THRESHOLD:.6g} "
                f"(system is a binary, not a planet + primary)"
            )
    else:
        ratio = float("inf")
        is_exoplanet = False
        reasons.append(
            "FAIL mass ratio: no central object (free-floating); ratio undefined"
        )

    return Classification(
        name=name,
        is_exoplanet=is_exoplanet,
        mass_mjup=mass_mjup,
        mass_mpluto=mass_mpluto,
        central_mass_msun=central_msun,
        central_mass_mpluto=central_mpluto,
        mass_ratio=ratio,
        deuterium_limit_mjup=deuterium_limit_mjup,
        deuterium_limit_mpluto=limit_mpluto,
        in_solar_system=in_solar_system,
        reasons=reasons,
    )


def report(c: Classification) -> str:
    verdict = (
        "WOULD COUNT AS AN EXOPLANET"
        if c.is_exoplanet
        else "WOULD NOT COUNT AS AN EXOPLANET"
    )
    lines = [
        f"{c.name}:",
        f"  exoplanet status (if NOT in the Solar System): {verdict}",
    ]
    if c.in_solar_system:
        lines.append(
            "    note: this object is currently IN the Solar System — its local "
            "designation (planet / dwarf planet / small body) is governed by the "
            "separate IAU 2006 definition, not by the exoplanet criteria above."
        )
    lines += [
        f"  mass               : {c.mass_mjup:.4g} M_Jup  "
        f"= {c.mass_mpluto:.4g} M_Pluto",
        f"  central mass       : {c.central_mass_msun:.4g} M_Sun  "
        f"= {c.central_mass_mpluto:.4g} M_Pluto",
        f"  mass ratio         : {c.mass_ratio:.4g}",
        f"  L4/L5 threshold    : {L4_L5_THRESHOLD:.6g}",
        f"  D-burning limit    : {c.deuterium_limit_mjup:.4g} M_Jup  "
        f"= {c.deuterium_limit_mpluto:.4g} M_Pluto",
        "  criteria:",
    ]
    lines += [f"    - {r}" for r in c.reasons]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Handy reference: what a Pluto-mass object looks like in other units
# ---------------------------------------------------------------------------
def print_pluto_reference():
    print("Pluto mass reference:")
    print(f"  1 M_Pluto = {M_PLUTO_KG:.4g} kg")
    print(f"           = {M_PLUTO_KG / M_EARTH_KG:.4g} M_Earth")
    print(f"           = {M_PLUTO_KG / M_JUP_KG:.4g} M_Jup")
    print(f"           = {M_PLUTO_KG / M_SUN_KG:.4g} M_Sun")
    print(f"  13 M_Jup  = {13.0 * M_JUP_KG / M_PLUTO_KG:.4g} M_Pluto "
          f"(D-burning limit)")
    print()


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"L4/L5 threshold = 2/(25+sqrt(621)) = {L4_L5_THRESHOLD:.8f}\n")
    print_pluto_reference()

    cases = [
        dict(name="51 Peg b", mass=0.47, central_mass=1.0, central_type="star"),
        dict(name="BD + planet", mass=3.0, central_mass=75.0,
             central_type="brown_dwarf"),
        dict(name="Massive companion", mass=20.0, central_mass=1.0,
             central_type="star"),
        dict(name="Binary-like pair", mass=5.0, central_mass=15.0,
             central_type="brown_dwarf"),
        dict(name="PSR B1257+12 b", mass=0.0006, central_mass=1.4,
             central_type="stellar_remnant", mass_unit="mearth"),
        dict(name="Free floater", mass=5.0, central_mass=0.0,
             central_type="none"),
        dict(name="Pluto-mass world around another star", mass=1.0,
             central_mass=1.0, central_type="star", mass_unit="mpluto"),
        dict(name="Pluto (as it actually is, in our Solar System)", mass=1.0,
             central_mass=1.0, central_type="star", mass_unit="mpluto",
             in_solar_system=True),
    ]

    for kw in cases:
        print(report(classify_object(**kw)))
        print()