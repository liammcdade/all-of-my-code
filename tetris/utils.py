"""
Utility functions for metrics tracking, graph generation, and model management.
"""

import os
import json
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime


class MetricsTracker:
    """Tracks and stores training metrics over episodes."""

    def __init__(self):
        self.episodes: List[int] = []
        self.scores: List[float] = []
        self.lines_cleared: List[int] = []
        self.epsilons: List[float] = []
        self.losses: List[float] = []
        self.steps: List[int] = []
        self.best_score: float = 0.0
        self.best_lines: int = 0
        self.hole_counts: List[float] = []
        self.heights: List[float] = []

    def log_episode(
        self,
        episode: int,
        score: float,
        lines: int,
        epsilon: float,
        steps: int,
        loss: Optional[float] = None,
        avg_holes: float = 0,
        avg_height: float = 0,
    ):
        """Log metrics for a completed episode."""
        self.episodes.append(episode)
        self.scores.append(score)
        self.lines_cleared.append(lines)
        self.epsilons.append(epsilon)
        self.steps.append(steps)
        self.hole_counts.append(avg_holes)
        self.heights.append(avg_height)

        if loss is not None:
            self.losses.append(loss)

        if score > self.best_score:
            self.best_score = score
        if lines > self.best_lines:
            self.best_lines = lines

    def get_recent_average(self, values: List[float], window: int = 100) -> float:
        """Get the average of the last N values."""
        if not values:
            return 0.0
        return np.mean(values[-window:])

    def get_summary(self, window: int = 100) -> Dict:
        """Get a summary of recent performance."""
        return {
            "episodes": len(self.episodes),
            "best_score": self.best_score,
            "best_lines": self.best_lines,
            "avg_score": self.get_recent_average(self.scores, window),
            "avg_lines": self.get_recent_average(self.lines_cleared, window),
            "avg_steps": self.get_recent_average(self.steps, window),
            "current_epsilon": self.epsilons[-1] if self.epsilons else 0,
            "avg_loss": self.get_recent_average(self.losses, window),
        }

    def save(self, filepath: str):
        """Save metrics to JSON file."""
        data = {
            "episodes": self.episodes,
            "scores": self.scores,
            "lines_cleared": self.lines_cleared,
            "epsilons": self.epsilons,
            "losses": self.losses,
            "steps": self.steps,
            "best_score": self.best_score,
            "best_lines": self.best_lines,
            "hole_counts": self.hole_counts,
            "heights": self.heights,
        }
        with open(filepath, "w") as f:
            json.dump(data, f)

    def load(self, filepath: str):
        """Load metrics from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        self.episodes = data["episodes"]
        self.scores = data["scores"]
        self.lines_cleared = data["lines_cleared"]
        self.epsilons = data["epsilons"]
        self.losses = data.get("losses", [])
        self.steps = data.get("steps", [])
        self.best_score = data.get("best_score", 0.0)
        self.best_lines = data.get("best_lines", 0)
        self.hole_counts = data.get("hole_counts", [])
        self.heights = data.get("heights", [])


def plot_training_metrics(metrics: MetricsTracker, save_path: str = None):
    """Generate and save training analysis plots."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    fig.suptitle("Tetris RL Training Analysis", fontsize=16, fontweight="bold")

    episodes = metrics.episodes

    # Scores with moving average
    ax = axes[0, 0]
    ax.plot(episodes, metrics.scores, alpha=0.3, color="blue", linewidth=0.5)
    if len(metrics.scores) > 50:
        window = min(100, len(metrics.scores) // 3)
        ma = np.convolve(metrics.scores, np.ones(window) / window, mode="valid")
        ax.plot(
            range(window, len(metrics.scores) + 1),
            ma,
            color="red",
            linewidth=1.5,
            label=f"Moving avg ({window})",
        )
    ax.set_title("Score per Episode")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Score")
    if len(metrics.scores) > 50:
        ax.legend()
    ax.grid(True, alpha=0.3)

    # Lines cleared
    ax = axes[0, 1]
    ax.plot(episodes, metrics.lines_cleared, alpha=0.3, color="green", linewidth=0.5)
    if len(metrics.lines_cleared) > 50:
        window = min(100, len(metrics.lines_cleared) // 3)
        ma = np.convolve(
            metrics.lines_cleared, np.ones(window) / window, mode="valid"
        )
        ax.plot(
            range(window, len(metrics.lines_cleared) + 1),
            ma,
            color="darkgreen",
            linewidth=1.5,
            label=f"Moving avg ({window})",
        )
    ax.set_title("Lines Cleared per Episode")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Lines")
    if len(metrics.lines_cleared) > 50:
        ax.legend()
    ax.grid(True, alpha=0.3)

    # Epsilon decay
    ax = axes[1, 0]
    ax.plot(episodes, metrics.epsilons, color="orange", linewidth=1.5)
    ax.set_title("Epsilon Decay")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Epsilon")
    ax.grid(True, alpha=0.3)

    # Training loss
    ax = axes[1, 1]
    if metrics.losses:
        loss_episodes = list(range(1, len(metrics.losses) + 1))
        ax.plot(loss_episodes, metrics.losses, alpha=0.4, color="red", linewidth=0.5)
        if len(metrics.losses) > 50:
            window = min(100, len(metrics.losses) // 3)
            ma = np.convolve(metrics.losses, np.ones(window) / window, mode="valid")
            ax.plot(
                range(window, len(metrics.losses) + 1),
                ma,
                color="darkred",
                linewidth=1.5,
                label=f"Moving avg ({window})",
            )
            ax.legend()
    ax.set_title("Training Loss")
    ax.set_xlabel("Training Step")
    ax.set_ylabel("Loss")
    ax.grid(True, alpha=0.3)

    # Hole count trend
    ax = axes[2, 0]
    if metrics.hole_counts:
        ax.plot(episodes, metrics.hole_counts, alpha=0.3, color="purple", linewidth=0.5)
        if len(metrics.hole_counts) > 50:
            window = min(100, len(metrics.hole_counts) // 3)
            ma = np.convolve(
                metrics.hole_counts, np.ones(window) / window, mode="valid"
            )
            ax.plot(
                range(window, len(metrics.hole_counts) + 1),
                ma,
                color="darkviolet",
                linewidth=1.5,
                label=f"Moving avg ({window})",
            )
            ax.legend()
    ax.set_title("Average Hole Count per Episode")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Holes")
    ax.grid(True, alpha=0.3)

    # Height trend
    ax = axes[2, 1]
    if metrics.heights:
        ax.plot(episodes, metrics.heights, alpha=0.3, color="brown", linewidth=0.5)
        if len(metrics.heights) > 50:
            window = min(100, len(metrics.heights) // 3)
            ma = np.convolve(
                metrics.heights, np.ones(window) / window, mode="valid"
            )
            ax.plot(
                range(window, len(metrics.heights) + 1),
                ma,
                color="saddlebrown",
                linewidth=1.5,
                label=f"Moving avg ({window})",
            )
            ax.legend()
    ax.set_title("Average Max Height per Episode")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Height")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Training plots saved to {save_path}")
    plt.close(fig)


def ensure_dir(path: str):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def get_timestamp() -> str:
    """Get current timestamp string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
