"""Entry point: python main.py [--train N] [--games N]"""
import argparse
import sys
from collections import deque

from ai import Agent, Brain, load_brains, save_brains, DEFAULT_BRAINS
from engine import Engine, play_game
from tuning import (load_tuners, save_tuners, TUNER_FILE,
                    PARAM_SPEC, fitness as fit_fn)


def _baseline_agent(pid):
    """Frozen reference: default params, empty brain, no learning."""
    a = Agent(pid, Brain(), tuner=None)
    a.params = {k: v[2] for k, v in PARAM_SPEC.items()}
    return a


def train_until_ready(threshold=75.0,
                      max_games=20000,
                      window=100,
                      baseline_games=200):
    brains = load_brains(DEFAULT_BRAINS, 4)
    tuners = load_tuners(TUNER_FILE, 4)
    agents = [Agent(i, brains[i], tuners[i]) for i in range(4)]

    # ---------------- Phase 1: measure baseline ----------------
    sys.stdout.write(f"Measuring baseline ({baseline_games} games)... ")
    sys.stdout.flush()

    base_wins   = [0] * 4
    base_played = [0] * 4
    base_seq    = [[] for _ in range(4)]   # per-agent ordered 0/1 outcomes

    for g in range(baseline_games):
        seat = g % 4
        agents[seat].params = dict(tuners[seat].mean)  # starting params, no sampling
        seats = [_baseline_agent(s) if s != seat else agents[seat]
                 for s in range(4)]
        eng = Engine(agents=seats, turn_limit=400, verbose=False)
        play_game(eng)                                  # no tuner.update() here

        won = 1 if eng.winner == seat else 0
        base_wins[seat]   += won
        base_played[seat] += 1
        base_seq[seat].append(won)

    baseline_rate = [base_wins[i] / max(1, base_played[i]) for i in range(4)]
    targets       = [max(0.35, baseline_rate[i] + 0.03)   for i in range(4)]

    sys.stdout.write("done\n")
    sys.stdout.write("Baseline: " + "  ".join(
        f"A{i}:{baseline_rate[i]:.3f}" for i in range(4)) + "\n")
    sys.stdout.write("Targets:  " + "  ".join(
        f"A{i}:{targets[i]:.3f}"       for i in range(4)) + "\n\n")

    # ---------------- Phase 2: train until all > threshold ----------------
    wins = [deque(maxlen=window) for _ in range(4)]
    for i in range(4):
        for v in base_seq[i][-window:]:      # seed window with baseline games
            wins[i].append(v)

    def score(i):
        if not wins[i]:
            return 0.0
        wr    = sum(wins[i]) / len(wins[i])
        b, t  = baseline_rate[i], targets[i]
        denom = t - b
        if denom <= 1e-3:
            return 100.0 if wr >= b else 0.0
        return max(0.0, min(100.0, (wr - b) / denom * 100.0))

    scores = [0.0] * 4
    for g in range(max_games):
        seat    = g % 4
        learner = agents[seat]
        learner.params = learner.tuner.sample()

        seats = [_baseline_agent(s) if s != seat else learner
                 for s in range(4)]
        eng = Engine(agents=seats, turn_limit=400, verbose=False)
        play_game(eng)

        won = (eng.winner == seat)
        wins[seat].append(1 if won else 0)
        learner.tuner.update(fit_fn(eng, seat))

        scores = [score(i) for i in range(4)]

        line = (f"\r game {g + 1:>6}   "
                + "   ".join(f"A{i}:{scores[i]:>7.3f}" for i in range(4))
                + f"   need > {threshold:.0f}")
        sys.stdout.write(line + "     ")
        sys.stdout.flush()

        if all(s >= threshold for s in scores):
            sys.stdout.write(f"\n\nAll four agents reached {threshold:.0f}+ "
                             f"at game {g + 1}.\n")
            break
    else:
        sys.stdout.write(f"\n\nHit max_games={max_games}. Final: "
                         + ", ".join(f"A{i}:{scores[i]:.3f}" for i in range(4))
                         + "\n")

    print()
    save_brains(brains, DEFAULT_BRAINS)
    save_tuners(tuners, TUNER_FILE)
    print(f"Saved → {DEFAULT_BRAINS}, {TUNER_FILE}")
    return scores


def run_ab_test(n_games=200, turn_limit=400):
    """A/B test: trained agents (slots 0-1) vs fresh default agents (slots 2-3).

    A win rate significantly above 50% means training helped.
    ~50% means defaults were already good. Below 50% suggests a bug
    in the fitness/tuner or that save_brains didn't persist.
    """
    trained_brains = load_brains(DEFAULT_BRAINS, 4)
    trained_tuners = load_tuners(TUNER_FILE, 4)

    wins = 0
    for _ in range(n_games):
        agents = [
            Agent(0, trained_brains[0], trained_tuners[0]),
            Agent(1, trained_brains[1], trained_tuners[1]),
            Agent(2, None, None),
            Agent(3, None, None),
        ]
        eng = Engine(agents=agents, turn_limit=turn_limit, verbose=False)
        play_game(eng)
        if eng.winner in (0, 1):
            wins += 1

    rate = wins / n_games
    verdict = (">60% → training clearly helped" if rate > 0.6
               else "~50% → defaults already good" if abs(rate - 0.5) < 0.1
               else "<50% → check fitness/tuner/save_brains")
    print(f"Trained agents won {wins}/{n_games} = {rate:.1%}  ({verdict})")
    return rate


def headless_game(seed=None):
    brains = load_brains(DEFAULT_BRAINS, 4)
    agents = [Agent(i, brains[i]) for i in range(4)]
    eng = Engine(agents=agents, seed=seed, turn_limit=700, verbose=False)
    play_game(eng)
    for row in eng.summary():
        print(f"{row['name']:<8} cash £{row['cash']:<6} "
              f"net £{row['net_worth']:<6} props {row['properties']:<3} "
              f"monopolies {row['monopolies']}"
              + ("  BANKRUPT" if row["bankrupt"] else ""))
    if eng.winner is not None:
        print(f"\nWinner: {eng.players[eng.winner].name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=int, default=0,
                    help="train live: 1 learner vs 3 frozen baselines, stop at 75/100")
    ap.add_argument("--games", type=int, default=0,
                    help="play N headless games and print results")
    ap.add_argument("--ab-test", type=int, default=0, metavar="N",
                    help="run N game A/B test (trained vs default agents), "
                         "print win rate; good N is 200")
    args = ap.parse_args()

    if args.train:
        train_until_ready()
    elif args.ab_test:
        run_ab_test(args.ab_test)
    elif args.games:
        for _ in range(args.games):
            headless_game()
            print("-" * 60)
    else:
        from gui import run
        run()