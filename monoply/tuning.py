"""Learnable tuning parameters via (1+1) evolution strategy."""
import json
import os
import random

# name : (low, high, initial, initial_sigma)
PARAM_SPEC = {
    "buy_threshold":      (0.4,  1.5,  0.75, 0.10),   # accept if EV >= k*price
    "reserve_frac":       (0.00, 0.40, 0.10, 0.05),   # keep k*cash in reserve
    "denial_weight":      (0.00, 1.50, 0.50, 0.15),   # value of blocking opponents
    "mono_bonus":         (1.20, 3.00, 1.80, 0.20),   # multiplier when purchase completes set
    "horizon":            (80.0, 400.0, 200.0, 30.0), # remaining-game turn estimate
    "payback_base":       (8.0,  40.0, 20.0, 5.0),    # payback threshold at cash=0
    "payback_cash_scale": (0.01, 0.10, 0.03, 0.01),   # how much to loosen as cash grows
    "bail_threshold":     (80.0, 500.0, 200.0, 50.0), # pay jail fine if cash > this
    "epsilon":            (0.02, 0.30, 0.10, 0.03),   # Q-learning exploration
    "alpha":              (0.05, 0.50, 0.25, 0.05),   # Q-learning rate
    "gamma":              (0.60, 0.99, 0.85, 0.05),   # Q-learning discount
}

TUNER_FILE = "monopoly_tuners.json"


class SelfTuner:
    """(1+1)-ES: sample a candidate each game; if it beats the running mean,
    pull the mean toward it and shrink sigma, else expand sigma."""

    def __init__(self, spec=None, rng=None):
        self.spec = spec or PARAM_SPEC
        self.rng = rng or random.Random()
        self.mean = {k: v[2] for k, v in self.spec.items()}
        self.sigma = {k: v[3] for k, v in self.spec.items()}
        self.run_fitness = None
        self.best_mean = dict(self.mean)
        self.best_fitness = -1e18
        self.games = 0
        self._last = None

    def sample(self):
        c = {}
        for k, (lo, hi, _, _) in self.spec.items():
            v = self.rng.gauss(self.mean[k], self.sigma[k])
            c[k] = max(lo, min(hi, v))
        self._last = c
        return c

    def update(self, fitness):
        self.games += 1
        if self.run_fitness is None:
            self.run_fitness = fitness
        success = self._last is not None and fitness > self.run_fitness
        if success:
            lr = 0.25
            for k in self.mean:
                self.mean[k] = (1 - lr) * self.mean[k] + lr * self._last[k]
            for k in self.sigma:
                lo, hi, *_ = self.spec[k]
                self.sigma[k] = max((hi - lo) * 0.01, self.sigma[k] * 0.90)
        else:
            for k in self.sigma:
                lo, hi, *_ = self.spec[k]
                self.sigma[k] = min((hi - lo) * 0.25, self.sigma[k] * 1.10)
        self.run_fitness = 0.9 * self.run_fitness + 0.1 * fitness
        if fitness > self.best_fitness:
            self.best_fitness = fitness
            self.best_mean = dict(self.mean)

    def to_dict(self):
        return {"mean": self.mean, "sigma": self.sigma,
                "run_fitness": self.run_fitness,
                "best_mean": self.best_mean, "best_fitness": self.best_fitness,
                "games": self.games}

    @classmethod
    def from_dict(cls, d):
        t = cls()
        t.mean.update(d.get("mean", {}))
        t.sigma.update(d.get("sigma", {}))
        t.run_fitness = d.get("run_fitness")
        t.best_mean.update(d.get("best_mean", {}))
        t.best_fitness = d.get("best_fitness", -1e18)
        t.games = d.get("games", 0)
        return t


def fitness(eng, pid):
    """Reward: final net worth, big bonus for winning, penalty for bankruptcy."""
    p = eng.players[pid]
    if p.bankrupt:
        return -1000.0 - eng.turn * 0.1
    nw = float(eng.net_worth(pid))
    if eng.winner == pid:
        nw += 1000.0
    return nw


def load_tuners(path=TUNER_FILE, n=4):
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            out = [SelfTuner.from_dict(d) for d in data][:n]
            while len(out) < n:
                out.append(SelfTuner())
            return out
        except (json.JSONDecodeError, OSError, KeyError):
            pass
    return [SelfTuner() for _ in range(n)]


def save_tuners(tuners, path=TUNER_FILE):
    with open(path, "w") as f:
        json.dump([t.to_dict() for t in tuners], f, indent=1)
