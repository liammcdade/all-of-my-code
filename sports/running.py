#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNAKE-DQN  ·  GRASS GUI EDITION  ·  pure NumPy  ·  TURBO
=======================================================

A from-scratch Deep Q-Network learns to master Snake, on a proper
grassy playing field with a real apple and a proper snake.

NEW  ·  press  T  at any time to toggle TURBO:
        normal = 2 moves per frame   (visually smooth)
        turbo  = 6 moves per frame   (3× quicker, snap-update)
        The status line and the on-field HUD both show TURBO.

Visuals
-------
  * Grass field: base green + scattered tufts + flowers + checker.
  * Snake: rounded body segments, brighter head with two eyes that
    always look in the direction of travel.
  * Apple: red disc + highlight + brown stem + green leaf.
  * Death pause: short beat after each death so you SEE the failure.

Training
--------
  * Network, replay buffer, Adam — all hand-rolled in NumPy.
  * EVERYTHING checkpoints every 100 moves: online weights, target
    weights, Adam moments, the whole replay buffer, counters.
  * Ctrl-C / window-close is safe.  --resume continues exactly.

Usage
-----
    python snake_dqn_grass.py                  # fresh run, speed 2/frame
    python snake_dqn_grass.py --resume         # continue saved training
    python snake_dqn_grass.py --speed 1        # smooth glide, one cell/frame
    python snake_dqn_grass.py --speed 4        # 4 per frame normal, 12 turbo
    python snake_dqn_grass.py --grid 15        # larger field
    python snake_dqn_grass.py --no-save        # disable checkpoints

Keys
----
    T      toggle turbo (3× faster)
    Q      quit (also closing the window)

Deps: numpy + matplotlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, Ellipse, Rectangle


# ======================================================================
#  CONSTANTS
# ======================================================================
STATE_SIZE  = 11
ACTION_SIZE = 4
DIRS        = [(0, -1), (1, 0), (0, 1), (-1, 0)]   # up, right, down, left

DEFAULT_CKPT = "snake_dqn.npz"
DEFAULT_LOG  = "snake_dqn_log.json"
REPLAY_CAP   = 20000

TURBO_MULT   = 3            # turbo moves per frame = normal × TURBO_MULT


# ======================================================================
#  ENVIRONMENT
# ======================================================================
class SnakeEnv:
    def __init__(self, grid: int = 12, seed: int | None = None):
        self.grid = int(grid)
        self.rng  = np.random.default_rng(seed)
        self.max_steps_no_food = grid * grid
        self.reset()

    def reset(self):
        c = self.grid // 2
        self.snake            = [(c, c), (c - 1, c), (c - 2, c)]
        self.direction        = 1
        self.score            = 0
        self.steps            = 0
        self.steps_since_food = 0
        self.done             = False
        self._place_food()
        return self._state()

    def _place_food(self):
        occupied = set(self.snake)
        free = [(x, y) for x in range(self.grid) for y in range(self.grid)
                if (x, y) not in occupied]
        self.food = None if not free else free[int(self.rng.integers(len(free)))]

    def legal_actions(self):
        return [a for a in range(ACTION_SIZE) if (a + 2) % 4 != self.direction]

    def _state(self):
        hx, hy = self.snake[0]
        d_vec = DIRS[self.direction]
        r_vec = DIRS[(self.direction + 1) % 4]
        l_vec = DIRS[(self.direction - 1) % 4]
        body = set(self.snake[:-1])

        def danger(d):
            nx, ny = hx + d[0], hy + d[1]
            if not (0 <= nx < self.grid and 0 <= ny < self.grid):
                return 1.0
            return 1.0 if (nx, ny) in body else 0.0

        if self.food is None:
            fu = fd = fl = fr = 0.0
        else:
            fx, fy = self.food
            fu = 1.0 if fy < hy else 0.0
            fd = 1.0 if fy > hy else 0.0
            fl = 1.0 if fx < hx else 0.0
            fr = 1.0 if fx > hx else 0.0

        return np.array([
            danger(d_vec), danger(r_vec), danger(l_vec),
            1.0 if self.direction == 0 else 0.0,
            1.0 if self.direction == 1 else 0.0,
            1.0 if self.direction == 2 else 0.0,
            1.0 if self.direction == 3 else 0.0,
            fu, fd, fl, fr,
        ], dtype=np.float32)

    def step(self, action):
        if self.done:
            return self._state(), 0.0, True, self.score

        action = int(action)
        if (action + 2) % 4 == self.direction:
            action = self.direction
        self.direction = action

        dx, dy = DIRS[action]
        hx, hy = self.snake[0]
        nx, ny = hx + dx, hy + dy

        self.steps += 1
        self.steps_since_food += 1

        if not (0 <= nx < self.grid and 0 <= ny < self.grid):
            self.done = True
            return self._state(), -10.0, True, self.score
        if (nx, ny) in self.snake[:-1]:
            self.done = True
            return self._state(), -10.0, True, self.score

        self.snake.insert(0, (nx, ny))

        if self.food is not None and (nx, ny) == self.food:
            self.score += 1
            reward = 10.0
            self.steps_since_food = 0
            self._place_food()
            if self.food is None:
                self.done = True
                return self._state(), reward + 100.0, True, self.score
        else:
            self.snake.pop()
            reward = -0.01

        if self.steps_since_food > self.max_steps_no_food:
            self.done = True
            return self._state(), -10.0, True, self.score

        return self._state(), reward, False, self.score


# ======================================================================
#  REPLAY BUFFER
# ======================================================================
class ReplayBuffer:
    def __init__(self, capacity, state_size=STATE_SIZE):
        self.capacity = int(capacity)
        self.states      = np.zeros((capacity, state_size), dtype=np.float32)
        self.actions     = np.zeros(capacity, dtype=np.int64)
        self.rewards     = np.zeros(capacity, dtype=np.float32)
        self.next_states = np.zeros((capacity, state_size), dtype=np.float32)
        self.dones       = np.zeros(capacity, dtype=np.bool_)
        self.ptr  = 0
        self.size = 0

    def append(self, s, a, r, s2, d):
        i = self.ptr
        self.states[i]      = s
        self.actions[i]     = a
        self.rewards[i]     = r
        self.next_states[i] = s2
        self.dones[i]       = d
        self.ptr = (self.ptr + 1) % self.capacity
        if self.size < self.capacity:
            self.size += 1

    def __len__(self):
        return self.size

    def sample(self, batch_size, rng):
        idx = rng.choice(self.size, size=batch_size, replace=False)
        return (self.states[idx], self.actions[idx], self.rewards[idx],
                self.next_states[idx], self.dones[idx])


# ======================================================================
#  DQN  —  pure NumPy
# ======================================================================
class DQN:
    def __init__(self, state_size=STATE_SIZE, action_size=ACTION_SIZE,
                 hidden=128, seed=0):
        rng = np.random.default_rng(seed)
        self.state_size  = state_size
        self.action_size = action_size

        self.W1 = (rng.standard_normal((state_size, hidden))
                   .astype(np.float32) * np.float32(np.sqrt(2.0 / state_size)))
        self.b1 = np.zeros(hidden, dtype=np.float32)
        self.W2 = (rng.standard_normal((hidden, hidden))
                   .astype(np.float32) * np.float32(np.sqrt(2.0 / hidden)))
        self.b2 = np.zeros(hidden, dtype=np.float32)
        self.W3 = (rng.standard_normal((hidden, action_size))
                   .astype(np.float32) * np.float32(np.sqrt(2.0 / hidden)))
        self.b3 = np.zeros(action_size, dtype=np.float32)

        self.m = {k: np.zeros_like(v) for k, v in self._params().items()}
        self.v = {k: np.zeros_like(v) for k, v in self._params().items()}
        self.t = 0

    def _params(self):
        return {"W1": self.W1, "b1": self.b1,
                "W2": self.W2, "b2": self.b2,
                "W3": self.W3, "b3": self.b3}

    def forward(self, X):
        z1 = X @ self.W1 + self.b1
        a1 = np.maximum(z1, 0.0)
        z2 = a1 @ self.W2 + self.b2
        a2 = np.maximum(z2, 0.0)
        q  = a2 @ self.W3 + self.b3
        return q, (X, z1, a1, z2, a2)

    def predict(self, X):
        q, _ = self.forward(X)
        return q

    def train_step(self, states, actions, targets,
                   lr=5e-4, beta1=0.9, beta2=0.999, eps=1e-8):
        batch = states.shape[0]
        q, (X, z1, a1, z2, a2) = self.forward(states)

        idx = np.arange(batch)
        diff = q[idx, actions] - targets
        loss = float(np.mean(diff * diff))

        dq = np.zeros_like(q)
        dq[idx, actions] = (2.0 * diff) / batch

        dW3 = a2.T @ dq
        db3 = dq.sum(axis=0)
        da2 = dq @ self.W3.T
        dz2 = da2 * (z2 > 0.0)
        dW2 = a1.T @ dz2
        db2 = dz2.sum(axis=0)
        da1 = dz2 @ self.W2.T
        dz1 = da1 * (z1 > 0.0)
        dW1 = X.T @ dz1
        db1 = dz1.sum(axis=0)

        grads = {"W1": dW1, "b1": db1,
                 "W2": dW2, "b2": db2,
                 "W3": dW3, "b3": db3}

        self.t += 1
        b1t = 1.0 - beta1 ** self.t
        b2t = 1.0 - beta2 ** self.t
        params = self._params()
        for k, g in grads.items():
            self.m[k] = beta1 * self.m[k] + (1.0 - beta1) * g
            self.v[k] = beta2 * self.v[k] + (1.0 - beta2) * (g * g)
            m_hat = self.m[k] / b1t
            v_hat = self.v[k] / b2t
            params[k] -= (lr * m_hat / (np.sqrt(v_hat) + eps)).astype(params[k].dtype)

        return loss

    def copy_from(self, other):
        for k in ("W1", "b1", "W2", "b2", "W3", "b3"):
            getattr(self, k)[...] = getattr(other, k)

    def state_dict(self):
        d = {}
        for k, v in self._params().items():
            d[k] = v
        for k, v in self.m.items():
            d["m_" + k] = v
        for k, v in self.v.items():
            d["v_" + k] = v
        d["t"] = np.array(self.t, dtype=np.int64)
        return d

    def load_state_dict(self, d):
        for k in ("W1", "b1", "W2", "b2", "W3", "b3"):
            getattr(self, k)[...] = d[k].astype(np.float32)
            self.m[k] = d["m_" + k].astype(np.float32).copy()
            self.v[k] = d["v_" + k].astype(np.float32).copy()
        self.t = int(d["t"])


# ======================================================================
#  CHECKPOINTING
# ======================================================================
def save_checkpoint(path, online, target, replay, meta):
    arrays = dict(online.state_dict())
    arrays["tW1"] = target.W1; arrays["tb1"] = target.b1
    arrays["tW2"] = target.W2; arrays["tb2"] = target.b2
    arrays["tW3"] = target.W3; arrays["tb3"] = target.b3

    n = len(replay)
    if n == replay.capacity:
        arrays["r_s"], arrays["r_a"], arrays["r_r"] = (
            replay.states, replay.actions, replay.rewards)
        arrays["r_s2"], arrays["r_d"] = replay.next_states, replay.dones
    elif n > 0:
        arrays["r_s"]  = replay.states[:n]
        arrays["r_a"]  = replay.actions[:n]
        arrays["r_r"]  = replay.rewards[:n]
        arrays["r_s2"] = replay.next_states[:n]
        arrays["r_d"]  = replay.dones[:n]
    else:
        arrays["r_s"]  = np.zeros((0, STATE_SIZE), dtype=np.float32)
        arrays["r_a"]  = np.zeros(0, dtype=np.int64)
        arrays["r_r"]  = np.zeros(0, dtype=np.float32)
        arrays["r_s2"] = np.zeros((0, STATE_SIZE), dtype=np.float32)
        arrays["r_d"]  = np.zeros(0, dtype=np.bool_)

    arrays["meta"] = np.array([
        meta.get("episode", 0), meta.get("total_steps", 0),
        meta.get("epsilon", 1.0), meta.get("best_score", 0),
        meta.get("total_episodes", 0), meta.get("total_episode_steps", 0),
    ], dtype=np.float64)

    tmp = path + ".tmp.npz"
    np.savez(tmp, **arrays)
    os.replace(tmp, path)


def load_checkpoint(path, online, target):
    data = np.load(path, allow_pickle=False)
    online.load_state_dict({
        "W1": data["W1"], "b1": data["b1"],
        "W2": data["W2"], "b2": data["b2"],
        "W3": data["W3"], "b3": data["b3"],
        "m_W1": data["m_W1"], "m_b1": data["m_b1"],
        "m_W2": data["m_W2"], "m_b2": data["m_b2"],
        "m_W3": data["m_W3"], "m_b3": data["m_b3"],
        "v_W1": data["v_W1"], "v_b1": data["v_b1"],
        "v_W2": data["v_W2"], "v_b2": data["v_b2"],
        "v_W3": data["v_W3"], "v_b3": data["v_b3"],
        "t":    data["t"],
    })
    for k_src, k_dst in (("tW1","W1"),("tb1","b1"),
                         ("tW2","W2"),("tb2","b2"),
                         ("tW3","W3"),("tb3","b3")):
        getattr(target, k_dst)[...] = data[k_src]

    replay = ReplayBuffer(REPLAY_CAP)
    s_arr, a_arr, r_arr = data["r_s"], data["r_a"], data["r_r"]
    s2_arr, d_arr       = data["r_s2"], data["r_d"]
    for i in range(len(s_arr)):
        replay.append(s_arr[i], int(a_arr[i]), float(r_arr[i]),
                      s2_arr[i], bool(d_arr[i]))

    m = data["meta"]
    meta = {
        "episode":             int(m[0]),
        "total_steps":         int(m[1]),
        "epsilon":             float(m[2]),
        "best_score":          int(m[3]),
        "total_episodes":      int(m[4]),
        "total_episode_steps": int(m[5]),
    }
    return replay, meta


# ======================================================================
#  TRAINER
# ======================================================================
class Trainer:
    def __init__(self, args):
        self.args = args
        self.env  = SnakeEnv(grid=args.grid, seed=args.seed)
        self.online = DQN(seed=args.seed + 1)
        self.target = DQN(seed=args.seed + 2)
        self.target.copy_from(self.online)

        self.replay = ReplayBuffer(REPLAY_CAP)
        self.meta = {"episode": 0, "total_steps": 0, "epsilon": 1.0,
                     "best_score": 0, "total_episodes": 0,
                     "total_episode_steps": 0}
        self.score_history: list[int] = []

        if args.resume and os.path.exists(args.ckpt):
            self.replay, self.meta = load_checkpoint(
                args.ckpt, self.online, self.target)
            if os.path.exists(args.log):
                try:
                    with open(args.log) as f:
                        self.score_history = json.load(f)
                except Exception:
                    self.score_history = []

        self.state      = self.env.reset()
        self.ep_reward  = 0.0
        self.last_loss  = 0.0
        self.loss_ema   = 0.0
        self.last_save_step = self.meta["total_steps"]
        self.saves      = 0
        self.episodes_this_session = 0
        self.start_time = time.time()
        self.finished   = False

        self.np_rng = np.random.default_rng(args.seed + 99)

    # ------------------------------------------------------------------
    def step_once(self):
        if self.finished:
            return False

        if self.env.done:
            self._end_episode()
            if self.finished:
                return False
            self.state     = self.env.reset()
            self.ep_reward = 0.0

        legal = self.env.legal_actions()
        eps   = self.meta["epsilon"]
        if self.np_rng.random() < eps:
            action = int(legal[int(self.np_rng.integers(len(legal)))])
        else:
            q = self.online.predict(self.state[None, :])[0].copy()
            for a_idx in range(ACTION_SIZE):
                if a_idx not in legal:
                    q[a_idx] = -1e9
            action = int(np.argmax(q))

        s2, r, done, score = self.env.step(action)
        self.replay.append(self.state, action, r, s2, done)
        self.state = s2
        self.ep_reward += r
        self.meta["total_steps"] += 1
        steps = self.meta["total_steps"]

        a = self.args
        if len(self.replay) >= a.batch and steps % a.update_every == 0:
            s_b, a_b, r_b, s2_b, d_b = self.replay.sample(a.batch, self.np_rng)
            q_next = self.target.predict(s2_b)
            max_q  = q_next.max(axis=1)
            tgt    = r_b + a.gamma * max_q * (~d_b).astype(np.float32)
            loss   = self.online.train_step(s_b, a_b, tgt, lr=a.lr)
            self.last_loss = loss
            self.loss_ema  = (0.99 * self.loss_ema + 0.01 * loss
                              if self.loss_ema else loss)

        if steps % a.target_update == 0:
            self.target.copy_from(self.online)

        if (not a.no_save) and steps - self.last_save_step >= a.save_every:
            self._save()
            self.last_save_step = steps

        return done

    # ------------------------------------------------------------------
    def _end_episode(self):
        score = self.env.score
        self.score_history.append(int(score))
        self.episodes_this_session += 1

        m = self.meta
        m["episode"] += 1
        m["total_episodes"] += 1
        m["total_episode_steps"] += self.env.steps
        if score > m["best_score"]:
            m["best_score"] = int(score)

        m["epsilon"] = max(self.args.eps_min,
                           m["epsilon"] * self.args.eps_decay)

        if (self.args.episodes > 0
                and self.episodes_this_session >= self.args.episodes):
            self.finished = True

    # ------------------------------------------------------------------
    def _save(self):
        if self.args.no_save:
            return
        save_checkpoint(self.args.ckpt, self.online, self.target,
                        self.replay, self.meta)
        with open(self.args.log, "w") as f:
            json.dump(self.score_history, f)
        self.saves += 1

    def final_save(self):
        self._save()

    def stats(self):
        h = self.score_history
        n = len(h)
        return {
            "episode":     self.meta["episode"],
            "total_steps": self.meta["total_steps"],
            "epsilon":     self.meta["epsilon"],
            "best":        self.meta["best_score"],
            "avg_all":     float(np.mean(h)) if n else 0.0,
            "avg_100":     float(np.mean(h[-100:])) if h else 0.0,
            "avg_20":      float(np.mean(h[-20:])) if h else 0.0,
            "replay":      len(self.replay),
            "loss":        self.last_loss,
            "loss_ema":    self.loss_ema,
            "saves":       self.saves,
            "elapsed":     time.time() - self.start_time,
            "finished":    self.finished,
        }


# ======================================================================
#  GRASS-FIELD RENDERER
# ======================================================================
class GrassRenderer:
    def __init__(self, ax, grid):
        self.ax   = ax
        self.grid = grid

        ax.set_xlim(-0.5, grid - 0.5)
        ax.set_ylim(grid - 0.5, -0.5)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)

        self._draw_grass()

        # body pool
        self.body_patches = []
        for _ in range(grid * grid):
            c = Circle((0, 0), radius=0.40,
                       facecolor="#2f9e44", edgecolor="#0e3a17",
                       linewidth=1.2, zorder=4)
            c.set_visible(False)
            ax.add_patch(c)
            self.body_patches.append(c)

        # head
        self.head = Circle((0, 0), radius=0.48,
                           facecolor="#4ecb5a", edgecolor="#0e3a17",
                           linewidth=1.6, zorder=6)
        self.head.set_visible(False)
        ax.add_patch(self.head)

        self.eye_w = [Circle((0, 0), radius=0.13, facecolor="white",
                             edgecolor="none", zorder=8) for _ in range(2)]
        self.eye_p = [Circle((0, 0), radius=0.06, facecolor="#101010",
                             edgecolor="none", zorder=9) for _ in range(2)]
        for e in self.eye_w + self.eye_p:
            e.set_visible(False)
            ax.add_patch(e)

        # apple
        self.apple_body = Circle((0, 0), radius=0.36,
                                 facecolor="#e03131",
                                 edgecolor="#7a0f0f",
                                 linewidth=1.2, zorder=5)
        self.apple_body.set_visible(False)
        ax.add_patch(self.apple_body)

        self.apple_shine = Circle((0, 0), radius=0.10,
                                  facecolor="#ffb8b8",
                                  edgecolor="none", alpha=0.85, zorder=6)
        self.apple_shine.set_visible(False)
        ax.add_patch(self.apple_shine)

        self.apple_stem, = ax.plot([], [], color="#6b3f1a",
                                   lw=2.4, zorder=6,
                                   solid_capstyle="round")
        self.apple_leaf = Ellipse((0, 0), width=0.28, height=0.14,
                                  angle=35, facecolor="#3aa03a",
                                  edgecolor="#134a13", linewidth=0.8,
                                  zorder=6)
        self.apple_leaf.set_visible(False)
        ax.add_patch(self.apple_leaf)

        # HUD on the field
        self.score_text = ax.text(
            -0.35, -0.35, "", color="#f8f8d8",
            fontsize=15, fontweight="bold", family="monospace",
            ha="left", va="top", zorder=20)
        self.turbo_text = ax.text(
            grid - 0.35, -0.35, "", color="#ff3030",
            fontsize=15, fontweight="bold", family="monospace",
            ha="right", va="top", zorder=20)

    # ------------------------------------------------------------------
    def _draw_grass(self):
        ax = self.ax
        G  = self.grid

        ax.add_patch(Rectangle((-0.5, -0.5), G, G,
                               facecolor="#3a8a4a",
                               edgecolor="none", zorder=0))

        for y in range(G):
            for x in range(G):
                if (x + y) % 2 == 0:
                    ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1,
                                           facecolor="#41a053",
                                           edgecolor="none", zorder=1))

        rng = np.random.default_rng(20240513)
        n   = 400
        segs   = []
        colors = []
        palette = ["#2c6e38", "#54b064", "#26602f", "#68c078"]
        for _ in range(n):
            x = rng.uniform(-0.5, G - 0.5)
            y = rng.uniform(-0.5, G - 0.5)
            h = rng.uniform(0.10, 0.22)
            w = rng.uniform(-0.06, 0.06)
            segs.append([(x, y), (x + w, y - h)])
            colors.append(palette[int(rng.integers(len(palette)))])
        lc = LineCollection(segs, colors=colors, linewidths=0.9,
                            capstyle="round", zorder=2)
        ax.add_collection(lc)

        for _ in range(25):
            x = rng.uniform(-0.4, G - 0.6)
            y = rng.uniform(-0.4, G - 0.6)
            col = ["#ffe066", "#ff9ec0", "#e0f0ff"][int(rng.integers(3))]
            ax.add_patch(Circle((x, y), 0.05, facecolor=col,
                                edgecolor="none", zorder=2))

        ax.add_patch(Rectangle((-0.5, -0.5), G, G, fill=False,
                               edgecolor="#0e3a17", linewidth=3.0,
                               zorder=10))

    # ------------------------------------------------------------------
    def draw_snake(self, visual_positions, direction):
        n = len(visual_positions)

        for i, patch in enumerate(self.body_patches):
            if i < n - 1:
                vx, vy = visual_positions[i + 1]
                patch.set_center((vx, vy))
                patch.set_visible(True)
            else:
                patch.set_visible(False)

        if n == 0:
            self.head.set_visible(False)
            for e in self.eye_w + self.eye_p:
                e.set_visible(False)
            return

        hx, hy = visual_positions[0]
        self.head.set_center((hx, hy))
        self.head.set_visible(True)

        dx, dy = DIRS[direction]
        px, py = -dy, dx

        eye_fwd, eye_side = 0.14, 0.17
        for i, sgn in enumerate((+1, -1)):
            ex = hx + eye_fwd * dx + sgn * eye_side * px
            ey = hy + eye_fwd * dy + sgn * eye_side * py
            self.eye_w[i].set_center((ex, ey))
            self.eye_w[i].set_visible(True)
            self.eye_p[i].set_center((ex + 0.02 * dx, ey + 0.02 * dy))
            self.eye_p[i].set_visible(True)

    # ------------------------------------------------------------------
    def draw_apple(self, food):
        if food is None:
            self.apple_body.set_visible(False)
            self.apple_shine.set_visible(False)
            self.apple_leaf.set_visible(False)
            self.apple_stem.set_data([], [])
            return

        fx, fy = food
        self.apple_body.set_center((fx, fy))
        self.apple_body.set_visible(True)

        self.apple_shine.set_center((fx - 0.12, fy - 0.13))
        self.apple_shine.set_visible(True)

        self.apple_stem.set_data([fx, fx + 0.02], [fy - 0.34, fy - 0.52])

        self.apple_leaf.set_center((fx + 0.12, fy - 0.48))
        self.apple_leaf.set_visible(True)

    # ------------------------------------------------------------------
    def set_hud(self, score, episode, epsilon, best, turbo):
        self.score_text.set_text(
            f"score {score:>2}   ep {episode:>5}   "
            f"best {best:>3}   eps {epsilon:.2f}")
        if turbo:
            self.turbo_text.set_text(">> TURBO 6x/frame <<")
        else:
            self.turbo_text.set_text("")


# ======================================================================
#  MAIN
# ======================================================================
def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--grid",          type=int,   default=12)
    ap.add_argument("--episodes",      type=int,   default=0,
                    help="episodes this session (0 = unlimited)")
    ap.add_argument("--resume",        action="store_true")
    ap.add_argument("--no-save",       action="store_true")
    ap.add_argument("--ckpt",          type=str,   default=DEFAULT_CKPT)
    ap.add_argument("--log",           type=str,   default=DEFAULT_LOG)
    ap.add_argument("--save-every",    type=int,   default=100,
                    help="checkpoint every N moves")
    ap.add_argument("--speed",         type=int,   default=2,
                    help="normal moves per frame "
                         "(turbo multiplies by 3)")
    ap.add_argument("--fps",           type=int,   default=30)
    ap.add_argument("--batch",         type=int,   default=64)
    ap.add_argument("--lr",            type=float, default=5e-4)
    ap.add_argument("--gamma",         type=float, default=0.95)
    ap.add_argument("--eps-min",       type=float, default=0.01)
    ap.add_argument("--eps-decay",     type=float, default=0.9985)
    ap.add_argument("--update-every",  type=int,   default=2)
    ap.add_argument("--target-update", type=int,   default=500)
    ap.add_argument("--seed",          type=int,   default=0)
    args = ap.parse_args()

    np.random.seed(args.seed)
    random.seed(args.seed)

    trainer = Trainer(args)

    # smooth glide only when the user asks for speed 1
    smooth_mode = args.speed <= 1
    alpha       = 0.35
    settle_tol  = 0.15

    normal_moves = args.speed
    turbo_moves  = args.speed * TURBO_MULT

    # ==================================================================
    #  FIGURE
    # ==================================================================
    fig = plt.figure(figsize=(14, 8), facecolor="#0b0e12")
    gs  = fig.add_gridspec(
        2, 2, width_ratios=[1.15, 1.0], height_ratios=[1.0, 1.0],
        left=0.04, right=0.97, top=0.92, bottom=0.06,
        hspace=0.30, wspace=0.18,
    )
    ax_game  = fig.add_subplot(gs[:, 0])
    ax_curve = fig.add_subplot(gs[0, 1])
    ax_stats = fig.add_subplot(gs[1, 1])
    ax_stats.axis("off")

    ax_game.set_facecolor("#0b0e12")
    ax_curve.set_facecolor("#0b0e12")
    ax_stats.set_facecolor("#0b0e12")

    fig.suptitle(
        "DQN SNAKE  ·  grass field  ·  pure-NumPy deep Q-learning  ·  "
        f"checkpoint every {args.save_every} moves  ·  "
        "press  T  for turbo",
        color="#f0f4f8", fontsize=12.5, fontweight="bold")

    renderer = GrassRenderer(ax_game, args.grid)

    # curve
    ax_curve.tick_params(colors="#708090")
    for sp in ax_curve.spines.values():
        sp.set_color("#303840")
    ax_curve.set_xlabel("episode", color="#90a0b0", fontsize=9)
    ax_curve.set_ylabel("score",   color="#90a0b0", fontsize=9)
    ax_curve.set_title("score per episode  (raw + running mean)",
                       color="#a0b0c0", fontsize=10)
    ax_curve.grid(True, color="#182030", lw=0.6)
    line_raw, = ax_curve.plot([], [], color="#3060ff", lw=0.6, alpha=0.45,
                              label="raw")
    line_avg, = ax_curve.plot([], [], color="#ffd040", lw=1.8,
                              label="running mean")
    ax_curve.legend(loc="upper left", fontsize=8, facecolor="#0b0e12",
                    edgecolor="#303840", labelcolor="#c0d0e0")

    stats_text = ax_stats.text(
        0.02, 0.98, "", transform=ax_stats.transAxes,
        color="#c8d8e8", fontsize=11, va="top", family="monospace")
    status_text = ax_stats.text(
        0.02, 0.02, "", transform=ax_stats.transAxes,
        color="#8090a0", fontsize=9, va="bottom", family="monospace")

    # ==================================================================
    #  VISUAL STATE + TURBO TOGGLE
    # ==================================================================
    logical = list(trainer.env.snake)
    visual  = [list(map(float, c)) for c in logical]
    state   = {"death_pause": 0}
    turbo   = {"on": False}

    def visuals_settled():
        if len(visual) != len(logical):
            return False
        for (vx, vy), (lx, ly) in zip(visual, logical):
            if abs(vx - lx) > settle_tol or abs(vy - ly) > settle_tol:
                return False
        return True

    def update_visuals(a):
        new_vis = []
        for i, (lx, ly) in enumerate(logical):
            if i < len(visual):
                vx, vy = visual[i]
            else:
                vx, vy = float(lx), float(ly)
            new_vis.append([vx + (lx - vx) * a, vy + (ly - vy) * a])
        visual[:] = new_vis

    # ---------------- keyboard ----------------
    def on_key(event):
        if event.key in ("t", "T"):
            turbo["on"] = not turbo["on"]
            flag = "TURBO ON" if turbo["on"] else "TURBO OFF"
            print(f"[key] {flag}  ({normal_moves}/frame → "
                  f"{turbo_moves if turbo['on'] else normal_moves}/frame)")
        elif event.key in ("q", "Q", "escape"):
            plt.close(fig)

    fig.canvas.mpl_connect("key_press_event", on_key)

    # ==================================================================
    #  ANIMATION
    # ==================================================================
    interval_ms = max(10, int(1000 / max(1, args.fps)))

    def update(_):
        turbo_on = turbo["on"]
        # snap mode whenever base speed > 1 OR turbo is on
        snap_mode = (not smooth_mode) or turbo_on
        moves_this_frame = turbo_moves if turbo_on else normal_moves

        # ---- death pause ----
        if trainer.env.done:
            if state["death_pause"] < 12:
                state["death_pause"] += 1
            else:
                state["death_pause"] = 0
                trainer.step_once()
                logical[:] = list(trainer.env.snake)
                visual[:]  = [list(map(float, c)) for c in logical]
        else:
            if snap_mode:
                for _ in range(moves_this_frame):
                    if trainer.env.done:
                        break
                    trainer.step_once()
                logical[:] = list(trainer.env.snake)
                visual[:]  = [list(map(float, c)) for c in logical]
            else:
                # smooth glide — one move per settled visual
                if visuals_settled():
                    trainer.step_once()
                    logical[:] = list(trainer.env.snake)

        update_visuals(1.0 if snap_mode else alpha)

        # ---- draw ----
        renderer.draw_snake(visual, trainer.env.direction)
        renderer.draw_apple(trainer.env.food)
        renderer.set_hud(trainer.env.score,
                         trainer.meta["episode"],
                         trainer.meta["epsilon"],
                         trainer.meta["best_score"],
                         turbo_on)

        # ---- curve ----
        h = trainer.score_history
        if h:
            n = len(h)
            ys = np.asarray(h, dtype=np.float32)
            line_raw.set_data(np.arange(n), ys)
            win = max(1, min(50, n))
            k = np.ones(win, dtype=np.float32) / win
            smooth = np.convolve(ys, k, mode="valid")
            line_avg.set_data(np.arange(len(smooth)), smooth)
            ax_curve.relim()
            ax_curve.autoscale_view()
            ax_curve.set_xlim(0, max(10, n))

        # ---- stats ----
        s = trainer.stats()
        stats_text.set_text(
            f"episode         {s['episode']:>7}\n"
            f"total moves     {s['total_steps']:>7}\n"
            f"epsilon         {s['epsilon']:>7.3f}\n"
            f"best score      {s['best']:>7}\n"
            f"avg score (20)  {s['avg_20']:>7.2f}\n"
            f"avg score (100) {s['avg_100']:>7.2f}\n"
            f"avg score (all) {s['avg_all']:>7.2f}\n"
            f"replay buffer   {s['replay']:>7}\n"
            f"last loss       {s['loss']:>7.4f}\n"
            f"loss EMA        {s['loss_ema']:>7.4f}\n"
            f"checkpoints     {s['saves']:>7}\n"
            f"elapsed         {s['elapsed']:>7.1f}s")

        if s["finished"]:
            status_text.set_text("FINISHED — close the window")
        else:
            mode = (f"TURBO {turbo_moves}/frame"
                    if turbo_on
                    else (f"glide {normal_moves}/frame"
                          if smooth_mode
                          else f"normal {normal_moves}/frame"))
            status_text.set_text(
                f"[T] toggle turbo  ·  [Q] quit  ·  now: {mode}  ·  "
                f"checkpoint -> "
                f"{args.ckpt if not args.no_save else '(disabled)'}")

        return ()

    anim = FuncAnimation(   # noqa: F841
        fig, update, interval=interval_ms, blit=False,
        cache_frame_data=False)

    def on_close(_evt):
        trainer.final_save()
        print("[GUI] final checkpoint saved.")

    fig.canvas.mpl_connect("close_event", on_close)

    print(f"[GUI] grid={args.grid}  batch={args.batch}  lr={args.lr}")
    print(f"[GUI] normal = {normal_moves}/frame  ·  "
          f"turbo = {turbo_moves}/frame  (press T to toggle)")
    print(f"[GUI] initial mode: "
          f"{'smooth glide' if smooth_mode else f'snap {normal_moves}/frame'}")
    if trainer.meta["total_steps"] > 0:
        print(f"[GUI] resumed from {args.ckpt}  "
              f"episode={trainer.meta['episode']}  "
              f"best={trainer.meta['best_score']}  "
              f"steps={trainer.meta['total_steps']}")

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        trainer.final_save()


if __name__ == "__main__":
    main()