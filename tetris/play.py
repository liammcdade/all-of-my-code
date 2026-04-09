"""
Evaluation and playback mode for trained Tetris RL agent.
Plays games using the trained model without exploration.
"""

import os
import argparse
import numpy as np

from environment import TetrisEnv
from agent import PlacementAgent


def play(
    checkpoint_path: str,
    num_games: int = 10,
    fps: int = 30,
    headless: bool = False,
):
    """Play games using a trained placement-based model."""
    env = TetrisEnv(render=not headless)
    state_size = env.get_state_size()

    agent = PlacementAgent(state_size=state_size)

    if os.path.exists(checkpoint_path):
        agent.load(checkpoint_path)
        agent.epsilon = 0.0
        print(f"Loaded model from {checkpoint_path}")
    else:
        print(f"Checkpoint not found: {checkpoint_path}")
        return

    print(f"Playing {num_games} games with trained agent")
    print("-" * 50)

    all_scores = []
    all_lines = []
    all_steps = []

    for game in range(1, num_games + 1):
        state = env.reset()
        placements = env.get_valid_placements()
        steps = 0

        while not env.game_over and placements:
            idx = agent.select_placement(
                state, placements, env.current_type, env.next_type, eval_mode=True
            )
            state, reward, done, info = env.apply_placement(idx)
            placements = env.get_valid_placements() if not done else []
            steps += 1

            if not headless:
                env.render_frame(
                    placement_idx=idx,
                    episode=game,
                    epsilon=0.0,
                    best_score=max(all_scores) if all_scores else 0,
                    fps=fps,
                )

        all_scores.append(env.score)
        all_lines.append(env.lines_cleared)
        all_steps.append(steps)

        print(
            f"Game {game:>3d}/{num_games} | "
            f"Score: {env.score:>7.0f} | "
            f"Lines: {env.lines_cleared:>3d} | "
            f"Placements: {steps:>4d}"
        )

    env.close()

    print("\n" + "=" * 50)
    print("Evaluation Results")
    print("=" * 50)
    print(f"Games played:    {num_games}")
    print(f"Average score:   {np.mean(all_scores):>10.1f}")
    print(f"Best score:      {np.max(all_scores):>10.0f}")
    print(f"Average lines:   {np.mean(all_lines):>10.1f}")
    print(f"Best lines:      {np.max(all_lines):>10.0f}")
    print(f"Average placements: {np.mean(all_steps):>10.1f}")
    print(f"Score std dev:   {np.std(all_scores):>10.1f}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Play Tetris with trained agent")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--headless", action="store_true")

    args = parser.parse_args()

    play(
        checkpoint_path=args.checkpoint,
        num_games=args.games,
        fps=args.fps,
        headless=args.headless,
    )
