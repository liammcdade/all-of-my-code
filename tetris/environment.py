"""
Tetris Environment for Reinforcement Learning - Meta-Action Architecture.
Instead of primitive actions, the agent chooses among all valid final placements.
Each placement = (rotation, column) + hard drop. Dramatically improves learning.
"""

import numpy as np
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Board dimensions
BOARD_WIDTH = 10
BOARD_HEIGHT = 20
CELL_SIZE = 30
SIDEBAR_WIDTH = 200

# Colors (only used for rendering)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (40, 40, 40)

PIECE_COLORS = {
    'I': (0, 240, 240),
    'O': (240, 240, 0),
    'T': (160, 0, 240),
    'S': (0, 240, 0),
    'Z': (240, 0, 0),
    'J': (0, 0, 240),
    'L': (240, 160, 0),
}

# Piece shapes: all 4 rotation states for each of the 7 tetrominoes
# Each cell is (row_offset, col_offset) from the piece origin
SHAPES = {
    'I': [
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 0), (1, 0), (2, 0), (3, 0)],
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 0), (1, 0), (2, 0), (3, 0)],
    ],
    'O': [
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    ],
    'T': [
        [(0, 0), (0, 1), (0, 2), (1, 1)],
        [(0, 0), (1, 0), (2, 0), (1, 1)],
        [(1, 0), (1, 1), (1, 2), (0, 1)],
        [(0, 0), (1, 0), (2, 0), (1, -1)],
    ],
    'S': [
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
    ],
    'Z': [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
    ],
    'J': [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (0, 1), (1, 0), (2, 0)],
        [(0, 0), (0, 1), (0, 2), (1, 2)],
        [(0, 0), (1, 0), (2, 0), (2, -1)],
    ],
    'L': [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (1, 0), (2, 0), (2, 1)],
        [(0, 0), (0, 1), (0, 2), (1, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
    ],
}

PIECE_TYPES = ['I', 'O', 'T', 'S', 'Z', 'J', 'L']

# One-hot encodings for pieces
PIECE_ONEHOT = {p: [1.0 if p == t else 0.0 for t in PIECE_TYPES] for p in PIECE_TYPES}

MAX_ROTATIONS = 4
NUM_PIECE_TYPES = len(PIECE_TYPES)

# Precompute all (rotation, col) combos for fast enumeration
ALL_RC = []
for _rot in range(MAX_ROTATIONS):
    for _col in range(BOARD_WIDTH):
        ALL_RC.append((_rot, _col))
MAX_PLACEMENTS = len(ALL_RC)  # 40


@dataclass
class Placement:
    """Describes one valid placement for the current piece."""
    rotation: int
    col: int
    row: int  # landing row
    reward: float
    nes_points: int  # raw NES score for this placement
    next_board: np.ndarray
    lines_cleared: int
    height: float
    holes: int
    bumpiness: float
    row_transitions: int
    col_transitions: int


def _get_cells(piece_type: str, rotation: int, row: int, col: int):
    """Absolute board coords for a piece at given (rotation, row, col)."""
    for dr, dc in SHAPES[piece_type][rotation]:
        yield row + dr, col + dc


def _check_collision(board, piece_type: str, rotation: int, row: int, col: int) -> bool:
    for r, c in _get_cells(piece_type, rotation, row, col):
        if c < 0 or c >= BOARD_WIDTH or r >= BOARD_HEIGHT:
            return True
        if r >= 0 and board[r][c] != 0:
            return True
    return False


def _lock_onto(board, piece_type: str, rotation: int, row: int, col: int):
    """Place piece onto a copy of the board. Returns new board + lines cleared."""
    new_board = board.copy()
    val = PIECE_TYPES.index(piece_type) + 1
    for r, c in _get_cells(piece_type, rotation, row, col):
        if 0 <= r < BOARD_HEIGHT and 0 <= c < BOARD_WIDTH:
            new_board[r][c] = val
    # Clear lines
    cleared = 0
    r = BOARD_HEIGHT - 1
    while r >= 0:
        if all(new_board[r][c] != 0 for c in range(BOARD_WIDTH)):
            new_board = np.delete(new_board, r, axis=0)
            new_board = np.vstack([np.zeros(BOARD_WIDTH, dtype=np.int8), new_board])
            cleared += 1
        else:
            r -= 1
    return new_board, cleared


def _board_features(board):
    """Compute board quality metrics including depth-weighted holes and wells."""
    heights = np.zeros(BOARD_WIDTH)
    for c in range(BOARD_WIDTH):
        for r in range(BOARD_HEIGHT):
            if board[r][c] != 0:
                heights[c] = BOARD_HEIGHT - r
                break

    # Basic holes count
    holes = 0
    # Depth-weighted holes: deeper holes are worse (weight = depth from surface)
    depth_holes = 0.0
    # Trapped empty cells: empty cells fully enclosed by blocks (left, right, top)
    trapped = 0
    for c in range(BOARD_WIDTH):
        block_found = False
        local_depth = 0
        for r in range(BOARD_HEIGHT):
            if board[r][c] != 0:
                block_found = True
            elif block_found:
                holes += 1
                local_depth += 1
                depth_holes += local_depth * local_depth  # quadratic penalty for depth

    # Wells: columns significantly lower than both neighbors
    wells_total = 0
    deepest_well = 0
    for c in range(BOARD_WIDTH):
        left_h = heights[c - 1] if c > 0 else heights[c]
        right_h = heights[c + 1] if c < BOARD_WIDTH - 1 else heights[c]
        wall_h = min(left_h, right_h)
        well_depth = wall_h - heights[c]
        if well_depth > 0:
            wells_total += well_depth
            deepest_well = max(deepest_well, well_depth)

    bumpiness = sum(abs(heights[c] - heights[c + 1]) for c in range(BOARD_WIDTH - 1))

    # Row transitions: fewer = smoother surface
    row_transitions = 0
    for r in range(BOARD_HEIGHT):
        for c in range(BOARD_WIDTH - 1):
            if (board[r][c] == 0) != (board[r][c + 1] == 0):
                row_transitions += 1

    # Column transitions
    col_transitions = 0
    for c in range(BOARD_WIDTH):
        for r in range(BOARD_HEIGHT - 1):
            if (board[r][c] == 0) != (board[r + 1][c] == 0):
                col_transitions += 1

    return (float(np.sum(heights)), int(np.max(heights)), holes, bumpiness,
            heights, row_transitions, col_transitions,
            depth_holes, wells_total, deepest_well)


def _compute_placement_reward(old_board, new_board, lines_cleared, nes_level):
    """Multi-objective reward: NES score + shaping signals.

    NES scoring (matches NES Tetris):
      1 line  = 40  * (level + 1)
      2 lines = 100 * (level + 1)
      3 lines = 300 * (level + 1)
      4 lines = 1200 * (level + 1)
    """
    old_agg, old_max, old_holes, old_bump, _, old_rt, _, old_dh, _, _ = _board_features(old_board)
    new_agg, new_max, new_holes, new_bump, _, new_rt, _, new_dh, _, new_deepest = _board_features(new_board)

    nes_scores = {0: 0, 1: 40, 2: 100, 3: 300, 4: 1200}
    nes_points = nes_scores.get(lines_cleared, 0) * (nes_level + 1)

    reward = 0.0

    # === POSITIVE SIGNALS ===

    # NES component (scaled)
    reward += nes_points * 0.02

    # Strong line-clear bonus
    reward += lines_cleared * 10.0

    # Bonus for clearing more lines at once
    tetris_bonus = {0: 0, 1: 2, 2: 10, 3: 30, 4: 100}
    reward += tetris_bonus.get(lines_cleared, 0)

    # Flat survival bonus — dominant early signal to keep the agent alive
    reward += 2.0

    # Bonus for reducing holes (negative delta = good)
    hole_delta = new_holes - old_holes
    if hole_delta < 0:
        reward += abs(hole_delta) * 2.0

    # Clean surface bonus
    if new_rt < old_rt:
        reward += (old_rt - new_rt) * 0.1

    # === NEGATIVE SIGNALS ===

    # Hole creation penalty
    if hole_delta > 0:
        reward -= hole_delta * 2.0

    # Height growth penalty
    height_delta = new_agg - old_agg
    reward -= height_delta * 0.3

    # Bumpiness growth penalty
    bump_delta = new_bump - old_bump
    reward -= bump_delta * 0.8

    # Absolute height danger (nonlinear)
    if new_max > 17:
        reward -= 3.0
    elif new_max > 15:
        reward -= 1.0

    # Clip reward to keep gradients stable
    reward = np.clip(reward, -10.0, 50.0)

    return reward, nes_points


class TetrisEnv:
    """Tetris environment with meta-action (placement) interface.

    Supports curriculum learning via:
    - starting_level: begin at a higher level (faster gravity)
    - extra_bag_pieces: inject specific pieces into the bag more often
      (e.g. ['Z', 'S'] to practice with harder pieces)
    """

    def __init__(self, render: bool = False, starting_level: int = 1,
                 extra_bag_pieces: list = None):
        self.render_mode = render
        self.starting_level = starting_level
        self.extra_bag_pieces = extra_bag_pieces or []
        self._pygame = None
        if self.render_mode:
            import pygame
            self._pygame = pygame
            pygame.init()
            self.screen = pygame.display.set_mode(
                (BOARD_WIDTH * CELL_SIZE + SIDEBAR_WIDTH, BOARD_HEIGHT * CELL_SIZE)
            )
            pygame.display.set_caption("Tetris RL")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont("consolas", 18)
            self.font_large = pygame.font.SysFont("consolas", 24, bold=True)
        self.reset()

    def set_curriculum(self, starting_level: int = 1, extra_bag_pieces: list = None):
        """Update curriculum parameters for future resets."""
        self.starting_level = starting_level
        self.extra_bag_pieces = extra_bag_pieces or []

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def reset(self) -> np.ndarray:
        """Reset environment and return initial state features."""
        self.board = np.zeros((BOARD_HEIGHT, BOARD_WIDTH), dtype=np.int8)
        self.score = 0
        self.nes_score = 0  # raw NES score (unaffected by RL shaping)
        self.lines_cleared = 0
        self.level = self.starting_level
        self.game_over = False
        self.piece_bag = []
        self.hold_piece = None
        self._fill_bag()
        self.current_type = self._bag_pop()
        self.next_type = self._bag_pop()
        self._placements = self._enumerate_placements()
        return self._build_state()

    def get_valid_placements(self) -> List[Placement]:
        """Return valid placements for the current piece."""
        return self._placements

    def apply_placement(self, idx: int) -> Tuple[np.ndarray, float, bool, dict]:
        """Apply the chosen placement. Returns (state, reward, done, info)."""
        p = self._placements[idx]

        self.board = p.next_board
        self.score += p.reward
        self.nes_score += p.nes_points
        self.lines_cleared += p.lines_cleared
        self.level = self.lines_cleared // 10 + 1

        # Small step cost to discourage suiciding
        step_reward = p.reward - 0.05

        # Spawn next piece
        self.current_type = self.next_type
        self.next_type = self._bag_pop()

        if _check_collision(self.board, self.current_type, 0,
                            0, BOARD_WIDTH // 2):
            self.game_over = True
            self._placements = []
            return self._build_state(), step_reward - 5.0, True, {
                'score': self.score, 'nes_score': self.nes_score,
                'lines': self.lines_cleared, 'level': self.level,
            }

        self._placements = self._enumerate_placements()

        if not self._placements:
            self.game_over = True
            return self._build_state(), step_reward - 5.0, True, {
                'score': self.score, 'nes_score': self.nes_score,
                'lines': self.lines_cleared, 'level': self.level,
            }

        info = {'score': self.score, 'nes_score': self.nes_score,
                'lines': self.lines_cleared, 'level': self.level}
        return self._build_state(), step_reward, False, info

    # ------------------------------------------------------------------
    # Placement enumeration
    # ------------------------------------------------------------------

    def _enumerate_placements(self) -> List[Placement]:
        """Simulate every valid (rotation, col) and return Placement list."""
        placements = []
        for rot in range(MAX_ROTATIONS):
            for col in range(BOARD_WIDTH):
                p = self._simulate_placement(self.current_type, rot, col)
                if p is not None:
                    placements.append(p)
        return placements

    def _simulate_placement(self, piece_type: str, rotation: int,
                            col: int) -> Optional[Placement]:
        """Simulate dropping piece at (rotation, col). Returns None if invalid."""
        # Find landing row
        row = 0
        if _check_collision(self.board, piece_type, rotation, row, col):
            return None
        while not _check_collision(self.board, piece_type, rotation, row + 1, col):
            row += 1

        new_board, cleared = _lock_onto(self.board, piece_type, rotation, row, col)
        nes_level = max(0, self.level - 1)  # NES level is 0-based
        reward, nes_pts = _compute_placement_reward(self.board, new_board, cleared, nes_level)
        agg, mx, holes, bump, _, row_trans, col_trans, _, _, _ = _board_features(new_board)

        return Placement(
            rotation=rotation, col=col, row=row, reward=reward,
            nes_points=nes_pts, next_board=new_board, lines_cleared=cleared,
            height=mx, holes=holes, bumpiness=bump,
            row_transitions=row_trans, col_transitions=col_trans,
        )

    # ------------------------------------------------------------------
    # State representation
    # ------------------------------------------------------------------

    def _build_state(self) -> np.ndarray:
        """Build rich state vector for the RL agent.
        Includes: board, column heights, aggregate height, max height, bumpiness,
        holes, wells, danger, row features, transitions, level, current + next piece.
        """
        board_flat = self.board.flatten().astype(np.float32) / NUM_PIECE_TYPES

        heights = np.zeros(BOARD_WIDTH)
        for c in range(BOARD_WIDTH):
            for r in range(BOARD_HEIGHT):
                if self.board[r][c] != 0:
                    heights[c] = BOARD_HEIGHT - r
                    break

        agg = np.sum(heights)
        mx = np.max(heights)

        holes = 0
        for c in range(BOARD_WIDTH):
            block_found = False
            for r in range(BOARD_HEIGHT):
                if self.board[r][c] != 0:
                    block_found = True
                elif block_found:
                    holes += 1

        bump = sum(abs(heights[c] - heights[c + 1]) for c in range(BOARD_WIDTH - 1))

        wells = 0
        for c in range(BOARD_WIDTH):
            left_h = heights[c - 1] if c > 0 else BOARD_HEIGHT
            right_h = heights[c + 1] if c < BOARD_WIDTH - 1 else BOARD_HEIGHT
            w = min(left_h, right_h) - heights[c]
            if w > 0:
                wells += w

        danger = np.sum(heights > 14)

        row_features = []
        for r in range(BOARD_HEIGHT):
            row_features.append(np.sum(self.board[r] != 0) / BOARD_WIDTH)

        # Row and column transitions
        row_trans = 0
        for r in range(BOARD_HEIGHT):
            for c in range(BOARD_WIDTH - 1):
                if (self.board[r][c] == 0) != (self.board[r][c + 1] == 0):
                    row_trans += 1
        col_trans = 0
        for c in range(BOARD_WIDTH):
            for r in range(BOARD_HEIGHT - 1):
                if (self.board[r][c] == 0) != (self.board[r + 1][c] == 0):
                    col_trans += 1

        # Piece one-hot encodings
        cur_oh = np.array(PIECE_ONEHOT[self.current_type], dtype=np.float32)
        nxt_oh = np.array(PIECE_ONEHOT[self.next_type], dtype=np.float32)

        state = np.concatenate([
            board_flat,
            heights / BOARD_HEIGHT,
            [agg / (BOARD_WIDTH * BOARD_HEIGHT)],
            [mx / BOARD_HEIGHT],
            [bump / (BOARD_WIDTH * BOARD_HEIGHT)],
            [holes / (BOARD_WIDTH * BOARD_HEIGHT)],
            [wells / (BOARD_WIDTH * BOARD_HEIGHT)],
            [danger / BOARD_WIDTH],
            np.array(row_features, dtype=np.float32),
            [row_trans / (BOARD_HEIGHT * (BOARD_WIDTH - 1))],
            [col_trans / (BOARD_WIDTH * (BOARD_HEIGHT - 1))],
            [self.level / 20.0],
            cur_oh,
            nxt_oh,
        ])
        return state

    def get_state_size(self) -> int:
        return self._build_state().shape[0]

    # ------------------------------------------------------------------
    # Bag randomizer
    # ------------------------------------------------------------------

    def _fill_bag(self):
        bag = list(PIECE_TYPES)
        random.shuffle(bag)
        self.piece_bag.extend(bag)
        # Curriculum: inject extra hard pieces (e.g. Z, S) to force practice
        if self.extra_bag_pieces:
            for p in self.extra_bag_pieces:
                if p in PIECE_TYPES:
                    self.piece_bag.insert(random.randint(0, len(self.piece_bag)), p)

    def _bag_pop(self) -> str:
        if len(self.piece_bag) < 7:
            self._fill_bag()
        return self.piece_bag.pop(0)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_frame(self, placement_idx: Optional[int] = None,
                     episode: int = 0, epsilon: float = 0,
                     best_score: float = 0, fps: int = 30):
        if not self.render_mode:
            return
        pg = self._pygame
        self.screen.fill(BLACK)
        self._draw_board()
        self._draw_sidebar(placement_idx, episode, epsilon, best_score)
        pg.display.flip()
        self.clock.tick(fps)
        for ev in pg.event.get():
            if ev.type == pg.QUIT:
                pg.quit()
                raise SystemExit

    def _draw_board(self):
        pg = self._pygame
        for r in range(BOARD_HEIGHT):
            for c in range(BOARD_WIDTH):
                x, y = c * CELL_SIZE, r * CELL_SIZE
                pg.draw.rect(self.screen, GRAY, (x, y, CELL_SIZE, CELL_SIZE), 1)
                if self.board[r][c] != 0:
                    color = PIECE_COLORS[PIECE_TYPES[self.board[r][c] - 1]]
                    pg.draw.rect(self.screen, color,
                                 (x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2))
                    hi = tuple(min(255, v + 50) for v in color)
                    pg.draw.rect(self.screen, hi, (x + 2, y + 2, CELL_SIZE - 8, 4))

    def _draw_sidebar(self, placement_idx, episode, epsilon, best_score):
        x0 = BOARD_WIDTH * CELL_SIZE + 10

        def txt(s, y, color=WHITE, font=None):
            self.screen.blit((font or self.font).render(s, True, color), (x0, y))

        txt("TETRIS RL", 10, PIECE_COLORS['T'], self.font_large)
        txt(f"NES:   {self.nes_score}", 50, (255, 255, 0))
        txt(f"RL:    {self.score:.0f}", 75)
        txt(f"Lines: {self.lines_cleared}", 100)
        txt(f"Level: {self.level}", 125)
        txt(f"Episode: {episode}", 160)
        txt(f"Epsilon: {epsilon:.4f}", 185)
        txt(f"Best: {best_score:.0f}", 210)

        if placement_idx is not None:
            txt(f"Placement: #{placement_idx}", 245, (255, 255, 0))
            if placement_idx < len(self._placements):
                p = self._placements[placement_idx]
                txt(f"  rot={p.rotation} col={p.col}", 270, (200, 200, 100))
                txt(f"  lines={p.lines_cleared}", 290, (200, 200, 100))

        txt("NEXT:", 330, (200, 200, 200))
        self._draw_preview(self.next_type, x0, 355)

        txt("HOLD:", 440, (200, 200, 200))
        if self.hold_piece:
            self._draw_preview(self.hold_piece, x0, 465)

        if self.game_over:
            txt("GAME OVER", 540, (255, 0, 0), self.font_large)

    def _draw_preview(self, piece_type, x0, y0):
        color = PIECE_COLORS[piece_type]
        for r, c in SHAPES[piece_type][0]:
            self._pygame.draw.rect(self.screen, color, (x0 + c * 20, y0 + r * 20, 18, 18))

    def close(self):
        if self.render_mode:
            self._pygame.quit()
