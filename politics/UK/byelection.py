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


# ─── Main Entry Point ─────────────────────────────────────────────

def main() -> None:
    """Load data from CSVs and print the Clacton by-election forecast."""
    parser = argparse.ArgumentParser(
        description="Clacton by-election predictor powered by CSV data."
    )
    parser.add_argument(
        "--gb-wide",
        action="store_true",
        help="Use GB-wide polling averages from polling_averages.csv "
        "instead of the 2026 SON candidate list.",
    )
    args = parser.parse_args()

    np.random.seed(42)
    sys.stdout.reconfigure(encoding="utf-8")

    predictor = ClactonByElectionPredictor()

    if args.gb_wide:
        polls_label = "GB-wide polling (polling_averages.csv)"
        pass  # predictor defaults to self.polling when current_polls=None
    else:
        polls_label = "2026 SON candidate list"
    print(f"\n  Polling source: {polls_label}\n")
    print(f"  Candidates standing: {len(CANDIDATE_LIST_2026)}\n")

    results = predictor.predict(
        current_polls=candidate_polls_from_list(CANDIDATE_LIST_2026) if not args.gb_wide else None,
    )

    print(format_results(results, predictor))


if __name__ == "__main__":
    main()
