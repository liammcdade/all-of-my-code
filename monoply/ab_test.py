"""Standalone A/B test: trained agents vs fresh default agents.

Usage:
    python ab_test.py [N]     # N games, default 200

Trained agents occupy slots 0-1 (loaded from monopoly_brains.json /
monopoly_tuners.json).  Fresh default agents occupy slots 2-3.

Win rate interpretation:
    >60%  training clearly helped
    ~50%  defaults were already good (training confirms it)
    <50%  check fitness/tuner — save_brains may not be persisting
"""
import sys

from ai import Agent, load_brains, DEFAULT_BRAINS
from tuning import load_tuners, TUNER_FILE
from engine import Engine, play_game


def run(n_games=200, turn_limit=400):
    trained_brains = load_brains(DEFAULT_BRAINS, 4)
    trained_tuners = load_tuners(TUNER_FILE, 4)

    wins = 0
    for i in range(n_games):
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
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{n_games} — {wins} wins "
                  f"({wins / (i + 1):.1%})", flush=True)

    rate = wins / n_games
    verdict = (">60% → training clearly helped" if rate > 0.6
               else "~50% → defaults already good" if abs(rate - 0.5) < 0.1
               else "<50% → check fitness/tuner/save_brains")
    print(f"\nTrained agents won {wins}/{n_games} = {rate:.1%}  ({verdict})")
    return rate


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    run(n)
