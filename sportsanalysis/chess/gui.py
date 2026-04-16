"""
Advanced Chess Reinforcement Learning Agent with GUI
Target: Reach 2000 ELO rating through self-play learning
"""

import numpy as np
import pandas as pd
import sys

# Import chess library avoiding name conflict with this file
current_dir = sys.path.pop(0)
import chess as chess_lib
sys.path.insert(0, current_dir)
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import json
import os
import random
import time
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

import pygame

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChessNet(nn.Module):
    def __init__(self, input_planes=20, num_filters=256, num_res_blocks=19):
        super(ChessNet, self).__init__()
        self.input_planes = input_planes
        self.num_filters = num_filters

        # Initial convolution
        self.conv1 = nn.Conv2d(input_planes, num_filters, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(num_filters)

        # Residual blocks
        self.res_blocks = nn.ModuleList([
            ResidualBlock(num_filters) for _ in range(num_res_blocks)
        ])

        # Policy head
        self.policy_conv = nn.Conv2d(num_filters, 2, kernel_size=1)
        self.policy_bn = nn.BatchNorm2d(2)
        self.policy_fc = nn.Linear(2 * 8 * 8, 4096)  # 64*64 for from*64 + to

        # Value head
        self.value_conv = nn.Conv2d(num_filters, 1, kernel_size=1)
        self.value_bn = nn.BatchNorm2d(1)
        self.value_fc1 = nn.Linear(1 * 8 * 8, 256)
        self.value_fc2 = nn.Linear(256, 1)

    def forward(self, x):
        # Initial conv
        x = F.relu(self.bn1(self.conv1(x)))

        # Residual blocks
        for block in self.res_blocks:
            x = block(x)

        # Policy head
        policy = F.relu(self.policy_bn(self.policy_conv(x)))
        policy = policy.view(policy.size(0), -1)
        policy = self.policy_fc(policy)
        policy = F.log_softmax(policy, dim=1)

        # Value head
        value = F.relu(self.value_bn(self.value_conv(x)))
        value = value.view(value.size(0), -1)
        value = F.relu(self.value_fc1(value))
        value = torch.tanh(self.value_fc2(value))

        return policy, value


class ResidualBlock(nn.Module):
    def __init__(self, num_filters):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(num_filters, num_filters, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(num_filters)
        self.conv2 = nn.Conv2d(num_filters, num_filters, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(num_filters)

    def forward(self, x):
        residual = x
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.bn2(self.conv2(x))
        x += residual
        x = F.relu(x)
        return x


class ChessRLAgent:
    def __init__(self, model_path="chess_model.pkl", training_data_path="training_games.json"):
        self.model_path = model_path
        self.training_data_path = training_data_path

        # Training data storage
        self.training_games = []
        self.load_training_data()

        # Neural network model
        self.model = ChessNet()
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001, weight_decay=1e-4)
        self.load_model()

        # MCTS parameters
        self.mcts_simulations = 1000
        self.c_puct = 1.4

        # Training parameters
        self.elo_rating = 1200  # Starting ELO
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0

        # Experience replay
        self.memory = deque(maxlen=10000)
        self.batch_size = 32

        # Feature extraction cache
        self.position_cache = {}

        logger.info("Chess RL Agent initialized")

    def load_training_data(self):
        """Load existing training data"""
        try:
            if os.path.exists(self.training_data_path):
                with open(self.training_data_path, 'r') as f:
                    self.training_games = json.load(f)
                logger.info(f"Loaded {len(self.training_games)} training games")
        except Exception as e:
            logger.warning(f"Could not load training data: {e}")
            self.training_games = []

    def save_training_data(self):
        """Save training data to disk"""
        try:
            with open(self.training_data_path, 'w') as f:
                json.dump(self.training_games, f, indent=2)
            logger.info(f"Saved {len(self.training_games)} training games")
        except Exception as e:
            logger.error(f"Could not save training data: {e}")

    def load_model(self):
        """Load or initialize the neural network model"""
        try:
            if os.path.exists(self.model_path):
                checkpoint = torch.load(self.model_path)
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
                logger.info("Loaded existing neural network model")
            else:
                logger.info("Initialized new neural network model")
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
            self.model = ChessNet()
            self.optimizer = optim.Adam(self.model.parameters(), lr=0.001, weight_decay=1e-4)

    def save_model(self):
        """Save the neural network model to disk"""
        try:
            checkpoint = {
                'model_state_dict': self.model.state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict()
            }
            torch.save(checkpoint, self.model_path)
            logger.info("Neural network model saved")
        except Exception as e:
            logger.error(f"Could not save model: {e}")

    def board_to_tensor(self, board):
        """
        Convert chess board to tensor representation for neural network
        Returns tensor of shape (planes, 8, 8)
        """
        planes = []

        # Piece planes (12 total: 6 for white, 6 for black)
        piece_types = ['P', 'N', 'B', 'R', 'Q', 'K']
        for color in [chess_lib.WHITE, chess_lib.BLACK]:
            for piece_type in piece_types:
                plane = np.zeros((8, 8), dtype=np.float32)
                for square in chess_lib.SQUARES:
                    piece = board.piece_at(square)
                    if piece and piece.symbol() == (piece_type if color == chess_lib.WHITE else piece_type.lower()):
                        rank, file = divmod(square, 8)
                        plane[rank, file] = 1.0
                planes.append(plane)

        # Additional planes
        # Turn (1 if white to move)
        turn_plane = np.full((8, 8), 1.0 if board.turn == chess_lib.WHITE else 0.0, dtype=np.float32)
        planes.append(turn_plane)

        # Castling rights (4 planes: KQkq)
        castling_rights = [
            board.has_kingside_castling_rights(chess_lib.WHITE),
            board.has_queenside_castling_rights(chess_lib.WHITE),
            board.has_kingside_castling_rights(chess_lib.BLACK),
            board.has_queenside_castling_rights(chess_lib.BLACK)
        ]
        for right in castling_rights:
            plane = np.full((8, 8), 1.0 if right else 0.0, dtype=np.float32)
            planes.append(plane)

        # En passant square
        en_passant_plane = np.zeros((8, 8), dtype=np.float32)
        if board.ep_square is not None:
            rank, file = divmod(board.ep_square, 8)
            en_passant_plane[rank, file] = 1.0
        planes.append(en_passant_plane)

        # Halfmove clock (normalized)
        halfmove_plane = np.full((8, 8), board.halfmove_clock / 100.0, dtype=np.float32)
        planes.append(halfmove_plane)

        # Fullmove number (normalized)
        fullmove_plane = np.full((8, 8), board.fullmove_number / 100.0, dtype=np.float32)
        planes.append(fullmove_plane)

        # Stack planes into tensor (planes, 8, 8)
        tensor = torch.from_numpy(np.stack(planes))
        return tensor

    def extract_features(self, board):
        """
        Extract comprehensive features from chess position (legacy for RandomForest)
        """
        # Cache features to avoid recomputation
        fen = board.fen()
        if fen in self.position_cache:
            return self.position_cache[fen]

        features = []

        # Material balance
        piece_values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0}
        white_material = 0
        black_material = 0

        for square in chess_lib.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = piece_values[piece.symbol().lower()]
                if piece.color == chess_lib.WHITE:
                    white_material += value
                else:
                    black_material += value

        features.extend([white_material, black_material, white_material - black_material])

        # Piece counts
        white_pieces = [0] * 6  # P, N, B, R, Q, K
        black_pieces = [0] * 6

        for square in chess_lib.SQUARES:
            piece = board.piece_at(square)
            if piece:
                idx = 'pnbrqk'.index(piece.symbol().lower())
                if piece.color == chess_lib.WHITE:
                    white_pieces[idx] += 1
                else:
                    black_pieces[idx] += 1

        features.extend(white_pieces)
        features.extend(black_pieces)

        # Positional features
        features.append(1 if board.is_check() else 0)
        features.append(len(list(board.legal_moves)))
        features.append(board.fullmove_number)
        features.append(1 if board.turn == chess_lib.WHITE else 0)

        # King safety (simplified)
        white_king_square = board.king(chess_lib.WHITE)
        black_king_square = board.king(chess_lib.BLACK)

        white_king_attackers = len(board.attackers(chess_lib.BLACK, white_king_square))
        black_king_attackers = len(board.attackers(chess_lib.WHITE, black_king_square))

        features.extend([white_king_attackers, black_king_attackers])

        # Pawn structure (simplified)
        white_pawn_advances = sum(chess_lib.square_rank(sq) for sq in chess_lib.SQUARES
                                if board.piece_at(sq) and board.piece_at(sq).symbol() == 'P')
        black_pawn_advances = sum(7 - chess_lib.square_rank(sq) for sq in chess_lib.SQUARES
                                if board.piece_at(sq) and board.piece_at(sq).symbol() == 'p')

        features.extend([white_pawn_advances, black_pawn_advances])

        # Center control
        center_squares = [chess_lib.D4, chess_lib.D5, chess_lib.E4, chess_lib.E5]
        white_center_control = sum(1 for sq in center_squares
                                 if any(board.attackers(chess_lib.WHITE, sq)))
        black_center_control = sum(1 for sq in center_squares
                                 if any(board.attackers(chess_lib.BLACK, sq)))

        features.extend([white_center_control, black_center_control])

        self.position_cache[fen] = features
        return features

    def evaluate_position(self, board):
        """
        Evaluate chess position using the neural network
        """
        self.model.eval()
        with torch.no_grad():
            tensor = self.board_to_tensor(board).unsqueeze(0)  # Add batch dim
            _, value = self.model(tensor)
            return value.item()

    def move_to_index(self, move):
        """Convert move to index for policy vector"""
        return move.from_square * 64 + move.to_square

    def get_best_move_mcts(self, board, time_limit=5.0, return_policy=False):
        """
        Use Monte Carlo Tree Search to find best move
        If return_policy, also return the policy distribution
        """
        if not board.legal_moves:
            return None

        legal_moves = list(board.legal_moves)
        if len(legal_moves) == 1:
            if return_policy:
                policy = np.zeros(4096)
                policy[self.move_to_index(legal_moves[0])] = 1.0
                return legal_moves[0], policy
            return legal_moves[0]

        start_time = time.time()

        # Get policy priors from NN
        self.model.eval()
        with torch.no_grad():
            tensor = self.board_to_tensor(board).unsqueeze(0)
            policy_pred, _ = self.model(tensor)
            policy = torch.exp(policy_pred).squeeze().numpy()

        # Initialize MCTS root
        root = MCTSNode(board)

        while time.time() - start_time < time_limit:
            # Selection
            node = root
            while node.children and not node.board.is_game_over():
                node = max(node.children.values(),
                          key=lambda n: n.ucb1(total_visits=root.visits))

            # Expansion
            if not node.board.is_game_over() and node.visits > 0:
                untried_moves = [move for move in node.board.legal_moves
                               if move not in node.children]
                if untried_moves:
                    move = random.choice(untried_moves)
                    new_board = node.board.copy()
                    new_board.push(move)
                    prior = policy[self.move_to_index(move)] if node.parent is None else 0.0
                    node.children[move] = MCTSNode(new_board, parent=node, move=move, prior=prior)

            # Simulation (using neural network for evaluation)
            sim_board = node.board.copy()
            depth = 0
            while not sim_board.is_game_over() and depth < 50:
                moves = list(sim_board.legal_moves)
                if not moves:
                    break
                # Use random move for simulation (can be improved)
                move = random.choice(moves)
                sim_board.push(move)
                depth += 1

            # Backpropagation
            result = self.get_game_result(sim_board)
            node.backpropagate(result)

        # Return best move
        if root.children:
            best_move = max(root.children.items(),
                          key=lambda x: x[1].visits)[0]
            if return_policy:
                policy = np.zeros(4096)
                total_visits = sum(child.visits for child in root.children.values())
                for move, child in root.children.items():
                    policy[self.move_to_index(move)] = child.visits / total_visits if total_visits > 0 else 1.0 / len(root.children)
                return best_move, policy
            return best_move

        # Fallback
        move = random.choice(legal_moves)
        if return_policy:
            policy = np.zeros(4096)
            policy[self.move_to_index(move)] = 1.0
            return move, policy
        return move

    def get_game_result(self, board):
        """
        Get game result from board state
        """
        if board.is_checkmate():
            return 1 if board.turn == chess_lib.BLACK else -1
        elif board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves():
            return 0
        else:
            # Use model evaluation for ongoing games
            return self.evaluate_position(board)

    def play_game(self, opponent_agent=None, max_moves=200):
        """
        Play a game against opponent or self
        """
        board = chess_lib.Board()
        game_history = []
        move_count = 0

        while not board.is_game_over() and move_count < max_moves:
            # Store position before move
            tensor = self.board_to_tensor(board)
            policy = None

            if opponent_agent and board.turn == chess_lib.BLACK:
                # Play against opponent
                move = opponent_agent.get_best_move_mcts(board, time_limit=2.0)
            else:
                # Self-play
                move, policy = self.get_best_move_mcts(board, time_limit=2.0, return_policy=True)

            game_history.append({
                'fen': board.fen(),
                'move': move.uci(),
                'tensor': tensor,
                'policy': policy,
                'turn': board.turn
            })

            board.push(move)
            print(f"Move {move_count}: {move.uci()}")
            move_count += 1

        # Determine result
        result = self.get_game_result(board)
        if result > 0.5:
            winner = 'white'
        elif result < -0.5:
            winner = 'black'
        else:
            winner = 'draw'

        game_data = {
            'moves': game_history,
            'result': result,
            'winner': winner,
            'final_fen': board.fen(),
            'move_count': move_count
        }

        return game_data

    def train_on_game(self, game_data):
        """
        Train the neural network on a completed game
        """
        training_samples = []

        # Calculate target values
        for i, move_data in enumerate(game_data['moves']):
            if 'policy' in move_data and move_data['policy'] is not None:
                tensor = move_data['tensor']
                policy = torch.from_numpy(move_data['policy']).float()

                # Target value is the final result with discount
                target_value = game_data['result']
                discount = 0.99 ** (len(game_data['moves']) - i - 1)
                target_value *= discount

                training_samples.append((tensor, policy, target_value))

        # Add to memory
        self.memory.extend(training_samples)

        # Train model if we have enough samples
        if len(self.memory) >= self.batch_size:
            self._train_model()

    def _train_model(self):
        """Train the neural network model"""
        if len(self.memory) < self.batch_size:
            return

        # Sample batch
        batch = random.sample(list(self.memory), min(self.batch_size, len(self.memory)))
        tensors = torch.stack([sample[0] for sample in batch])
        policies = torch.stack([sample[1] for sample in batch])
        values = torch.tensor([sample[2] for sample in batch], dtype=torch.float32)

        self.model.train()
        self.optimizer.zero_grad()

        # Forward pass
        policy_pred, value_pred = self.model(tensors)

        # Compute losses
        value_loss = F.mse_loss(value_pred.squeeze(), values)
        policy_loss = F.kl_div(policy_pred, policies, reduction='batchmean')

        # Total loss
        loss = value_loss + policy_loss

        # Backward pass
        loss.backward()
        self.optimizer.step()

        logger.info(f"Trained NN on {len(batch)} samples, loss: {loss.item():.4f}")

    def train_self_play(self, num_games=100, save_interval=10):
        """
        Train through self-play
        """
        logger.info(f"Starting self-play training for {num_games} games")

        for game_num in range(num_games):
            logger.info(f"Playing game {game_num + 1}/{num_games}")

            # Play game
            game_data = self.play_game()
            self.training_games.append(game_data)

            # Train on game
            self.train_on_game(game_data)

            # Update stats
            self.games_played += 1
            if game_data['winner'] == 'white':
                self.wins += 1
            elif game_data['winner'] == 'black':
                self.losses += 1
            else:
                self.draws += 1

            # Update ELO (simplified)
            if game_data['winner'] == 'white':
                self.elo_rating += 10
            elif game_data['winner'] == 'black':
                self.elo_rating -= 10

            # Save progress periodically
            if (game_num + 1) % save_interval == 0:
                self.save_model()
                self.save_training_data()
                self.generate_report()

        logger.info("Self-play training completed")

    def generate_report(self):
        """
        Generate comprehensive JSON report of training progress
        """
        report = {
            'timestamp': time.time(),
            'elo_rating': self.elo_rating,
            'games_played': self.games_played,
            'wins': self.wins,
            'losses': self.losses,
            'draws': self.draws,
            'win_rate': self.wins / max(1, self.games_played),
            'training_games_count': len(self.training_games),
            'memory_size': len(self.memory),
            'model_trained': self.model is not None,
            'cache_size': len(self.position_cache),
            'performance_metrics': self._calculate_performance_metrics()
        }

        # Save report
        report_path = f"training_report_{int(time.time())}.json"
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to {report_path}")
        except Exception as e:
            logger.error(f"Could not save report: {e}")

        return report

    def _calculate_performance_metrics(self):
        """
        Calculate various performance metrics
        """
        if not self.training_games:
            return {}

        metrics = {
            'avg_game_length': np.mean([g['move_count'] for g in self.training_games]),
            'avg_final_score': np.mean([g['result'] for g in self.training_games]),
            'win_rate_white': sum(1 for g in self.training_games if g['winner'] == 'white') / len(self.training_games),
            'win_rate_black': sum(1 for g in self.training_games if g['winner'] == 'black') / len(self.training_games),
            'draw_rate': sum(1 for g in self.training_games if g['winner'] == 'draw') / len(self.training_games)
        }

        return metrics

    def evaluate_against_random(self, num_games=10):
        """
        Evaluate agent against a random player
        """
        results = []
        for i in range(num_games):
            board = chess_lib.Board()
            game_moves = 0

            while not board.is_game_over() and game_moves < 200:
                if board.turn == chess_lib.WHITE:
                    # Agent's turn
                    move = self.get_best_move_mcts(board, time_limit=1.0)
                else:
                    # Random player's turn
                    legal_moves = list(board.legal_moves)
                    move = random.choice(legal_moves) if legal_moves else None

                if move:
                    board.push(move)
                    game_moves += 1
                else:
                    break

            result = self.get_game_result(board)
            results.append(result)
            logger.info(f"Game {i+1} vs Random: {result}")

        return {
            'random_games': num_games,
            'results': results,
            'avg_score': np.mean(results),
            'win_rate': sum(1 for r in results if r > 0.5) / len(results)
        }


class MCTSNode:
    def __init__(self, board, parent=None, move=None, prior=0.0):
        self.board = board.copy()
        self.parent = parent
        self.move = move
        self.children = {}
        self.visits = 0
        self.value = 0.0
        self.prior = prior

    def ucb1(self, total_visits, c_puct=1.4):
        if self.visits == 0:
            return float('inf') if self.prior == 0 else c_puct * self.prior * np.sqrt(total_visits)
        exploitation = self.value / self.visits
        exploration = c_puct * self.prior * np.sqrt(total_visits) / (1 + self.visits)
        return exploitation + exploration

    def backpropagate(self, result):
        self.visits += 1
        self.value += result
        if self.parent:
            self.parent.backpropagate(result)


# Constants
WIDTH, HEIGHT = 800, 800
SQUARE_SIZE = WIDTH // 8
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_BROWN = (240, 217, 181)
DARK_BROWN = (181, 136, 99)
HIGHLIGHT = (255, 255, 0, 100)  # Semi-transparent yellow

# Piece symbols
PIECE_SYMBOLS = {
    'P': '♟', 'R': '♜', 'N': '♞', 'B': '♝', 'Q': '♛', 'K': '♚',
    'p': '♙', 'r': '♖', 'n': '♘', 'b': '♗', 'q': '♕', 'k': '♔'
}

class ChessGUI:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chess RL Agent GUI")
        self.font = pygame.font.SysFont('segoeuisymbol', 60)  # For Unicode chess symbols
        self.board = chess_lib.Board()
        self.agent = ChessRLAgent()
        self.selected_square = None
        self.legal_moves = []
        self.human_color = chess_lib.WHITE
        self.game_over = False
        self.status_text = "White to move"

    def draw_board(self):
        for row in range(8):
            for col in range(8):
                color = LIGHT_BROWN if (row + col) % 2 == 0 else DARK_BROWN
                pygame.draw.rect(self.screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

                # Highlight selected square
                if self.selected_square and self.selected_square == chess_lib.square(col, 7 - row):
                    pygame.draw.rect(self.screen, HIGHLIGHT, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

                # Highlight legal moves
                square = chess_lib.square(col, 7 - row)
                if square in self.legal_moves:
                    center = (col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2)
                    pygame.draw.circle(self.screen, HIGHLIGHT, center, SQUARE_SIZE // 6)

    def draw_pieces(self):
        for square in chess_lib.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                col = chess_lib.square_file(square)
                row = 7 - chess_lib.square_rank(square)
                symbol = PIECE_SYMBOLS[piece.symbol()]
                text = self.font.render(symbol, True, WHITE if piece.color == chess_lib.WHITE else BLACK)
                text_rect = text.get_rect(center=(col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2))
                self.screen.blit(text, text_rect)

    def draw_status(self):
        font = pygame.font.SysFont(None, 36)
        text = font.render(self.status_text, True, BLACK)
        self.screen.blit(text, (10, HEIGHT - 40))

    def get_square_from_mouse(self, pos):
        x, y = pos
        col = x // SQUARE_SIZE
        row = 7 - (y // SQUARE_SIZE)
        if 0 <= col < 8 and 0 <= row < 8:
            return chess_lib.square(col, row)
        return None

    def handle_click(self, pos):
        if self.game_over:
            return

        square = self.get_square_from_mouse(pos)
        if square is None:
            return

        if self.selected_square is None:
            # Select piece
            piece = self.board.piece_at(square)
            if piece and piece.color == self.board.turn:
                self.selected_square = square
                self.legal_moves = [move.to_square for move in self.board.legal_moves if move.from_square == square]
        else:
            # Try to move
            move = chess_lib.Move(self.selected_square, square)
            if move in self.board.legal_moves:
                self.board.push(move)
                self.check_game_end()
                if not self.game_over and self.board.turn != self.human_color:
                    self.make_ai_move()
            self.selected_square = None
            self.legal_moves = []

    def make_ai_move(self):
        if self.game_over:
            return
        move = self.agent.get_best_move_mcts(self.board, time_limit=2.0)
        if move:
            self.board.push(move)
            self.check_game_end()

    def check_game_end(self):
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess_lib.WHITE else "White"
            self.status_text = f"Checkmate! {winner} wins"
            self.game_over = True
        elif self.board.is_stalemate():
            self.status_text = "Stalemate! Draw"
            self.game_over = True
        elif self.board.is_insufficient_material():
            self.status_text = "Draw - Insufficient material"
            self.game_over = True
        else:
            turn = "White" if self.board.turn == chess_lib.WHITE else "Black"
            self.status_text = f"{turn} to move"
            if self.board.is_check():
                self.status_text += " - Check!"

    def new_game(self):
        self.board = chess_lib.Board()
        self.selected_square = None
        self.legal_moves = []
        self.game_over = False
        self.status_text = "White to move"

    def run(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # R key for new game
                        self.new_game()

            self.screen.fill(WHITE)
            self.draw_board()
            self.draw_pieces()
            self.draw_status()
            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    gui = ChessGUI()
    gui.run()