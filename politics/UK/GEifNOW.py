"""
Clacton By-Election Predictor

A hybrid predictor combining historical general election results with
by-election precedents and current polling data. All data is loaded
dynamically from CSV files in this directory.

Data sources:
    general_election_results.csv  Historical GE vote shares by constituency
    by_elections.csv              By-election outcomes and causes (1955-present)
    polling_averages.csv          Latest polling averages by party/country
    mps_elected.csv               Seat counts by party (most recent GE)

Usage:
    python uk.py                          Uses latest polling from CSV
    python uk.py --clacton-polls         Uses Clacton-specific estimates below
"""

import argparse
import sys

import numpy as np
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from datetime import date

from tqdm import tqdm

# ─── Paths ────────────────────────────────────────────────────────

ROOT = Path(__file__).parent
GE_RESULTS_PATH = ROOT / "general_election_results.csv"
BY_ELECTIONS_PATH = ROOT / "by_elections.csv"
POLLING_PATH = ROOT / "polling_averages.csv"
MPS_PATH = ROOT / "mps_elected.csv"

# ─── Configuration ────────────────────────────────────────────────

CONFIG: Dict = {
    "constituency": "Clacton",
    "country": "Great Britain",
    "min_year": 2010,
    "hist_weight": 0.30,
    "poll_weight": 0.70,
    "n_simulations": 10_000,
    "uncertainty_factor": 0.08,
    "min_stddev": 1.5,
    "default_baseline": 2.0,
    "penalty_swing_ratio": 0.55,
    "protest_cap": 4.0,
    "turnout_factor": 0.42,
    "blend_alpha": 2.0,  # Beta distribution alpha for blend weight per sim
    "blend_beta": 5.0,   # Beta distribution beta (~mean=0.285, near 0.30 prior)
}

# ─── 2026 Clacton By-Election: Statement of Persons Nominated ─────────
# 34 candidates standing (record-breaking). Major parties (Conservative, Labour,
# Lib Dems, Green) are NOT running. Only Reform UK (Farage) and Count Binface
# have recognizable names. 32 other candidates are Independents/minor parties.
#
# Polling allocation (Survation telephone poll, 502 adults, 16-24 July 2026,
# conducted for Mandate Research, ahead of 13 August by-election):
#   Farage 73%, Binface 20%, Fox 2%, Others 5% (decided voters only)
#   Two-horse race (forced choice): Farage 69%, Binface 31%
# ──────────────────────────────────────────────────────────────────────────

CANDIDATE_LIST_2026: List[Tuple[str, str, float]] = [
    # (candidate_name, party, estimated_share)
    ("Nigel Farage",             "Reform UK",           73.0),
    ("Count Binface",            "Count Binface Party", 20.0),
    ("Laurence Fox",             "The Reclaim Party",    2.0),
    ("William Clouston",         "SDP",                   0.8),
    ("Adham Alkhatip",           "Forward",               0.6),
    ("Martin Davies",            "Freedom Alliance",      0.5),
    ("Andy Erlam",               "Independent",           0.4),
    ("James Ransley",            "Consensus",             0.4),
    ("Daniel Pocock",            "Independent",           0.3),
    ("John Stevens",             "Rejoin EU",             0.3),
    ("Joseph 77",                "Independent",           0.3),
    ("Tony Cane",                "Independent",           0.3),
    ("Rees Cowne",               "Independent",           0.3),
    ("Glenn Cummings",           "Independent",           0.2),
    ("Attieh Fard",              "Independent",           0.2),
    ("Tony Francis",             "Independent",           0.2),
    ("Robin Green",              "Independent",           0.2),
    ("Abi Hookway",              "Independent",           0.2),
    ("Stephen Ingram",           "Independent",           0.2),
    ("Amy Morris",               "Independent",           0.2),
    ("Derrick Morris",           "Independent",           0.2),
    ("Martyn Obrien",            "Independent",           0.2),
    ("Michael O'Keeffe",         "Independent",           0.2),
    ("Nick Pelas",               "Independent",           0.2),
    ("Ketankumar Pipaliya",      "UK Voice",              0.2),
    ("Gerry Smith",              "Independent",           0.1),
    ("Kai Stephens",             "British Democratic",    0.1),
    ("Marcus White",             "Everyone is God",       0.1),
    ("Marc Wilkinson",           "Independent",           0.1),
    ("Nick The Incredible Flying Brick", "Monster Raving Loony", 0.1),
    ("Howling Laud Hope",        "Monster Raving Loony",  0.1),
    ("Baron Von Thunderclap",    "Monster Raving Loony",  0.1),
    ("Woke Trump Carrzee",       "Independent",           0.1),
    ("Pamela Walford",           "Independent",           0.1),
]

# ─── Party Normalisation ──────────────────────────────────────────

_MAJOR_PARTIES: Dict[str, str] = {
    "conservative": "Conservative",
    "tory": "Conservative",
    "labour": "Labour",
    "lib dem": "Liberal Democrats",
    "liberal democrat": "Liberal Democrats",
    "green": "Green",
    "green party": "Green",
    "reform": "Reform UK",
    "reform uk": "Reform UK",
    "ukip": "Reform UK",
    "uk independence": "Reform UK",
    "bnp": "Other",
    "count binface": "Count Binface Party",
    "monster": "Other",
    "loony": "Other",
    "heritage": "Other",
    "climate": "Other",
    "other": "Other",
    "traditional": "Other",
}


def normalize_party(party_name: str) -> str:
    """Normalize party names to a canonical form across CSV sources."""
    p = party_name.lower().strip()
    for alias, canonical in _MAJOR_PARTIES.items():
        if alias in p:
            return canonical
    return party_name


def _candidate_party_from_name(name: str) -> str:
    """Map a candidate name to a canonical party using the 2026 SON list."""
    for cand_name, party, _ in CANDIDATE_LIST_2026:
        if cand_name.lower() in name.lower() or name.lower() in cand_name.lower():
            return normalize_party(party)
    return normalize_party(name)


def candidate_polls_from_list(
    candidate_list: List[Tuple[str, str, float]],
) -> Dict[str, float]:
    """Convert the 2026 SON candidate list into a {name: share} polling dict."""
    return {name: share for name, _, share in candidate_list}


# ─── Data Loading Functions ───────────────────────────────────────

def load_clacton_history(
    csv_path: Path = GE_RESULTS_PATH,
    constituency: str = CONFIG["constituency"],
) -> Dict[int, Dict[str, float]]:
    """
    Load historical general election vote shares for a constituency.

    Returns a dict mapping election_year -> {normalized_party: perc_share}.
    If multiple candidates belong to the same normalized party, shares are summed.
    """
    df = pd.read_csv(csv_path)
    mask = df["constituency_name"].str.contains(constituency, case=False, na=False)
    clacton_df = df[mask & df["perc_share"].notna()].copy()

    history: Dict[int, Dict[str, float]] = {}
    for year in sorted(clacton_df["election_year"].unique()):
        year_df = clacton_df[clacton_df["election_year"] == year]
        history[int(year)] = {}
        for _, row in year_df.iterrows():
            party = normalize_party(str(row["party_name"]))
            share = float(row["perc_share"])
            history[int(year)][party] = history[int(year)].get(party, 0.0) + share
    return history


def load_latest_polling(
    csv_path: Path = POLLING_PATH,
    country: str = CONFIG["country"],
) -> Tuple[Dict[str, float], str]:
    """
    Load the most recent polling averages for a country.

    Returns a tuple of (party -> voting_intention, date_string).
    """
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    latest_date = df["date"].max()
    latest = df[(df["date"] == latest_date) & (df["country_name"] == country)]

    polling = {
        normalize_party(str(row["party_name"])): float(row["voting_intention"])
        for _, row in latest.iterrows()
    }
    return polling, latest_date.strftime("%Y-%m-%d")


def load_governing_party(csv_path: Path = MPS_PATH) -> str:
    """Determine the governing party from the most recent election seat data."""
    df = pd.read_csv(csv_path)
    latest_year = df["election_year"].max()
    latest = df[df["election_year"] == latest_year]
    seat_counts = latest.groupby("winning_party_name").size()
    return str(seat_counts.idxmax())


def compute_gov_defence_penalty(
    by_elections_path: Path = BY_ELECTIONS_PATH,
    ge_results_path: Path = GE_RESULTS_PATH,
    min_year: int = CONFIG["min_year"],
) -> float:
    """
    Compute the average government defence penalty from historical by-elections.

    For each 'Government Defence' by-election since *min_year*, the governing
    party's margin of victory in the preceding general election is computed.
    The penalty is approximately 55% of the average margin — representing the
    typical protest/right-wing swing against the governing party in defensive
    by-elections.

    Returns:
        Float penalty (negative percentage points) or -18.5 if no data available.
    """
    be_df = pd.read_csv(by_elections_path)
    ge_df = pd.read_csv(ge_results_path)

    gov_defence = be_df[
        (be_df["governing_outcome"] == "Government Defence")
        & (be_df["general_election_year"] >= min_year)
    ]
    if len(gov_defence) == 0:
        return -18.5

    margins: List[float] = []
    for _, be_row in gov_defence.iterrows():
        ge_year = be_row["general_election_year"]
        constituency = be_row["constituency_name"]
        governing_party = _normalize_party_from_str(be_row["incumbent_elected_party_name"])

        ge_data = ge_df[
            (ge_df["election_year"] == ge_year)
            & (ge_df["constituency_name"].str.contains(constituency, case=False, na=False))
        ]
        if len(ge_data) == 0:
            continue

        gov_mask = ge_data["party_name"].apply(
            lambda p: normalize_party(str(p)) == governing_party
        )
        gov_shares = ge_data[gov_mask]["perc_share"]
        if len(gov_shares) == 0:
            continue
        gov_share = float(gov_shares.iloc[0])

        sorted_shares = sorted(ge_data["perc_share"].tolist(), reverse=True)
        runner_up = float(sorted_shares[1]) if len(sorted_shares) > 1 else 0.0
        margins.append(gov_share - runner_up)

    if not margins:
        return -18.5

    avg_margin = float(np.mean(margins))
    return round(-(avg_margin * CONFIG["penalty_swing_ratio"]), 1)


def compute_protest_vote_ceiling(polling: Dict[str, float]) -> float:
    """
    Compute the protest vote ceiling from the polling 'Other' category.

    The 'Other' share represents the combined protest/minor-party vote.
    Individual protest candidates are capped at this value (max 4.0%).
    """
    other_share = polling.get("Other", CONFIG["protest_cap"])
    return min(other_share, CONFIG["protest_cap"])


def _normalize_party_from_str(name: str) -> str:
    """Normalize a party name string, handling NaN."""
    if pd.isna(name):
        return "Other"
    return normalize_party(str(name))


# ─── Dataclass ────────────────────────────────────────────────────

@dataclass
class CandidateForecast:
    """Forecast result for a single candidate/party."""
    name: str
    party: str
    base_share: float      # Historical GE baseline (after gov defence penalty)
    adjusted_share: float  # After Bayesian blend + normalisation
    win_probability: float # Monte Carlo derived probability (%)


# ─── Predictor ───────────────────────────────────────────────────

class ClactonByElectionPredictor:
    """
    Hybrid predictor combining historical GE results with by-election
    precedents and current polling data.

    All data is loaded dynamically from CSV files. A Clacton-specific polling
    override can be supplied for more accurate local estimates.
    """

    def __init__(
        self,
        csv_root: Path = ROOT,
        constituency: str = CONFIG["constituency"],
    ):
        self.constituency = constituency
        self.ge_history = load_clacton_history(
            csv_root / "general_election_results.csv", constituency
        )
        self.polling, self.polling_date = load_latest_polling(
            csv_root / "polling_averages.csv"
        )
        self.gov_defence_penalty = compute_gov_defence_penalty(
            csv_root / "by_elections.csv",
            csv_root / "general_election_results.csv",
        )
        self.protest_vote_ceiling = compute_protest_vote_ceiling(self.polling)
        self.governing_party = _normalize_party_from_str(
            load_governing_party(csv_root / "mps_elected.csv")
        )
        self.latest_ge_year = max(self.ge_history.keys()) if self.ge_history else 0

    def predict(
        self,
        current_polls: Optional[Dict[str, float]] = None,
        n_simulations: int = CONFIG["n_simulations"],
    ) -> List[CandidateForecast]:
        """
        Run the full prediction pipeline.

        Args:
            current_polls: Override polling dict {name: share}. If None,
                           uses the 2026 SON candidate list by default.
            n_simulations: Number of Monte Carlo iterations.

        Returns:
            List of CandidateForecast sorted by win probability (descending).
        """
        polls = self._resolve_polls(current_polls)
        candidates = self._blend(polls)
        candidates = self._renormalize(candidates)
        win_probs = self._simulate(candidates, n_simulations)

        return sorted(
            [
                CandidateForecast(
                    name=c["name"],
                    party=c["party"],
                    base_share=c["base_share"],
                    adjusted_share=c["adjusted_share"],
                    win_probability=round(win_probs[i] * 100, 1),
                )
                for i, c in enumerate(candidates)
            ],
            key=lambda f: f.win_probability,
            reverse=True,
        )

    def _resolve_polls(
        self, current_polls: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """Determine which polling data to use."""
        if current_polls is not None and len(current_polls) > 0:
            return current_polls
        if CANDIDATE_LIST_2026 is not None:
            return candidate_polls_from_list(CANDIDATE_LIST_2026)
        return self.polling

    def _blend(self, current_polls: Dict[str, float]) -> List[Dict]:
        """Bayesian blend of historical GE baseline and current polls."""
        total_poll = sum(current_polls.values())
        latest_hist = self.ge_history.get(self.latest_ge_year, {})

        candidates: List[Dict] = []
        for name, poll_share in current_polls.items():
            norm_poll = poll_share / total_poll * 100
            party = _candidate_party_from_name(name)
            baseline = self._compute_baseline(party, name, latest_hist)

            adjusted = (
                CONFIG["hist_weight"] * baseline
                + CONFIG["poll_weight"] * norm_poll
            )

            # No protest cap — let polling data speak freely

            candidates.append({
                "name": name,
                "party": party,
                "base_share": round(baseline, 1),
                "adjusted_share": round(adjusted, 1),
                "baseline": baseline,
                "norm_poll": norm_poll,
            })
        return candidates

    def _compute_baseline(
        self, party: str, name: str, latest_hist: Dict[str, float]
    ) -> float:
        """Compute historical baseline, applying gov defence penalty only to majors."""
        if party == "Independent":
            return 0.0

        if self._is_protest_candidate(name):
            return CONFIG["default_baseline"]

        baseline = latest_hist.get(party, CONFIG["default_baseline"])
        if party == self.governing_party:
            baseline += self.gov_defence_penalty
        return baseline

    def _is_protest_candidate(self, name: str) -> bool:
        """Check if a candidate is a protest/minor-party candidate."""
        n = name.lower()
        return any(kw in n for kw in ("binface", "monster", "loony"))

    @staticmethod
    def _renormalize(candidates: List[Dict]) -> List[Dict]:
        """Normalize adjusted shares so they sum to 100%."""
        total = sum(c["adjusted_share"] for c in candidates)
        if total > 0:
            for c in candidates:
                c["adjusted_share"] = round(c["adjusted_share"] / total * 100, 1)
        return candidates

    def _simulate(self, candidates: List[Dict], n_sims: int) -> np.ndarray:
        """
        Run Monte Carlo simulation for win probabilities.

        Each of the *n_sims* iterations uses a DIFFERENT Bayesian blend weight,
        sampled from a Dirichlet-like distribution centered on the prior weights.
        This captures uncertainty not just in polling, but in the optimal
        historical vs. poll weighting for this specific by-election context.

        Returns:
            Array of win probabilities per candidate (0..1).
        """
        n = len(candidates)
        baselines = np.array([c["baseline"] for c in candidates])
        polls = np.array([c["norm_poll"] for c in candidates])

        # Draw 10,000 different blend weights for historical vs poll share.
        # We use a Beta(2,2) distribution centered on hist_weight=0.30
        # to allow each simulation its own weighting.
        beta_samples = np.random.beta(
            a=CONFIG["blend_alpha"],
            b=CONFIG["blend_beta"],
            size=n_sims,
        )
        hist_weights = beta_samples
        poll_weights = 1.0 - hist_weights

        # Vectorized: for each sim, blend baselines and polls, then add noise
        # Shape: (n_sims, n_candidates)
        adjusted = (
            baselines[np.newaxis, :] * hist_weights[:, np.newaxis]
            + polls[np.newaxis, :] * poll_weights[:, np.newaxis]
        )

        # Apply protest caps (deterministic per candidate)
        for i, c in enumerate(candidates):
            if "binface" in c["name"].lower() or "monster" in c["name"].lower() or "loony" in c["name"].lower():
                adjusted[:, i] = np.minimum(adjusted[:, i], self.protest_vote_ceiling)

        # Normalize each simulation row to sum to 100
        row_sums = adjusted.sum(axis=1, keepdims=True)
        adjusted = adjusted / row_sums * 100.0

        # Add polling noise
        stds = np.maximum(
            adjusted * CONFIG["uncertainty_factor"],
            CONFIG["min_stddev"],
        )
        draws = np.random.normal(adjusted, stds)
        draws = np.maximum(draws, 0)

        winners = np.argmax(draws, axis=1)
        wins = np.bincount(winners, minlength=n)
        return wins / n_sims


# ─── Presentation ─────────────────────────────────────────────────

def format_results(forecasts: List[CandidateForecast], predictor: ClactonByElectionPredictor) -> str:
    """Format forecast results into a display string."""
    lines = [
        "=" * 65,
        "  CLACTON BY-ELECTION WIN PROBABILITY FORECAST",
        "=" * 65,
        f"  Historical GE baseline: {predictor.latest_ge_year} general election",
        f"  Polling source:         Survation (16-24 Jul 2026, n=502)",
        f"  Governing party:        {predictor.governing_party}",
        f"  Gov defence penalty:    {predictor.gov_defence_penalty:+.1f} pp",
        f"  Protest vote ceiling:   {predictor.protest_vote_ceiling:.1f}%",
        "-" * 65,
    ]
    lines.append(
        f"  {'#':>3}  {'Candidate':<28} {'Base%':>6} {'Adj%':>6} {'Win%':>7}  Bar"
    )
    lines.append("-" * 65)
    for i, f in enumerate(forecasts, 1):
        bar = "█" * int(f.win_probability / 2)
        lines.append(
            f"  {i:>3}  {f.name:<28} {f.base_share:>5.1f}% {f.adjusted_share:>5.1f}% "
            f"{f.win_probability:>6.1f}%  {bar}"
        )
    lines.append("-" * 65)
    lines.append(
        f"  Methodology: 30% GE history + 70% current poll (Bayesian blend)"
    )
    lines.append(
        f"  Per-sim weight: Beta({CONFIG['blend_alpha']}, {CONFIG['blend_beta']}) "
        f"→ each of {CONFIG['n_simulations']:,} sims uses different hist/poll weight"
    )
    lines.append(f"  Simulations: {CONFIG['n_simulations']:,} Monte Carlo runs")
    lines.append("=" * 65)
    return "\n".join(lines)


# ─── General Election: If Tomorrow ──────────────────────────────────
#
# Full 650-seat House of Commons simulation.  Uses 2024 GE results as
# the constituency-level baseline and applies a national poll swing to
# project a hypothetical General Election held "tomorrow".
# ─────────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ConstituencyBaseline:
    """2024 GE baseline vote shares for a single constituency."""
    name: str
    parties: Dict[str, float]  # normalized party -> vote share (%)


@dataclass(slots=True)
class HouseOfCommonsResult:
    """Aggregated seat distribution after Monte Carlo simulation."""
    party_seats: Dict[str, float]      # party -> expected seats (mean)
    party_seats_won: Dict[str, int]    # party -> seats won in this run
    total_seats: int
    n_simulations: int
    median_seats: Dict[str, float]     # party -> median seats across sims
    confidence_intervals: Dict[str, Tuple[int, int]]  # party -> (low, high) 95%


GE_CONFIG: Dict = {
    "baseline_year": 2024,
    "next_ge_date": date(2029, 5, 3),
    "n_sims": 5_000,
    "seat_uncertainty": 2.5,    # std dev (percentage points) applied per party per seat
    "swing_smoothing_far": 0.5,     # poll weight far from election (historical heavy)
    "swing_smoothing_near": 0.85,   # poll weight near election (poll heavy)
    "smoothing_ramp_weeks": 4 * 52,  # weeks over which to ramp from far to near (~4 years)
    "regional_variation": 1.8,  # extra noise for smaller parties / independents
    "reference_date": date(2026, 8, 13),  # current reference date for time-weighting
    "major_parties_ge": [
        "Reform UK",
        "Conservative",
        "Labour",
        "Liberal Democrats",
        "Green",
    ],
}

# Parties that appear in 2024 GE data but need renormalisation to canonical names
# Already handled by normalize_party(), but we ensure SNP/Plaid/SDLP/DUP are canonical.


def load_all_constituencies(
    csv_path: Path = GE_RESULTS_PATH,
    baseline_year: int = GE_CONFIG["baseline_year"],
) -> Dict[str, ConstituencyBaseline]:
    """
    Load 2024 general election results for all constituencies.

    Returns a dict mapping constituency_name -> ConstituencyBaseline with
    normalized party names and vote shares summing to ~100%.
    """
    df = pd.read_csv(csv_path)
    ge_df = df[(df["election_year"] == baseline_year) & df["perc_share"].notna()].copy()

    baselines: Dict[str, ConstituencyBaseline] = {}
    for consti_name, group in ge_df.groupby("constituency_name"):
        party_shares: Dict[str, float] = {}
        for _, row in group.iterrows():
            party = normalize_party(str(row["party_name"]))
            share = float(row["perc_share"])
            party_shares[party] = party_shares.get(party, 0.0) + share
        total = sum(party_shares.values())
        if total > 0:
            party_shares = {p: s / total * 100 for p, s in party_shares.items()}
        baselines[str(consti_name)] = ConstituencyBaseline(
            name=str(consti_name), parties=party_shares
        )
    return baselines


def load_national_ge_totals(
    csv_path: Path = GE_RESULTS_PATH,
    baseline_year: int = GE_CONFIG["baseline_year"],
) -> Dict[str, float]:
    """
    Compute national-level 2024 GE vote shares by normalized party.
    """
    df = pd.read_csv(csv_path)
    ge_df = df[(df["election_year"] == baseline_year) & df["perc_share"].notna()].copy()

    ge_df["norm_party"] = ge_df["party_name"].apply(
        lambda p: normalize_party(str(p))
    )
    weighted = ge_df.groupby("norm_party").apply(
        lambda g: np.average(g["perc_share"], weights=g["votes"]),
        include_groups=False,
    )
    totals = {str(p): float(v) for p, v in weighted.items()}
    total = sum(totals.values())
    if total > 0:
        totals = {p: v / total * 100 for p, v in totals.items()}
    return totals


def compute_poll_weight(reference_date: date = GE_CONFIG["reference_date"]) -> float:
    """
    Compute the poll weight as a fraction of time remaining until the next GE.

    Uses a sigmoid-like ramp: far from the election, historical baseline
    carries more weight (poll weight ~0.5); as election day approaches,
    polling data gets stronger weighting (~0.85).  The ramp spans the
    configured number of weeks from the reference date forward.

    Returns a value between swing_smoothing_far and swing_smoothing_near.
    """
    next_ge = GE_CONFIG["next_ge_date"]
    weeks_remaining = max((next_ge - reference_date).days / 7.0, 0)
    ramp_weeks = GE_CONFIG["smoothing_ramp_weeks"]

    # fraction of time elapsed through the ramp period (0 = start, 1 = election day)
    fraction = 1.0 - min(weeks_remaining / ramp_weeks, 1.0) if ramp_weeks > 0 else 0.0
    weight = GE_CONFIG["swing_smoothing_far"] + fraction * (
        GE_CONFIG["swing_smoothing_near"] - GE_CONFIG["swing_smoothing_far"]
    )
    return round(weight, 2)


def blend_poll_and_baseline(
    baseline: ConstituencyBaseline,
    poll_shares: Dict[str, float],
    poll_weight: float,
) -> Dict[str, float]:
    """
    Blend latest polls with the 2024 constituency baseline.

    For each party in the polling data:
        projected = poll_weight * poll_share + (1 - poll_weight) * baseline_share

    For parties only in the baseline (e.g. regional NI parties):
        projected = (1 - poll_weight) * baseline_share

    Parties in poll data but not in baseline are added with their full poll share.

    Result is renormalized to 100%.
    """
    projected: Dict[str, float] = {}
    hist_weight = 1.0 - poll_weight

    for party, baseline_share in baseline.parties.items():
        poll_share = poll_shares.get(party, 0.0)
        projected[party] = hist_weight * baseline_share + poll_weight * poll_share

    for party, poll_share in poll_shares.items():
        if party not in projected:
            projected[party] = poll_weight * poll_share

    total = sum(projected.values())
    if total > 0:
        projected = {p: v / total * 100 for p, v in projected.items()}
    return projected


def simulate_all_constituencies(
    baselines: Dict[str, ConstituencyBaseline],
    poll_shares: Dict[str, float],
    poll_weight: float,
    n_sims: int = GE_CONFIG["n_sims"],
    seat_uncertainty: float = GE_CONFIG["seat_uncertainty"],
    regional_variation: float = GE_CONFIG["regional_variation"],
) -> Tuple[Dict[str, int], Dict[str, np.ndarray]]:
    """
    Run Monte Carlo simulation across all constituencies.

    For each simulation iteration:
    1. Blend latest polls with each constituency's 2024 baseline (using
       poll_weight to control the historical vs. poll blend).
    2. Add Gaussian noise to each party's projected share (noise scales
       with the party's size and a base uncertainty factor).
    3. Determine the winner (highest projected share).
    4. Tally seats per party.

    Returns:
        Tuple of (aggregate seat counts, per-party seat arrays).
    """
    n_constituencies = len(baselines)
    consti_names = list(baselines.keys())

    # Pre-compute projected shares for each constituency (poll blend applied once)
    projected_shares: List[Dict[str, float]] = [
        blend_poll_and_baseline(baselines[cn], poll_shares, poll_weight) for cn in consti_names
    ]

    # Collect all unique parties across all constituencies
    all_parties: List[str] = []
    party_to_idx: Dict[str, int] = {}
    for shares in projected_shares:
        for party in shares:
            if party not in party_to_idx:
                party_to_idx[party] = len(all_parties)
                all_parties.append(party)

    n_parties = len(all_parties)

    # Build a matrix of projected shares: (n_constituencies, n_parties)
    share_matrix = np.zeros((n_constituencies, n_parties))
    for ci, shares in enumerate(projected_shares):
        for party, share in shares.items():
            share_matrix[ci, party_to_idx[party]] = share

    # Determine per-party noise level
    noise_levels = np.zeros(n_parties)
    for party, pi in party_to_idx.items():
        if party in ("Independent", "Other", "Traditional Unionist Voice - TUV"):
            noise_levels[pi] = regional_variation
        elif party in GE_CONFIG["major_parties_ge"]:
            noise_levels[pi] = seat_uncertainty * 0.8
        else:
            noise_levels[pi] = seat_uncertainty

    # Track seat wins: (n_sims, n_parties)
    seat_wins = np.zeros((n_sims, n_parties), dtype=int)

    for sim in tqdm(range(n_sims), desc="Simulating GE", unit="sim"):
        noise = np.random.normal(0, 1, size=(n_constituencies, n_parties))
        noisy = share_matrix + noise * noise_levels[np.newaxis, :]
        noisy = np.maximum(noisy, 0)
        noisy = noisy / noisy.sum(axis=1, keepdims=True) * 100

        winners = np.argmax(noisy, axis=1)
        seat_wins[sim] = np.bincount(winners, minlength=n_parties)

    aggregate_seats = {
        all_parties[pi]: int(round(np.mean(seat_wins[:, pi]))) for pi in range(n_parties)
    }

    # Ensure total seats equals n_constituencies (fix rounding drift)
    total = sum(aggregate_seats.values())
    diff = n_constituencies - total
    if diff != 0:
        top_party = max(aggregate_seats, key=aggregate_seats.get)
        aggregate_seats[top_party] += diff

    per_party_arrays = {
        all_parties[pi]: seat_wins[:, pi] for pi in range(n_parties)
    }

    return aggregate_seats, per_party_arrays


@dataclass(slots=True)
class PartySeatForecast:
    """Seat forecast for a single party in the House of Commons."""
    party: str
    projected_seats: int
    expected_seats: float
    win_probability: float
    median_seats: float
    ci_low: int
    ci_high: int
    swing: float


def forecast_general_election(
    csv_root: Path = ROOT,
    n_sims: int = GE_CONFIG["n_sims"],
    seed: int = 42,
    reference_date: date = GE_CONFIG["reference_date"],
) -> Tuple[List[PartySeatForecast], HouseOfCommonsResult, float]:
    """
    Run the full General Election simulation.

    Loads 2024 GE data, computes the national poll swing from current polling,
    applies it to all 650 constituencies, and runs Monte Carlo to produce
    a House of Commons seat distribution.

    The poll weight ramps up as the next GE date approaches: far from the
    election, the 2024 historical baseline carries more weight; as election
    day nears, polling data is weighted more heavily.

    Returns:
        Tuple of (per-party forecasts, aggregated result, poll weight used).
    """
    np.random.seed(seed)

    poll_weight = compute_poll_weight(reference_date)
    polling, _ = load_latest_polling(csv_root / "polling_averages.csv")
    baselines = load_all_constituencies(csv_root / "general_election_results.csv")

    aggregate_seats, per_party_arrays = simulate_all_constituencies(
        baselines, polling, poll_weight, n_sims=n_sims
    )

    MAJORTITY_THRESHOLD = 326  # seats needed for a House of Commons majority

    # Compute national-level swing (poll vs 2024 baseline) for display
    ge_totals = load_national_ge_totals(csv_root / "general_election_results.csv")
    swing_display: Dict[str, float] = {}
    for party in set(polling) & set(ge_totals):
        swing_display[party] = round(polling[party] - ge_totals.get(party, 0.0), 1)

    forecasts: List[PartySeatForecast] = []
    for party in sorted(aggregate_seats.keys(), key=lambda p: -aggregate_seats[p]):
        arr = per_party_arrays.get(party, np.zeros(n_sims, dtype=int))
        wins = int(aggregate_seats[party])
        expected = float(np.mean(arr))
        median = float(np.median(arr))
        ci_low = int(np.percentile(arr, 2.5))
        ci_high = int(np.percentile(arr, 97.5))
        majority_prob = float(np.mean(arr >= MAJORTITY_THRESHOLD)) * 100
        forecasts.append(PartySeatForecast(
            party=party,
            projected_seats=wins,
            expected_seats=round(expected, 1),
            win_probability=round(majority_prob, 1),
            median_seats=round(median, 1),
            ci_low=ci_low,
            ci_high=ci_high,
            swing=swing_display.get(party, 0.0),
        ))

    # Only display parties with at least some projected presence
    forecasts = [f for f in forecasts if f.projected_seats > 0 or f.expected_seats > 0.1]

    confidence_intervals: Dict[str, Tuple[int, int]] = {
        f.party: (f.ci_low, f.ci_high) for f in forecasts
    }
    median_seats: Dict[str, float] = {
        f.party: f.median_seats for f in forecasts
    }

    result = HouseOfCommonsResult(
        party_seats={f.party: f.projected_seats for f in forecasts},
        party_seats_won=aggregate_seats,
        total_seats=sum(aggregate_seats.values()),
        n_simulations=n_sims,
        median_seats=median_seats,
        confidence_intervals=confidence_intervals,
    )

    return forecasts, result, poll_weight


def format_ge_results(
    forecasts: List[PartySeatForecast],
    result: HouseOfCommonsResult,
    poll_weight: float = 0.5,
) -> str:
    """Format the General Election forecast into a display string."""
    bar_width = 50  # max bar characters
    next_ge = GE_CONFIG["next_ge_date"]
    ref_date = GE_CONFIG["reference_date"]
    days_remaining = (next_ge - ref_date).days
    weeks_remaining = max(days_remaining / 7.0, 0)
    ramp_weeks = GE_CONFIG["smoothing_ramp_weeks"]
    frac = min(weeks_remaining / ramp_weeks, 1.0) if ramp_weeks > 0 else 1.0

    lines = [
        "=" * 75,
        "  GENERAL ELECTION TOMORROW — HOUSE OF COMMONS SEAT FORECAST",
        "=" * 75,
        f"  Baseline:            {GE_CONFIG['baseline_year']} General Election",
        f"  Polling source:      GB-wide polling averages (latest from polling_averages.csv)",
        f"  Next GE date:        {next_ge.strftime('%Y-%m-%d')}",
        f"  Reference date:      {ref_date.strftime('%Y-%m-%d')} ({days_remaining} days / {weeks_remaining:.0f} weeks remaining)",
        f"  Poll weight:         {poll_weight:.0%} (latest polls vs 2024 baseline, ramp: {GE_CONFIG['swing_smoothing_far']}→{GE_CONFIG['swing_smoothing_near']} over {int(ramp_weeks/52)}yr, {frac:.1%} through ramp)",
    ]
    max_seats = max((f.projected_seats for f in forecasts), default=1)

    lines.append(
        f"  {'#':>3}  {'Party':<28} {'Seats':>6} {'Median':>7} "
         f"{'95% CI':>14} {'Swing':>7} {'Maj%':>6}  Bar"
    )
    lines.append("-" * 75)

    for i, f in enumerate(forecasts, 1):
        bar_len = int(f.projected_seats / max_seats * bar_width)
        bar = "█" * bar_len
        ci_str = f"{f.ci_low}–{f.ci_high}"
        lines.append(
            f"  {i:>3}  {f.party:<28} {f.projected_seats:>6} {f.median_seats:>7.1f} "
            f"{ci_str:>14} {f.swing:>+6.1f}pp {f.win_probability:>5.1f}%  {bar}"
        )

    lines.append("-" * 75)
    lines.append(
        f"  Total seats: {result.total_seats}   "
        f"Simulations: {result.n_simulations:,}   "
        f"Parties: {len(result.party_seats)}"
    )
    lines.append("=" * 75)
    return "\n".join(lines)


# ─── Main Entry Point ─────────────────────────────────────────────


def main() -> None:
    """Load data from CSVs and print both the GE seat forecast and Clacton by-election."""
    parser = argparse.ArgumentParser(
        description="General Election Tomorrow — House of Commons seat forecast."
    )
    parser.add_argument(
        "--simulations",
        type=int,
        default=None,
        help="Override the number of Monte Carlo simulations (default: 5,000).",
    )
    args = parser.parse_args()

    np.random.seed(42)
    sys.stdout.reconfigure(encoding="utf-8")

    ge_sims = args.simulations if args.simulations is not None else GE_CONFIG["n_sims"]
    _run_general_election(ge_sims)


def _run_general_election(n_sims: int) -> None:
    """Run and print the full 650-seat General Election forecast."""
    forecasts, result, poll_weight = forecast_general_election(n_sims=n_sims)
    print(format_ge_results(forecasts, result, poll_weight))


if __name__ == "__main__":
    main()
