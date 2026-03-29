"""Moon Mission Launcher with integrated weather risk assessment module.

Fetches real-time weather data for Kennedy Space Center and evaluates
launch commit criteria (LCC) to produce a GO / NO-GO recommendation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LAUNCH_SITE_NAME: str = "Kennedy Space Center"
LAUNCH_SITE_LAT: float = 28.4058
LAUNCH_SITE_LON: float = -80.6048
LAUNCH_DATE: str = "2026-04-01"
LAUNCH_TIME_LOCAL: str = "17:38"  # 5:38 PM local (EDT = UTC-4)

# Scrub-probability threshold at or above which we recommend NO-GO.
SCRUB_THRESHOLD_PCT: float = 40.0

# Launch Commit Criteria thresholds (NASA / SpaceX style)
@dataclass(frozen=True)
class LaunchCommitCriteria:
    """Thresholds derived from NASA/SpaceX launch commit criteria."""
    max_sustained_surface_wind_knots: float = 30.0
    max_precipitation_probability_pct: float = 60.0
    max_cloud_cover_pct: float = 80.0
    min_temperature_f: float = 41.0
    max_temperature_f: float = 99.0
    lightning_radius_nm: float = 10.0
    min_visibility_sm: float = 6.0  # statute miles


LCC = LaunchCommitCriteria()

# Relative weight of each factor toward the final scrub probability.
# Weights need not sum to 1 — they are normalised internally.
RISK_WEIGHTS: dict[str, float] = {
    "wind": 0.20,
    "precipitation": 0.15,
    "cloud_cover": 0.15,
    "temperature": 0.10,
    "lightning": 0.25,
    "visibility": 0.15,
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class WeatherSnapshot:
    """A single point-in-time weather observation at the launch site."""
    timestamp: datetime
    temperature_c: float
    wind_speed_knots: float
    cloud_cover_pct: float
    precipitation_probability_pct: float
    rain_mm: float
    # Open-Meteo free tier does not provide lightning or visibility directly.
    # These are estimated from available data with conservative defaults.
    lightning_within_10nm: bool = False
    visibility_sm: float = 10.0  # default: good visibility

    @property
    def temperature_f(self) -> float:
        return self.temperature_c * 9.0 / 5.0 + 32.0


@dataclass
class RiskBreakdown:
    """Per-factor risk scores (0-1 each) and whether the factor violates LCC."""
    wind: float = 0.0
    precipitation: float = 0.0
    cloud_cover: float = 0.0
    temperature: float = 0.0
    lightning: float = 0.0
    visibility: float = 0.0
    violations: list[str] = field(default_factory=list)

    def weighted_score(self) -> float:
        """Return a normalised weighted risk score between 0 and 1."""
        total_weight = sum(RISK_WEIGHTS.values())
        weighted = (
            self.wind * RISK_WEIGHTS["wind"]
            + self.precipitation * RISK_WEIGHTS["precipitation"]
            + self.cloud_cover * RISK_WEIGHTS["cloud_cover"]
            + self.temperature * RISK_WEIGHTS["temperature"]
            + self.lightning * RISK_WEIGHTS["lightning"]
            + self.visibility * RISK_WEIGHTS["visibility"]
        )
        return weighted / total_weight if total_weight else 0.0


# ---------------------------------------------------------------------------
# Weather data acquisition
# ---------------------------------------------------------------------------

def fetch_weather_data(
    lat: float = LAUNCH_SITE_LAT,
    lon: float = LAUNCH_SITE_LON,
    date: str = LAUNCH_DATE,
) -> Optional[pd.DataFrame]:
    """Fetch hourly weather data from the Open-Meteo API.

    Returns a DataFrame with hourly records or *None* on failure.
    """
    try:
        cache_session = requests_cache.CachedSession(
            ".cache", expire_after=3600
        )
        retry_session = retry(
            cache_session, retries=5, backoff_factor=0.2
        )
        client = openmeteo_requests.Client(session=retry_session)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m",
                "wind_speed_10m",
                "cloud_cover",
                "rain",
                "precipitation",
                "precipitation_probability",
                "visibility",
            ],
            "start_date": date,
            "end_date": date,
            "timezone": "America/New_York",
        }
        responses = client.weather_api(url, params=params)
        response = responses[0]

        hourly = response.Hourly()
        time_index = pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )

        df = pd.DataFrame({"date": time_index})
        var_names = [
            "temperature_2m",
            "wind_speed_10m",
            "cloud_cover",
            "rain",
            "precipitation",
            "precipitation_probability",
            "visibility",
        ]
        for i, name in enumerate(var_names):
            df[name] = hourly.Variables(i).ValuesAsNumpy()

        return df

    except Exception as exc:
        print(f"[ERROR] Failed to fetch weather data: {exc}")
        return None


# ---------------------------------------------------------------------------
# Snapshot extraction
# ---------------------------------------------------------------------------

def extract_snapshot(
    df: pd.DataFrame, target_hour: int = 17
) -> Optional[WeatherSnapshot]:
    """Extract a WeatherSnapshot for the hour closest to *target_hour* UTC.

    Kennedy Space Center is EDT (UTC-4), so 5:38 PM local = 21:38 UTC.
    """
    # 17:38 EDT = 21:38 UTC
    target_utc_hour = target_hour + 4  # EDT offset
    if df is None or df.empty:
        return None

    df = df.copy()
    df["hour_utc"] = df["date"].dt.hour
    closest_idx = (df["hour_utc"] - target_utc_hour).abs().idxmin()
    row = df.loc[closest_idx]

    wind_knots = float(row["wind_speed_10m"]) * 1.94384  # m/s -> knots

    # Visibility is in metres from Open-Meteo; convert to statute miles.
    vis_m = float(row["visibility"]) if not np.isnan(row["visibility"]) else 16093.0
    vis_sm = vis_m / 1609.34

    # Lightning proxy: heavy rain + high cloud cover suggests convective activity.
    rain_mm = float(row["rain"]) if not np.isnan(row["rain"]) else 0.0
    cloud = float(row["cloud_cover"]) if not np.isnan(row["cloud_cover"]) else 0.0
    lightning_flag = rain_mm > 2.0 and cloud > 70.0

    return WeatherSnapshot(
        timestamp=row["date"].to_pydatetime(),
        temperature_c=float(row["temperature_2m"]),
        wind_speed_knots=wind_knots,
        cloud_cover_pct=cloud,
        precipitation_probability_pct=float(
            row["precipitation_probability"]
        )
        if not np.isnan(row["precipitation_probability"])
        else 0.0,
        rain_mm=rain_mm,
        lightning_within_10nm=lightning_flag,
        visibility_sm=vis_sm,
    )


# ---------------------------------------------------------------------------
# Risk scoring model
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def assess_risk(snapshot: WeatherSnapshot) -> RiskBreakdown:
    """Evaluate each weather parameter against LCC thresholds.

    Each sub-score is in [0, 1] where 1 means the parameter is at or beyond
    the hard-fail threshold and 0 means it is well within acceptable limits.
    """
    breakdown = RiskBreakdown()

    # --- Wind ---------------------------------------------------------------
    # Warning zone below hard limit: 0% at warning_wind, 100% at hard limit.
    warning_wind = 20.0
    breakdown.wind = _clamp(
        (snapshot.wind_speed_knots - warning_wind)
        / (LCC.max_sustained_surface_wind_knots - warning_wind)
    )
    if snapshot.wind_speed_knots > LCC.max_sustained_surface_wind_knots:
        breakdown.violations.append(
            f"Wind {snapshot.wind_speed_knots:.1f} kt > "
            f"{LCC.max_sustained_surface_wind_knots:.0f} kt limit"
        )

    # --- Precipitation probability -----------------------------------------
    breakdown.precipitation = _clamp(
        snapshot.precipitation_probability_pct / LCC.max_precipitation_probability_pct
    )
    if snapshot.precipitation_probability_pct > LCC.max_precipitation_probability_pct:
        breakdown.violations.append(
            f"Precip probability {snapshot.precipitation_probability_pct:.0f}% > "
            f"{LCC.max_precipitation_probability_pct:.0f}% limit"
        )

    # --- Cloud cover --------------------------------------------------------
    warning_cloud = 50.0
    breakdown.cloud_cover = _clamp(
        (snapshot.cloud_cover_pct - warning_cloud)
        / (LCC.max_cloud_cover_pct - warning_cloud)
    )
    if snapshot.cloud_cover_pct > LCC.max_cloud_cover_pct:
        breakdown.violations.append(
            f"Cloud cover {snapshot.cloud_cover_pct:.0f}% > "
            f"{LCC.max_cloud_cover_pct:.0f}% limit"
        )

    # --- Temperature --------------------------------------------------------
    temp_f = snapshot.temperature_f
    if temp_f < LCC.min_temperature_f:
        breakdown.temperature = _clamp((LCC.min_temperature_f - temp_f) / 20.0)
        breakdown.violations.append(
            f"Temperature {temp_f:.1f}°F < {LCC.min_temperature_f:.0f}°F limit"
        )
    elif temp_f > LCC.max_temperature_f:
        breakdown.temperature = _clamp((temp_f - LCC.max_temperature_f) / 20.0)
        breakdown.violations.append(
            f"Temperature {temp_f:.1f}°F > {LCC.max_temperature_f:.0f}°F limit"
        )
    else:
        breakdown.temperature = 0.0

    # --- Lightning ----------------------------------------------------------
    if snapshot.lightning_within_10nm:
        breakdown.lightning = 1.0
        breakdown.violations.append(
            f"Lightning detected within {LCC.lightning_radius_nm:.0f} nm"
        )
    else:
        # Partial risk when convective indicators are present but not confirmed.
        convective_hint = _clamp(snapshot.rain_mm / 5.0) * _clamp(snapshot.cloud_cover_pct / 100.0)
        breakdown.lightning = convective_hint * 0.4

    # --- Visibility ---------------------------------------------------------
    if snapshot.visibility_sm < LCC.min_visibility_sm:
        breakdown.visibility = _clamp(
            1.0 - snapshot.visibility_sm / LCC.min_visibility_sm
        )
        breakdown.violations.append(
            f"Visibility {snapshot.visibility_sm:.1f} sm < "
            f"{LCC.min_visibility_sm:.0f} sm limit"
        )
    else:
        breakdown.visibility = 0.0

    return breakdown


# ---------------------------------------------------------------------------
# Scrub probability & GO / NO-GO decision
# ---------------------------------------------------------------------------

def calculate_scrub_probability(breakdown: RiskBreakdown) -> float:
    """Convert a RiskBreakdown into a single scrub probability (0-100%)."""
    return round(breakdown.weighted_score() * 100.0, 1)


def go_nogo_recommendation(
    scrub_probability: float,
    breakdown: RiskBreakdown,
    snapshot: WeatherSnapshot,
) -> str:
    """Return a formatted GO / NO-GO recommendation string."""
    hard_violation = bool(breakdown.violations)

    if hard_violation:
        decision = "NO-GO"
    elif scrub_probability >= SCRUB_THRESHOLD_PCT:
        decision = "NO-GO"
    else:
        decision = "GO"

    lines = [
        "=" * 60,
        "  WEATHER RISK ASSESSMENT — LAUNCH COMMIT CRITERIA",
        "=" * 60,
        f"  Launch site  : {LAUNCH_SITE_NAME}",
        f"  Launch window: {LAUNCH_DATE} {LAUNCH_TIME_LOCAL} local (EDT)",
        f"  Data time    : {snapshot.wind_speed_knots:.1f} kt wind at assessed hour",
        "-" * 60,
        "  RISK FACTOR BREAKDOWN",
        "-" * 60,
        f"    Wind .............. {breakdown.wind * 100:5.1f}%",
        f"    Precipitation ..... {breakdown.precipitation * 100:5.1f}%",
        f"    Cloud cover ....... {breakdown.cloud_cover * 100:5.1f}%",
        f"    Temperature ....... {breakdown.temperature * 100:5.1f}%",
        f"    Lightning ......... {breakdown.lightning * 100:5.1f}%",
        f"    Visibility ........ {breakdown.visibility * 100:5.1f}%",
        "-" * 60,
        f"  COMBINED SCRUB PROBABILITY: {scrub_probability:.1f}%",
        f"  SCRUB THRESHOLD         : {SCRUB_THRESHOLD_PCT:.1f}%",
        "-" * 60,
    ]
    if breakdown.violations:
        lines.append("  LCC VIOLATIONS:")
        for v in breakdown.violations:
            lines.append(f"    * {v}")
        lines.append("-" * 60)

    lines.append(f"  >>> RECOMMENDATION: {decision} <<<")
    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Launch countdown integration
# ---------------------------------------------------------------------------

def run_pre_launch_weather_assessment() -> tuple[float, RiskBreakdown, Optional[WeatherSnapshot]]:
    """Fetch weather, assess risk, and return (scrub_probability, breakdown, snapshot).

    Falls back to a conservative estimate if weather data is unavailable.
    """
    print(f"\n[INFO] Fetching weather data for {LAUNCH_SITE_NAME} "
          f"on {LAUNCH_DATE}...")

    df = fetch_weather_data()
    if df is None:
        print("[WARN] Weather data unavailable. Defaulting to conservative "
              "scrub estimate (80%).")
        conservative = RiskBreakdown(
            wind=0.5,
            precipitation=0.5,
            cloud_cover=0.5,
            temperature=0.0,
            lightning=0.8,
            visibility=0.5,
            violations=["Weather data unavailable — conservative estimate used"],
        )
        return 80.0, conservative, None

    snapshot = extract_snapshot(df, target_hour=17)
    if snapshot is None:
        print("[WARN] Could not extract weather snapshot. Defaulting to "
              "conservative scrub estimate (80%).")
        conservative = RiskBreakdown(
            wind=0.5,
            precipitation=0.5,
            cloud_cover=0.5,
            temperature=0.0,
            lightning=0.8,
            visibility=0.5,
            violations=["Snapshot extraction failed — conservative estimate used"],
        )
        return 80.0, conservative, None

    print(f"[INFO] Weather snapshot at {snapshot.timestamp:%Y-%m-%d %H:%M} UTC")
    print(f"       Temperature : {snapshot.temperature_f:.1f}°F "
          f"({snapshot.temperature_c:.1f}°C)")
    print(f"       Wind speed  : {snapshot.wind_speed_knots:.1f} kt")
    print(f"       Cloud cover : {snapshot.cloud_cover_pct:.0f}%")
    print(f"       Precip prob : {snapshot.precipitation_probability_pct:.0f}%")
    print(f"       Visibility  : {snapshot.visibility_sm:.1f} sm")

    breakdown = assess_risk(snapshot)
    scrub_probability = calculate_scrub_probability(breakdown)
    return scrub_probability, breakdown, snapshot


def launch_countdown() -> None:
    """Simulate a launch countdown with integrated weather assessment."""
    print("\n" + "#" * 60)
    print("#          MOON MISSION LAUNCHER — PRE-LAUNCH SEQUENCE          #")
    print("#" * 60)

    # Phase 1: Weather assessment
    scrub_probability, breakdown, snapshot = run_pre_launch_weather_assessment()

    # Build a fallback snapshot for the report if data was unavailable.
    if snapshot is None:
        snapshot = WeatherSnapshot(
            timestamp=datetime.utcnow(),
            temperature_c=0.0,
            wind_speed_knots=0.0,
            cloud_cover_pct=0.0,
            precipitation_probability_pct=0.0,
            rain_mm=0.0,
        )

    report = go_nogo_recommendation(scrub_probability, breakdown, snapshot)
    print("\n" + report)

    hard_violation = bool(breakdown.violations)
    if scrub_probability >= SCRUB_THRESHOLD_PCT or hard_violation:
        print("\n[ACTION] Launch SCRUBBED due to weather conditions.")
        print("         Re-evaluate for the next available window.")
        return

    # Phase 2: Proceed with countdown
    print("\n[INFO] Weather GO. Proceeding with countdown sequence...")
    for t in range(10, 0, -1):
        print(f"  T-minus {t}...")
    print("\n  *** LIFTOFF ***\n")
    print("  Moon mission is underway. Godspeed!\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    launch_countdown()