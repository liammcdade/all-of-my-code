"""
Tetris RL - Main entry point.
Usage:
  python main.py train [options]    - Train the agent (cycles when epsilon hits 0.05)
  python main.py play [options]     - Watch trained agent play
  python main.py test-env           - Quick environment test (no training)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "train":
        import train as train_mod
        import argparse

        # Re-parse using train.py's argument parser
        sys.argv = ["train"] + sys.argv[2:]
        train_mod.main()

    elif mode == "play":
        if len(sys.argv) < 3:
            print("Usage: python main.py play <checkpoint_path>")
            sys.exit(1)
        from play import play

        play(checkpoint_path=sys.argv[2])

    elif mode == "test-env":
        from environment import TetrisEnv

        env = TetrisEnv(render=False)
        state = env.reset()
        print(f"State size: {state.shape[0]}")

        for i in range(20):
            placements = env.get_valid_placements()
            if not placements:
                print("No valid placements - game over!")
                break
            idx = i % len(placements)
            p = placements[idx]
            state, reward, done, info = env.apply_placement(idx)
            print(
                f"Placement {i}: rot={p.rotation} col={p.col} "
                f"reward={reward:.3f} score={env.score} lines={env.lines_cleared} "
                f"done={done}"
            )
            if done:
                print("Game over!")
                break

        env.close()
        print("Environment test passed!")

    else:
        print(f"Unknown mode: {mode}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
