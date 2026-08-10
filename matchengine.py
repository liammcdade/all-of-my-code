
import random
import math
import csv
import importlib.util
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import numpy as np
from tqdm import tqdm
from typing import Dict, Tuple
import sys


def _load_modules():
    module_dir = Path(__file__).resolve().parent / "sportsanalysis" / "premier-league"
    candidate_paths = [
        module_dir,
        Path(r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\premier-league"),
    ]

    for path in candidate_paths:
        if not path.exists():
            continue
        sys.path.insert(0, str(path))
        try:
            import modules  # type: ignore

            return modules
        except ImportError:
            pass

    module_file = module_dir / "modules.py"
    if not module_file.exists():
        raise ImportError("Could not find sportsanalysis/premier-league/modules.py")

    spec = importlib.util.spec_from_file_location("modules", module_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {module_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modules = _load_modules()
FIXTURES_LIST = modules.FIXTURES_LIST
BETTING_MARKETS = modules.BETTING_MARKETS
POLYMARKET_TITLE = modules.POLYMARKET_TITLE
_load_historical_data = modules._load_historical_data


EXTERNAL_ELOS, WDL_RATES = _load_historical_data()
wdl_rates = WDL_RATES


def get_adjusted_elo(team: str, ratings) -> float:
    """
    Simple passthrough to current rating.
    If you later want team-specific adjustments, do them here.
    """
    return float(ratings.get(team, 1500.0))



class OptimizedELORatingSystem:
    def __init__(self, k_factor=30, home_advantage=85):
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.ratings = defaultdict(lambda: 1500.0)
        self.match_weights = {'league': 1.5}

    def expected_score(self, ra, rb):
        return 1 / (1 + 10 ** ((rb - ra) / 400))

    def update_ratings(self, home, away, hs, aws, match_type='league'):
        K = self.k_factor * self.match_weights.get(match_type, 1.5)
        hr, ar = self.ratings[home] + self.home_advantage, self.ratings[away]

        gm = min(1 + math.log(1 + abs(hs - aws)), 2.0)

        eh, ea = self.expected_score(hr, ar), self.expected_score(ar, hr)

        ah = 1 if hs > aws else (0.5 if hs == aws else 0)
        aa = 1 if aws > hs else (0.5 if hs == aws else 0)

        self.ratings[home] += K * gm * (ah - eh)
        self.ratings[away] += K * gm * (aa - ea)

    def predict_score(self, home, away, neutral=False):
        ha = 0 if neutral else self.home_advantage

        diff = (
            get_adjusted_elo(home, self.ratings)
            - get_adjusted_elo(away, self.ratings)
            + ha
        )

        hxg = 0.6 + 1.7 / (1 + math.exp(-diff / 400))
        axg = 0.6 + 1.7 / (1 + math.exp(diff / 400))

        closeness = math.exp(-(diff ** 2) / (2 * 180 ** 2))

        bd = (
            (wdl_rates[home]["win"] - wdl_rates[home]["loss"])
            - (wdl_rates[away]["win"] - wdl_rates[away]["loss"])
        ) * 0.5

        hxg = hxg + bd * 0.15
        axg = axg - bd * 0.15

        tempo = 0.9 + 0.1 * (abs(diff) / 400)

        hxg = hxg * tempo
        axg = axg * tempo

        vb = 1 + (wdl_rates[home]["win"] - wdl_rates[home]["draw"]) * 0.1
        db = max((wdl_rates[home]["draw"] + wdl_rates[away]["draw"]) / 2, 0.3)

        ls = 0.05 + closeness * 0.25 * db

        lh = max(0.05, hxg - ls) * vb
        la = max(0.05, axg - ls)

        sg = np.random.poisson(ls)

        home_goals = int(np.random.poisson(lh) + sg)
        away_goals = int(np.random.poisson(la) + sg)

        return home_goals, away_goals
