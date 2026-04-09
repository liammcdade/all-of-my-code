"""
Training loop for the Tetris RL agent.
Uses meta-actions (placement selection) instead of primitive actions.
Includes automatic epsilon cycling: when epsilon reaches the cycle threshold,
it resets to the starting value while keeping all learned weights.
"""

import os
import time
import argparse
import numpy as np

from environment import TetrisEnv
from agent import PlacementAgent
from utils import MetricsTracker, plot_training_metrics, ensure_dir, get_timestamp


def run_evaluation_episode(agent, render=False, max_placements=200):
    """Run one greedy episode (epsilon=0) and return (nes_score, lines, steps)."""
    env = TetrisEnv(render=render)
    state = env.reset()
    placements = env.get_valid_placements()
    steps = 0

    while not env.game_over and placements and steps < max_placements:
        idx = agent.select_placement(
            state, placements, env.current_type, env.next_type, eval_mode=True
        )
        state, reward, done, info = env.apply_placement(idx)
        placements = env.get_valid_placements() if not done else []
        steps += 1

    nes = env.nes_score
    lines = env.lines_cleared
    env.close()
    return nes, lines, steps


def train(
    render: bool = False,
    fast: bool = False,
    save_dir: str = "checkpoints",
    load_checkpoint: str = None,
    hidden_sizes: list = None,
    lr: float = 1e-4,
    gamma: float = 0.99,
    epsilon_start: float = 1.0,
    epsilon_end: float = 0.01,
    epsilon_decay: float = 0.99,
    epsilon_cycle_threshold: float = 0.05,
    batch_size: int = 128,
    buffer_size: int = 200000,
    target_update: int = 100,
    double_dqn: bool = True,
    fps: int = 30,
):
    """Train with placement-based DQN and epsilon cycling + curriculum learning.

    Curriculum: progressively increases starting level and injects harder pieces
    as the agent improves. Every curriculum_check episodes, if the rolling average
    score exceeds a threshold, the difficulty increases.
    """
    ensure_dir(save_dir)
    timestamp = get_timestamp()
    render_mode = render and not fast

    # Curriculum state
    curriculum_level = 1
    curriculum_pieces = []
    curriculum_threshold = 50.0  # avg score needed to advance
    curriculum_check = 300       # check every N episodes
    hard_pieces = ['Z', 'S', 'T']  # pieces to inject at higher curriculum

    env = TetrisEnv(render=render_mode, starting_level=curriculum_level,
                    extra_bag_pieces=curriculum_pieces)
    state_size = env.get_state_size()


    if hidden_sizes is None:
        hidden_sizes = [512, 256, 128]

    agent = PlacementAgent(
        state_size=state_size,
        hidden_sizes=hidden_sizes,
        lr=lr,
        gamma=gamma,
        epsilon_start=epsilon_start,
        epsilon_end=epsilon_end,
        epsilon_decay=epsilon_decay,
        batch_size=batch_size,
        buffer_size=buffer_size,
        target_update_freq=target_update,
        use_double_dqn=double_dqn,
    )

    metrics = MetricsTracker()

    if load_checkpoint and os.path.exists(load_checkpoint):
        agent.load(load_checkpoint)
        mp = load_checkpoint.replace(".pt", "_metrics.json")
        if os.path.exists(mp):
            metrics.load(mp)
        print(f"Loaded checkpoint from {load_checkpoint}")

    print(f"Training with meta-actions + epsilon cycling")
    print(f"Epsilon: {epsilon_start} -> {epsilon_cycle_threshold} -> reset (decay={epsilon_decay})")
    print(f"LR: {lr}, Batch: {batch_size}, Buffer: {buffer_size}")
    print(f"State size: {state_size}")
    print(f"Device: {agent.device}")
    print(f"Hidden: {hidden_sizes}")
    print(f"Double DQN: {double_dqn}")
    print("-" * 60)

    cycle = 1
    global_episode = 0
    fps_timer = time.time()
    fps_counter = 0

    while True:
        print(f"\n{'=' * 60}")
        print(f"CYCLE {cycle}  |  epsilon reset to {epsilon_start:.4f}")
        print(f"{'=' * 60}")

        agent.epsilon = epsilon_start
        cycle_start = global_episode

        while agent.epsilon > epsilon_cycle_threshold:
            global_episode += 1
            state = env.reset()
            placements = env.get_valid_placements()
            episode_losses = []
            steps = 0

            while not env.game_over and placements:
                current_type = env.current_type
                next_type = env.next_type

                idx = agent.select_placement(
                    state, placements, current_type, next_type, eval_mode=False
                )

                old_state = state
                old_placements = placements
                old_cur = current_type
                old_nxt = next_type

                next_state, reward, done, info = env.apply_placement(idx)
                next_placements = env.get_valid_placements() if not done else []
                new_cur = env.current_type
                new_nxt = env.next_type

                agent.store(old_state, old_placements, old_cur, old_nxt, idx,
                            reward, next_state, next_placements, new_nxt, done)

                loss = agent.train_step()
                if loss is not None:
                    episode_losses.append(loss)

                steps += 1
                state = next_state
                placements = next_placements

                if render_mode:
                    env.render_frame(
                        placement_idx=idx,
                        episode=global_episode,
                        epsilon=agent.epsilon,
                        best_score=metrics.best_score,
                        fps=fps,
                    )
                fps_counter += 1

            avg_loss = np.mean(episode_losses) if episode_losses else None

            metrics.log_episode(
                episode=global_episode,
                score=env.score,
                lines=env.lines_cleared,
                epsilon=agent.epsilon,
                steps=steps,
                loss=avg_loss,
            )

            summary = metrics.get_summary()
            elapsed = time.time() - fps_timer
            eph = fps_counter / elapsed if elapsed > 0 else 0
            fps_counter = 0
            fps_timer = time.time()

            print(
                f"C{cycle} Ep {global_episode:>5d} | "
                f"NES: {env.nes_score:>7d} | "
                f"RL: {env.score:>7.0f} | "
                f"Lines: {env.lines_cleared:>3d} | "
                f"Plcmnts: {steps:>3d} | "
                f"Loss: {avg_loss or 0:>7.4f} | "
                f"Eps: {agent.epsilon:.4f} | "
                f"Avg100: {summary['avg_score']:>7.1f} | "
                f"Best: {metrics.best_score:>7.0f} | "
                f"{eph:.0f} ep/h"
            )

            if global_episode % 200 == 0:
                ckpt = os.path.join(save_dir, f"ckpt_ep{global_episode}_{timestamp}.pt")
                agent.save(ckpt)
                metrics.save(ckpt.replace(".pt", "_metrics.json"))

            if env.score >= metrics.best_score and global_episode > 50:
                bp = os.path.join(save_dir, f"best_{timestamp}.pt")
                agent.save(bp)
                metrics.save(bp.replace(".pt", "_metrics.json"))

            # --- Curriculum check: increase difficulty if agent is improving ---
            if global_episode % curriculum_check == 0 and global_episode > 0:
                summary_now = metrics.get_summary(window=curriculum_check)
                avg = summary_now['avg_score']
                if avg > curriculum_threshold:
                    # Increase starting level
                    if curriculum_level < 10:
                        curriculum_level += 1
                    # Add harder pieces
                    for hp in hard_pieces:
                        if hp not in curriculum_pieces and len(curriculum_pieces) < 3:
                            curriculum_pieces.append(hp)
                            break
                    curriculum_threshold += 30.0  # raise bar for next level
                    env.set_curriculum(curriculum_level, curriculum_pieces)
                    print(
                        f"  >>> Curriculum advanced: level={curriculum_level}, "
                        f"extra_pieces={curriculum_pieces}, "
                        f"next_threshold={curriculum_threshold:.0f}"
                    )

        # --- Cycle boundary: save everything, reset epsilon, keep weights ---
        cycle_eps = global_episode - cycle_start
        cp = os.path.join(save_dir, f"cycle{cycle}_{timestamp}.pt")
        agent.save(cp)
        metrics.save(cp.replace(".pt", "_metrics.json"))

        plot_training_metrics(metrics, os.path.join(save_dir, f"plot_{timestamp}.png"))

        summary = metrics.get_summary()

        # ------------------------------------------------------------------
        # Run a quick evaluation episode (greedy, no exploration)
        # ------------------------------------------------------------------
        eval_nes, eval_lines, eval_steps = run_evaluation_episode(agent, render=False)

        print(f"\n--- Evaluation after Cycle {cycle} ---")
        print(f"  NES score:   {eval_nes}")
        print(f"  Lines:       {eval_lines}")
        print(f"  Placements:  {eval_steps}")
        print(f"  Avg RL score (last 100): {summary['avg_score']:.1f}")
        print(f"  Best RL score so far:    {metrics.best_score:.0f}")
        print("-" * 60)

        cycle += 1


def main():
    parser = argparse.ArgumentParser(description="Train Tetris RL (meta-actions)")
    parser.add_argument("--render", action="store_true", help="Enable pygame rendering (slower)")
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--save-dir", type=str, default="checkpoints")
    parser.add_argument("--load", type=str, default=None)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--epsilon-decay", type=float, default=0.99)
    parser.add_argument("--epsilon-cycle", type=float, default=0.05)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--buffer-size", type=int, default=200000)
    parser.add_argument("--fps", type=int, default=30)

    args = parser.parse_args()

    train(
        render=args.render,
        fast=args.fast,
        save_dir=args.save_dir,
        load_checkpoint=args.load,
        lr=args.lr,
        gamma=args.gamma,
        epsilon_decay=args.epsilon_decay,
        epsilon_cycle_threshold=args.epsilon_cycle,
        batch_size=args.batch_size,
        buffer_size=args.buffer_size,
        fps=args.fps,
    )


if __name__ == "__main__":
    main()
