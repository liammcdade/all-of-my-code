"""
Neural network for placement-based Tetris RL.
Evaluates (board_state, placement) -> Q-value.
Uses a CNN on the raw board + MLP on handcrafted features.
Includes NoisyNet layers for better exploration.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
from typing import List

from environment import BOARD_HEIGHT, BOARD_WIDTH, NUM_PIECE_TYPES, PIECE_ONEHOT, MAX_ROTATIONS

# Placement feature dimensions: 7 cur + 9 geom + 7 next = 23
PLACEMENT_FEAT_DIM = 23

# State layout (must match environment._build_state):
#   board_flat:  200  (BOARD_HEIGHT * BOARD_WIDTH)
#   heights:      10  (BOARD_WIDTH)
#   scalars:       6  (agg, max, bump, holes, wells, danger)
#   row_feats:   20  (BOARD_HEIGHT)
#   transitions:   2  (row_trans, col_trans)
#   level:         1
#   cur_oh:        7
#   nxt_oh:        7
BOARD_FLAT_SIZE = BOARD_HEIGHT * BOARD_WIDTH  # 200
HEIGHTS_SIZE = BOARD_WIDTH                     # 10
SCALARS_SIZE = 6
ROW_FEATS_SIZE = BOARD_HEIGHT                 # 20
TRANS_SIZE = 2
LEVEL_SIZE = 1
PIECE_SIZE = 7 * 2  # current + next
HANDCRAFTED_SIZE = HEIGHTS_SIZE + SCALARS_SIZE + ROW_FEATS_SIZE + TRANS_SIZE + LEVEL_SIZE + PIECE_SIZE  # 53


# ======================================================================
# NoisyNet: factorised Gaussian noise on linear layers
# ======================================================================

class NoisyLinear(nn.Module):
    """Noisy linear layer with factorised Gaussian noise (Fortunato et al., 2018).

    Provides state-dependent exploration without epsilon-greedy.
    The noise is learned and adapts during training.
    """

    def __init__(self, in_features: int, out_features: int, sigma_init: float = 0.5):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features

        # Learnable parameters: mu and sigma for weight and bias
        self.weight_mu = nn.Parameter(torch.empty(out_features, in_features))
        self.weight_sigma = nn.Parameter(torch.empty(out_features, in_features))
        self.register_buffer('weight_epsilon', torch.empty(out_features, in_features))

        self.bias_mu = nn.Parameter(torch.empty(out_features))
        self.bias_sigma = nn.Parameter(torch.empty(out_features))
        self.register_buffer('bias_epsilon', torch.empty(out_features))

        self.sigma_init = sigma_init
        self.reset_parameters()
        self.reset_noise()

    def reset_parameters(self):
        """Initialize mu with Kaiming uniform, sigma with constant."""
        bound = 1.0 / math.sqrt(self.in_features)
        self.weight_mu.data.uniform_(-bound, bound)
        self.weight_sigma.data.fill_(self.sigma_init / math.sqrt(self.in_features))
        self.bias_mu.data.uniform_(-bound, bound)
        self.bias_sigma.data.fill_(self.sigma_init / math.sqrt(self.in_features))

    @staticmethod
    def _scale_noise(size: int) -> torch.Tensor:
        """Factorised noise: f(x) = sign(x) * sqrt(|x|)."""
        x = torch.randn(size)
        return x.sign() * x.abs().sqrt()

    def reset_noise(self):
        """Sample new noise for weights and biases."""
        eps_in = self._scale_noise(self.in_features)
        eps_out = self._scale_noise(self.out_features)
        self.weight_epsilon.copy_(eps_out.outer(eps_in))
        self.bias_epsilon.copy_(eps_out)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.training:
            weight = self.weight_mu + self.weight_sigma * self.weight_epsilon
            bias = self.bias_mu + self.bias_sigma * self.bias_epsilon
        else:
            weight = self.weight_mu
            bias = self.bias_mu
        return F.linear(x, weight, bias)


# ======================================================================
# Network blocks
# ======================================================================

class ResBlock(nn.Module):
    """Simple residual block for CNN encoder."""

    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        return F.relu(out)


class PlacementNetwork(nn.Module):
    """Evaluates a board state + one placement and outputs a scalar Q-value.

    Architecture:
        board_grid (20x10) -> CNN encoder  -> board_vec
        handcrafted feats  -> MLP encoder  -> feat_vec
        placement feats    -> MLP encoder  -> place_vec
        [board_vec, feat_vec, place_vec] -> combiner -> Q(s, a)

    Uses NoisyNet on the final Q-value layer for better exploration.
    """

    def __init__(self, state_size: int, hidden: List[int] = None,
                 use_noisy: bool = True, sigma_init: float = 0.5):
        super().__init__()
        expected = BOARD_FLAT_SIZE + HANDCRAFTED_SIZE
        assert state_size == expected, (
            f"state_size={state_size} but expected {expected} "
            f"(board={BOARD_FLAT_SIZE} + handcrafted={HANDCRAFTED_SIZE})"
        )

        if hidden is None:
            hidden = [256, 128]

        self.use_noisy = use_noisy

        # --- CNN encoder for raw board ---
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            ResBlock(32),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            ResBlock(64),
            nn.AdaptiveAvgPool2d((4, 3)),
        )
        cnn_out_size = 64 * 4 * 3

        self.cnn_fc = nn.Sequential(
            nn.Linear(cnn_out_size, hidden[0]),
            nn.ReLU(),
        )

        # --- MLP encoder for handcrafted features ---
        self.feat_encoder = nn.Sequential(
            nn.Linear(HANDCRAFTED_SIZE, 128),
            nn.ReLU(),
            nn.Linear(128, hidden[0]),
            nn.ReLU(),
        )

        # --- MLP encoder for placement features ---
        self.place_encoder = nn.Sequential(
            nn.Linear(PLACEMENT_FEAT_DIM, 128),
            nn.ReLU(),
            nn.Linear(128, hidden[1]),
            nn.ReLU(),
        )

        # --- Combiner with NoisyNet on final layer ---
        self.combiner_hidden = nn.Sequential(
            nn.Linear(hidden[0] * 2 + hidden[1], hidden[1]),
            nn.ReLU(),
            nn.Dropout(0.1),
        )

        if use_noisy:
            self.combiner_out = NoisyLinear(hidden[1], 1, sigma_init=sigma_init)
        else:
            self.combiner_out = nn.Linear(hidden[1], 1)

    def _encode_board_and_features(self, state):
        """Split state into board grid and handcrafted features, encode both."""
        board_flat = state[:, :BOARD_FLAT_SIZE]
        handcrafted = state[:, BOARD_FLAT_SIZE:]
        board_grid = board_flat.reshape(-1, 1, BOARD_HEIGHT, BOARD_WIDTH)

        cnn_out = self.cnn(board_grid)
        cnn_out = cnn_out.reshape(cnn_out.size(0), -1)
        board_vec = self.cnn_fc(cnn_out)
        feat_vec = self.feat_encoder(handcrafted)
        return board_vec, feat_vec

    def reset_noise(self):
        """Resample noise in all NoisyLinear layers."""
        for m in self.modules():
            if isinstance(m, NoisyLinear):
                m.reset_noise()

    def forward(self, state: torch.Tensor,
                placement_feats: torch.Tensor) -> torch.Tensor:
        """
        Args:
            state: (batch, state_size)
            placement_feats: (batch, placement_count, PLACEMENT_FEAT_DIM)
        Returns:
            q_values: (batch, placement_count)
        """
        batch_size, num_placements, _ = placement_feats.shape

        board_vec, feat_vec = self._encode_board_and_features(state)
        state_vec = torch.cat([board_vec, feat_vec], dim=1)

        place_flat = placement_feats.reshape(
            batch_size * num_placements, PLACEMENT_FEAT_DIM
        )
        place_vec = self.place_encoder(place_flat)

        state_tiled = state_vec.unsqueeze(1).expand(
            -1, num_placements, -1
        ).reshape(batch_size * num_placements, -1)

        combined = torch.cat([state_tiled, place_vec], dim=1)
        h = self.combiner_hidden(combined)
        q = self.combiner_out(h).squeeze(-1)
        return q.reshape(batch_size, num_placements)


def placement_features(placement, current_type: str, next_type: str) -> np.ndarray:
    """Convert a Placement object to a feature vector, including next piece info."""
    cur_oh = PIECE_ONEHOT[current_type]
    nxt_oh = PIECE_ONEHOT[next_type]
    geom = [
        placement.rotation / max(MAX_ROTATIONS - 1, 1),
        placement.col / max(BOARD_WIDTH - 1, 1),
        placement.row / max(BOARD_HEIGHT - 1, 1),
        placement.height / BOARD_HEIGHT,
        placement.holes / 30.0,
        placement.bumpiness / 50.0,
        placement.lines_cleared / 4.0,
        placement.row_transitions / (BOARD_HEIGHT * (BOARD_WIDTH - 1)),
        placement.col_transitions / (BOARD_WIDTH * (BOARD_HEIGHT - 1)),
    ]
    return np.array(cur_oh + geom + nxt_oh, dtype=np.float32)
