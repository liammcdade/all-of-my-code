"""
Chess RL — pure terminal PPO self-play trainer. No GUI, no pygame.

Run:  python chess_ppo.py
Stop: Ctrl-C (autosaves on exit)

Deps: pip install python-chess numpy torch
"""

import collections
import os
import random
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical
import chess

torch.set_num_threads(1)
random.seed(0)
np.random.seed(0)
torch.manual_seed(0)

CKPT = "chess_ppo_ckpt.pt"
ACTION_DIM = 4096
PLANES = 18
WINDOW = 25
EVAL_INTERVAL = 25
EVAL_GAMES = 5
MAX_PLIES = 400
LOG_EVERY = 3.0          # seconds between terminal status updates
AUTOSAVE_EVERY = 50      # episodes


# =============================================================================
# Encoding
# =============================================================================
_PIECE_ORDER = [chess.PAWN, chess.KNIGHT, chess.BISHOP,
                chess.ROOK, chess.QUEEN, chess.KING]


def encode_board(board):
    p = np.zeros((PLANES, 8, 8), dtype=np.float32)
    for i, pt in enumerate(_PIECE_ORDER):
        for sq in board.pieces(pt, chess.WHITE):
            p[i, sq >> 3, sq & 7] = 1.0
        for sq in board.pieces(pt, chess.BLACK):
            p[6 + i, sq >> 3, sq & 7] = 1.0
    if board.turn == chess.WHITE:
        p[12, :, :] = 1.0
    if board.has_kingside_castling_rights(chess.WHITE):
        p[13, :, :] = 1.0
    if board.has_queenside_castling_rights(chess.WHITE):
        p[14, :, :] = 1.0
    if board.has_kingside_castling_rights(chess.BLACK):
        p[15, :, :] = 1.0
    if board.has_queenside_castling_rights(chess.BLACK):
        p[16, :, :] = 1.0
    if board.ep_square is not None:
        p[17, board.ep_square >> 3, board.ep_square & 7] = 1.0
    return p


def legal_mask(board):
    m = np.zeros(ACTION_DIM, dtype=bool)
    for mv in board.legal_moves:
        m[mv.from_square * 64 + mv.to_square] = True
    return m


def idx_to_move(idx, board):
    f, t = idx // 64, idx % 64
    for m in board.legal_moves:
        if m.from_square == f and m.to_square == t:
            return m
    return None


# =============================================================================
# Network
# =============================================================================
class ResBlock(nn.Module):
    def __init__(self, ch):
        super().__init__()
        self.c1 = nn.Conv2d(ch, ch, 3, padding=1, bias=False)
        self.b1 = nn.BatchNorm2d(ch)
        self.c2 = nn.Conv2d(ch, ch, 3, padding=1, bias=False)
        self.b2 = nn.BatchNorm2d(ch)

    def forward(self, x):
        y = F.relu(self.b1(self.c1(x)))
        y = self.b2(self.c2(y))
        return F.relu(x + y)


class ChessNet(nn.Module):
    def __init__(self, ch=48, blocks=1):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(PLANES, ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(ch), nn.ReLU(inplace=True))
        self.tower = nn.Sequential(*[ResBlock(ch) for _ in range(blocks)])
        self.p_conv = nn.Conv2d(ch, 32, 1, bias=False)
        self.p_bn = nn.BatchNorm2d(32)
        self.p_fc = nn.Linear(32 * 64, ACTION_DIM)
        self.v_conv = nn.Conv2d(ch, 8, 1, bias=False)
        self.v_bn = nn.BatchNorm2d(8)
        self.v_fc1 = nn.Linear(8 * 64, 128)
        self.v_fc2 = nn.Linear(128, 1)

    def forward(self, x):
        h = self.tower(self.stem(x))
        p = F.relu(self.p_bn(self.p_conv(h)))
        p = self.p_fc(p.flatten(1))
        v = F.relu(self.v_bn(self.v_conv(h)))
        v = F.relu(self.v_fc1(v.flatten(1)))
        v = torch.tanh(self.v_fc2(v)).squeeze(-1)
        return p, v


# =============================================================================
# PPO
# =============================================================================
class PPO:
    def __init__(self, lr=1e-3, epochs=2, batch=64, rollout=512,
                 clip=0.2, ent_start=0.02, ent_end=0.002):
        self.net = ChessNet()
        self.opt = optim.Adam(self.net.parameters(), lr=lr)
        self.epochs, self.batch, self.rollout = epochs, batch, rollout
        self.clip = clip
        self.ent_start, self.ent_end = ent_start, ent_end
        self.updates = 0

    def act(self, state, mask):
        with torch.no_grad():
            s = torch.from_numpy(state).unsqueeze(0)
            logits, _ = self.net(s)
            logits = logits.squeeze(0).masked_fill(
                ~torch.from_numpy(mask), -1e9)
            d = Categorical(logits=logits)
            a = d.sample()
            return int(a.item()), float(d.log_prob(a).item())

    def greedy(self, state, mask):
        with torch.no_grad():
            s = torch.from_numpy(state).unsqueeze(0)
            logits, _ = self.net(s)
            logits = logits.squeeze(0).masked_fill(
                ~torch.from_numpy(mask), -1e9)
            return int(logits.argmax().item())

    def update(self, batch):
        S = torch.from_numpy(np.stack([b['state'] for b in batch]))
        A = torch.tensor([b['action'] for b in batch], dtype=torch.long)
        LP = torch.tensor([b['logprob'] for b in batch], dtype=torch.float32)
        M = torch.from_numpy(np.stack([b['mask'] for b in batch]))
        VT = torch.tensor([b['vtarget'] for b in batch], dtype=torch.float32)
        with torch.no_grad():
            _, V = self.net(S)
            adv = VT - V.squeeze(-1)
            adv = (adv - adv.mean()) / (adv.std() + 1e-8)
        n = len(batch)
        frac = min(self.updates / 500.0, 1.0)
        ec = self.ent_start * (1 - frac) + self.ent_end * frac
        for _ in range(self.epochs):
            idx = np.random.permutation(n)
            for i in range(0, n, self.batch):
                b = idx[i:i + self.batch]
                logits, v = self.net(S[b])
                logits = logits.masked_fill(~M[b], -1e9)
                d = Categorical(logits=logits)
                nlp = d.log_prob(A[b])
                ent = d.entropy().mean()
                r = (nlp - LP[b]).exp()
                a_ = adv[b]
                s1 = r * a_
                s2 = torch.clamp(r, 1 - self.clip, 1 + self.clip) * a_
                loss = (-torch.min(s1, s2).mean()
                        + 0.5 * F.mse_loss(v, VT[b])
                        - ec * ent)
                self.opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.net.parameters(), 0.5)
                self.opt.step()
        self.updates += 1


# =============================================================================
# Self-play / eval
# =============================================================================
def self_play_game(agent):
    board = chess.Board()
    batch = []
    plies = 0
    while not board.is_game_over(claim_draw=True) and plies < MAX_PLIES:
        state = encode_board(board)
        mask = legal_mask(board)
        a, lp = agent.act(state, mask)
        mv = idx_to_move(a, board) or random.choice(list(board.legal_moves))
        batch.append({'state': state, 'action': a, 'logprob': lp,
                      'mask': mask, 'turn': board.turn})
        board.push(mv)
        plies += 1
    res = (board.result(claim_draw=True)
           if board.is_game_over(claim_draw=True) else "*")
    wr = 1.0 if res == "1-0" else (-1.0 if res == "0-1" else 0.0)
    for s in batch:
        s['vtarget'] = wr if s['turn'] == chess.WHITE else -wr
        del s['turn']
    return batch, res


def evaluate_vs_random(agent, n_games=EVAL_GAMES):
    w = d = l = 0
    for side in (chess.WHITE, chess.BLACK):
        for _ in range(n_games):
            board = chess.Board()
            plies = 0
            while not board.is_game_over(claim_draw=True) and plies < MAX_PLIES:
                if board.turn == side:
                    state = encode_board(board)
                    mask = legal_mask(board)
                    a = agent.greedy(state, mask)
                    mv = (idx_to_move(a, board)
                          or random.choice(list(board.legal_moves)))
                else:
                    mv = random.choice(list(board.legal_moves))
                board.push(mv)
                plies += 1
            res = (board.result(claim_draw=True)
                   if board.is_game_over(claim_draw=True) else "*")
            if side == chess.WHITE:
                if res == "1-0": w += 1
                elif res == "0-1": l += 1
                else: d += 1
            else:
                if res == "0-1": w += 1
                elif res == "1-0": l += 1
                else: d += 1
    return (w + 0.5 * d) / (2 * n_games), w, d, l


# =============================================================================
# Checkpoint
# =============================================================================
def save_ckpt(path, agent, episode, best_score, score_hist, total_steps):
    torch.save({
        'net': agent.net.state_dict(),
        'opt': agent.opt.state_dict(),
        'updates': agent.updates,
        'episode': episode,
        'best_score': best_score,
        'score_hist': list(score_hist),
        'total_steps': total_steps,
    }, path)


def load_ckpt(path, agent):
    if not os.path.exists(path):
        return None
    try:
        ck = torch.load(path, weights_only=False)
        agent.net.load_state_dict(ck['net'])
        try:
            agent.opt.load_state_dict(ck['opt'])
        except Exception:
            pass
        agent.updates = ck.get('updates', 0)
        return ck
    except Exception as e:
        print(f"[load failed] {e}")
        return None


# =============================================================================
# Trainer
# =============================================================================
def train():
    agent = PPO()

    buffer = []
    rolling = collections.deque(maxlen=WINDOW)
    score_hist = collections.deque(maxlen=200)
    episode = 0
    total_steps = 0
    best = 0.0
    start = time.time()

    # Resume
    if os.path.exists(CKPT):
        ck = load_ckpt(CKPT, agent)
        if ck is not None:
            episode = ck['episode']
            best = ck['best_score']
            total_steps = ck['total_steps']
            score_hist.extend(ck['score_hist'])
            print(f"[resumed] {CKPT}  episode={episode}  best={best:.3f}")

    print()
    print(f"{'episode':>9} {'steps':>11} {'updates':>8} "
          f"{'rolling':>9} {'best':>8} {'ep/s':>7} {'elapsed':>9}")
    print("-" * 68)

    last_log = 0.0
    last_log_ep = 0

    try:
        while True:
            # --- self-play one game ------------------------------------
            batch, _ = self_play_game(agent)
            buffer.extend(batch)
            episode += 1
            total_steps += len(batch)

            # --- PPO update --------------------------------------------
            if len(buffer) >= agent.rollout:
                agent.update(buffer)
                buffer.clear()

            # --- periodic eval -----------------------------------------
            if episode % EVAL_INTERVAL == 0:
                score, w, d, l = evaluate_vs_random(agent)
                rolling.append(score)
                score_hist.append(score)
                if score > best:
                    best = score

            # --- autosave ----------------------------------------------
            if episode % AUTOSAVE_EVERY == 0:
                save_ckpt(CKPT, agent, episode, best, score_hist, total_steps)

            # --- periodic log ------------------------------------------
            now = time.time()
            if now - last_log >= LOG_EVERY:
                ravg = float(np.mean(rolling)) if rolling else 0.0
                eps_per_sec = (episode - last_log_ep) / (now - last_log)
                elapsed = now - start
                em, es = divmod(int(elapsed), 60)
                eh, em = divmod(em, 60)
                print(f"{episode:>9} {total_steps:>11} {agent.updates:>8} "
                      f"{ravg:>9.3f} {best:>8.3f} {eps_per_sec:>7.2f} "
                      f"{eh:>3}:{em:02d}:{es:02d}")
                last_log = now
                last_log_ep = episode

    except KeyboardInterrupt:
        print("\nStopping...")
        save_ckpt(CKPT, agent, episode, best, score_hist, total_steps)
        print(f"[saved] {CKPT}  episode={episode}  best={best:.3f}")


if __name__ == "__main__":
    train()