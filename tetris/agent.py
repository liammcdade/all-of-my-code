"""
Placement-based DQN agent for Tetris.
Evaluates all valid placements for the current piece and chooses the best one.
Supports Double DQN, Prioritized Experience Replay, and epsilon-greedy.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import random
from collections import deque
from typing import List, Tuple, Optional

from model import PlacementNetwork, placement_features, PLACEMENT_FEAT_DIM
from environment import Placement


# ======================================================================
# Sum-tree for O(log n) prioritized sampling
# ======================================================================

class SumTree:
    """Binary sum-tree for proportional prioritized sampling."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity - 1, dtype=np.float64)
        self.data = [None] * capacity
        self.write_idx = 0
        self.size = 0

    def total(self) -> float:
        return self.tree[0]

    def add(self, priority: float, data):
        idx = self.write_idx + self.capacity - 1
        self.data[self.write_idx] = data
        self._update(idx, priority)
        self.write_idx = (self.write_idx + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def _update(self, idx: int, priority: float):
        delta = priority - self.tree[idx]
        self.tree[idx] = priority
        while idx > 0:
            idx = (idx - 1) // 2
            self.tree[idx] += delta

    def update_priority(self, idx: int, priority: float):
        """Update priority at leaf index (0-based within data)."""
        tree_idx = idx + self.capacity - 1
        self._update(tree_idx, priority)

    def get(self, cumulative: float):
        """Retrieve (leaf_index, priority, data) for a cumulative value."""
        idx = 0
        while idx < self.capacity - 1:
            left = 2 * idx + 1
            if cumulative <= self.tree[left]:
                idx = left
            else:
                cumulative -= self.tree[left]
                idx = left + 1
        data_idx = idx - self.capacity + 1
        return data_idx, self.tree[idx], self.data[data_idx]


# ======================================================================
# Prioritized replay buffer
# ======================================================================

class PrioritizedReplayBuffer:
    """Proportional prioritized experience replay with sum-tree.

    Stores transitions and samples them proportional to TD-error^alpha.
    Uses importance-sampling weights to correct for the bias.
    """

    def __init__(self, capacity: int = 200000, alpha: float = 0.6):
        self.tree = SumTree(capacity)
        self.alpha = alpha
        self.max_priority = 1.0
        self.capacity = capacity

    def push(self, state, place_feats, action, reward,
             next_state, next_place_feats, done):
        """Store a new transition with maximum priority."""
        data = (
            np.array(state, dtype=np.float32),
            np.array(place_feats, dtype=np.float32),
            int(action),
            float(reward),
            np.array(next_state, dtype=np.float32),
            np.array(next_place_feats, dtype=np.float32) if next_place_feats is not None else None,
            float(done),
        )
        self.tree.add(self.max_priority ** self.alpha, data)

    def sample(self, batch_size: int, beta: float = 0.4):
        """Sample a batch proportional to priorities.

        Returns (batch_data, indices, importance_weights).
        """
        indices = []
        priorities = []
        batch = []

        segment = self.tree.total() / batch_size
        for i in range(batch_size):
            low = segment * i
            high = segment * (i + 1)
            cum = np.random.uniform(low, high)
            idx, priority, data = self.tree.get(cum)
            indices.append(idx)
            priorities.append(priority)
            batch.append(data)

        # Importance sampling weights
        n = self.tree.size
        probs = np.array(priorities, dtype=np.float64) / max(self.tree.total(), 1e-8)
        weights = (n * probs) ** (-beta)
        weights /= weights.max()  # normalize

        states, place_feats_list, actions, rewards, next_states, next_place_feats_list, dones = zip(*batch)

        return (
            np.array(states),
            list(place_feats_list),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states),
            list(next_place_feats_list),
            np.array(dones, dtype=np.float32),
            indices,
            np.array(weights, dtype=np.float32),
        )

    def update_priorities(self, indices: List[int], td_errors: np.ndarray):
        """Update priorities based on TD-errors."""
        for idx, td_err in zip(indices, td_errors):
            p = (abs(td_err) + 1e-6) ** self.alpha
            self.tree.update_priority(idx, p)
            self.max_priority = max(self.max_priority, abs(td_err) + 1e-6)

    def __len__(self):
        return self.tree.size


# ======================================================================
# Standard (uniform) replay buffer
# ======================================================================

class ReplayBuffer:
    """Uniform experience replay buffer (fallback)."""

    def __init__(self, capacity: int = 200000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, place_feats, action, reward,
             next_state, next_place_feats, done):
        self.buffer.append((
            np.array(state, dtype=np.float32),
            np.array(place_feats, dtype=np.float32),
            int(action),
            float(reward),
            np.array(next_state, dtype=np.float32),
            np.array(next_place_feats, dtype=np.float32) if next_place_feats is not None else None,
            float(done),
        ))

    def sample(self, batch_size: int, beta: float = None):
        batch = random.sample(self.buffer, batch_size)
        states, place_feats_list, actions, rewards, next_states, next_place_feats_list, dones = zip(*batch)
        return (
            np.array(states),
            list(place_feats_list),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states),
            list(next_place_feats_list),
            np.array(dones, dtype=np.float32),
            None,  # no indices
            np.ones(len(batch), dtype=np.float32),  # uniform weights
        )

    def __len__(self):
        return len(self.buffer)


# ======================================================================
# Placement agent
# ======================================================================

class PlacementAgent:
    """DQN agent that evaluates placements instead of primitive actions.

    Supports:
    - True Double DQN (policy selects, target evaluates)
    - Prioritized Experience Replay with sum-tree
    - Beta annealing for importance-sampling correction
    """

    def __init__(
        self,
        state_size: int,
        hidden_sizes: list = None,
        lr: float = 1e-4,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.9998,
        batch_size: int = 128,
        buffer_size: int = 200000,
        target_update_freq: int = 1000,
        use_double_dqn: bool = True,
        use_per: bool = True,
        per_alpha: float = 0.6,
        per_beta_start: float = 0.4,
        per_beta_frames: int = 200000,
        use_noisy: bool = True,
        use_boltzmann: bool = True,
        boltzmann_temp_start: float = 1.0,
        boltzmann_temp_end: float = 0.1,
        boltzmann_temp_decay: float = 0.9999,
        device: str = None,
    ):
        self.state_size = state_size
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.use_double_dqn = use_double_dqn
        self.use_per = use_per
        self.use_noisy = use_noisy
        self.use_boltzmann = use_boltzmann
        self.boltzmann_temp = boltzmann_temp_start
        self.boltzmann_temp_end = boltzmann_temp_end
        self.boltzmann_temp_decay = boltzmann_temp_decay
        self.learn_steps = 0

        # Beta annealing: linearly increase from per_beta_start to 1.0
        self.per_beta_start = per_beta_start
        self.per_beta_frames = per_beta_frames

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        if hidden_sizes is None:
            hidden_sizes = [512, 256, 128]

        self.policy_net = PlacementNetwork(state_size, hidden_sizes,
                                           use_noisy=use_noisy).to(self.device)
        self.target_net = PlacementNetwork(state_size, hidden_sizes,
                                           use_noisy=use_noisy).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)
        self.loss_fn = nn.SmoothL1Loss(reduction='none')

        if use_per:
            self.memory = PrioritizedReplayBuffer(buffer_size, alpha=per_alpha)
        else:
            self.memory = ReplayBuffer(buffer_size)

    @property
    def per_beta(self):
        """Current beta value (annealed from 0.4 to 1.0)."""
        frac = min(1.0, self.learn_steps / max(self.per_beta_frames, 1))
        return self.per_beta_start + frac * (1.0 - self.per_beta_start)

    def select_placement(self, state: np.ndarray, placements: List[Placement],
                         current_type: str, next_type: str,
                         eval_mode: bool = False) -> int:
        """Choose a placement index.

        Exploration strategies (in priority order):
        1. If use_boltzmann: softmax sampling with temperature annealing
        2. Epsilon-greedy: random with probability epsilon
        3. Greedy: argmax Q-values

        During eval_mode, always greedy (no exploration).
        """
        n = len(placements)

        # Always greedy in eval mode
        if eval_mode:
            with torch.no_grad():
                state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                feats = np.array([placement_features(p, current_type, next_type)
                                  for p in placements])
                feats_t = torch.FloatTensor(feats).unsqueeze(0).to(self.device)
                q_values = self.policy_net(state_t, feats_t)
                return q_values.argmax(dim=1).item()

        # Epsilon-greedy fallback for pure random exploration
        if not self.use_boltzmann and random.random() < self.epsilon:
            return random.randint(0, n - 1)

        with torch.no_grad():
            state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            feats = np.array([placement_features(p, current_type, next_type)
                              for p in placements])
            feats_t = torch.FloatTensor(feats).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_t, feats_t).squeeze(0)

            if self.use_boltzmann:
                # Boltzmann (softmax) sampling with temperature
                temp = max(self.boltzmann_temp, 0.01)
                probs = F.softmax(q_values / temp, dim=0).cpu().numpy()
                # Clamp to avoid numerical issues
                probs = np.clip(probs, 1e-8, 1.0)
                probs /= probs.sum()
                return int(np.random.choice(n, p=probs))
            else:
                return q_values.argmax().item()

    def store(self, state, placements, current_type, next_type, action_idx,
              reward, next_state, next_placements, next_next_type, done):
        """Store a transition in replay memory."""
        place_feats = np.array([placement_features(p, current_type, next_type)
                                for p in placements])
        if next_placements is not None and len(next_placements) > 0:
            next_feats = np.array([placement_features(p, next_type, next_next_type)
                                   for p in next_placements])
        else:
            next_feats = None

        self.memory.push(state, place_feats, action_idx, reward,
                         next_state, next_feats, done)

    def can_train(self) -> bool:
        return len(self.memory) >= self.batch_size

    def train_step(self) -> Optional[float]:
        """One training step. Returns loss value or None."""
        if not self.can_train():
            return None

        beta = self.per_beta if self.use_per else 1.0
        (states, place_feats_list, actions, rewards,
         next_states, next_place_feats_list, dones,
         indices, is_weights) = self.memory.sample(self.batch_size, beta=beta)

        states_t = torch.FloatTensor(states).to(self.device)
        actions_t = torch.LongTensor(actions).to(self.device)
        rewards_t = torch.FloatTensor(rewards).to(self.device)
        dones_t = torch.FloatTensor(dones).to(self.device)
        is_weights_t = torch.FloatTensor(is_weights).to(self.device)

        # Current Q values: pick Q(s, chosen_placement)
        current_q = self._batch_q(self.policy_net, states_t, place_feats_list, actions_t)

        # Target Q values
        with torch.no_grad():
            if self.use_double_dqn:
                # True Double DQN: policy_net SELECTS action, target_net EVALUATES it
                best_actions = self._batch_argmax_actions(
                    self.policy_net, next_states, next_place_feats_list
                )
                next_q = self._batch_eval(
                    self.target_net, next_states, next_place_feats_list, best_actions
                )
            else:
                # Standard DQN: target_net does both
                next_q = self._batch_max_q(
                    self.target_net, next_states, next_place_feats_list
                )
            target_q = rewards_t + self.gamma * next_q * (1.0 - dones_t)

        # Per-sample TD errors (no reduction)
        td_errors = current_q - target_q
        per_sample_loss = self.loss_fn(current_q, target_q)

        # Weight by importance sampling and average
        weighted_loss = (per_sample_loss * is_weights_t).mean()

        self.optimizer.zero_grad()
        weighted_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()

        # Update priorities in PER
        if self.use_per and indices is not None:
            self.memory.update_priorities(
                indices, td_errors.detach().cpu().numpy()
            )

        self.learn_steps += 1
        if self.learn_steps % self.target_update_freq == 0:
            self._update_target()

        # Resample NoisyNet noise for next forward pass
        if self.use_noisy:
            self.policy_net.reset_noise()
            self.target_net.reset_noise()

        # Anneal exploration parameters
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        self.boltzmann_temp = max(
            self.boltzmann_temp_end,
            self.boltzmann_temp * self.boltzmann_temp_decay
        )

        return weighted_loss.item()

    def _batch_q(self, net, states, place_feats_list, actions):
        """Compute Q(s, a) for a batch where each sample has variable placements."""
        q_values = []
        for i in range(states.shape[0]):
            s = states[i].unsqueeze(0)
            pf = torch.FloatTensor(place_feats_list[i]).unsqueeze(0).to(self.device)
            q = net(s, pf).squeeze(0)
            q_values.append(q[actions[i]])
        return torch.stack(q_values)

    def _batch_argmax_actions(self, net, next_states_np, next_place_feats_list):
        """Select best placement index for each next state using the given net."""
        argmax_idxs = []
        for i in range(len(next_states_np)):
            if next_place_feats_list[i] is None:
                argmax_idxs.append(-1)
                continue
            s = torch.FloatTensor(next_states_np[i]).unsqueeze(0).to(self.device)
            pf = torch.FloatTensor(next_place_feats_list[i]).unsqueeze(0).to(self.device)
            q = net(s, pf).squeeze(0)
            argmax_idxs.append(q.argmax().item())
        return argmax_idxs

    def _batch_eval(self, net, next_states_np, next_place_feats_list, action_idxs):
        """Evaluate Q(s', a*) for each sample using the given net and provided action indices."""
        q_values = []
        for i in range(len(next_states_np)):
            if action_idxs[i] < 0:
                q_values.append(torch.tensor(0.0, device=self.device))
                continue
            s = torch.FloatTensor(next_states_np[i]).unsqueeze(0).to(self.device)
            pf = torch.FloatTensor(next_place_feats_list[i]).unsqueeze(0).to(self.device)
            q = net(s, pf).squeeze(0)
            q_values.append(q[action_idxs[i]])
        return torch.stack(q_values)

    def _batch_max_q(self, net, next_states_np, next_place_feats_list):
        """Compute max_a Q(s', a) for next states (standard DQN target)."""
        max_qs = []
        for i in range(len(next_states_np)):
            if next_place_feats_list[i] is None:
                max_qs.append(torch.tensor(0.0, device=self.device))
                continue
            s = torch.FloatTensor(next_states_np[i]).unsqueeze(0).to(self.device)
            pf = torch.FloatTensor(next_place_feats_list[i]).unsqueeze(0).to(self.device)
            q = net(s, pf).squeeze(0)
            max_qs.append(q.max())
        return torch.stack(max_qs)

    def _update_target(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def save(self, filepath: str):
        torch.save({
            'policy_net': self.policy_net.state_dict(),
            'target_net': self.target_net.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'learn_steps': self.learn_steps,
        }, filepath)

    def load(self, filepath: str):
        ckpt = torch.load(filepath, map_location=self.device)
        self.policy_net.load_state_dict(ckpt['policy_net'])
        self.target_net.load_state_dict(ckpt['target_net'])
        self.optimizer.load_state_dict(ckpt['optimizer'])
        self.epsilon = ckpt.get('epsilon', self.epsilon_end)
        self.learn_steps = ckpt.get('learn_steps', 0)
