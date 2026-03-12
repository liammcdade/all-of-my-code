"""
Advanced Chess Reinforcement Learning Agent
Target: Reach 2000 ELO rating through self-play learning
"""

import numpy as np
import chess as chess_lib
import pandas as pd
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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChessRLAgent:
    def __init__(self, model_path="chess_model.pkl", training_data_path="training_games.json"):
        self.model_path = model_path
        self.training_data_path = training_data_path

        # Training data storage
        self.training_games = []
        self.load_training_data()

        # Position evaluation model
        self.model = None
        self.scaler = StandardScaler()
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
        """Load or initialize the position evaluation model"""
        try:
            if os.path.exists(self.model_path):
                import joblib
                self.model = joblib.load(self.model_path)
                logger.info("Loaded existing model")
            else:
                self.model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
                logger.info("Initialized new model")
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )

    def save_model(self):
        """Save the model to disk"""
        try:
            import joblib
            joblib.dump(self.model, self.model_path)
            logger.info("Model saved")
        except Exception as e:
            logger.error(f"Could not save model: {e}")

    def extract_features(self, board):
        """
        Extract comprehensive features from chess position
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
        Evaluate chess position using the trained model
        """
        if self.model is None:
            # Simple material evaluation fallback
            piece_values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0}
            value = 0
            for square in chess_lib.SQUARES:
                piece = board.piece_at(square)
                if piece:
                    piece_value = piece_values[piece.symbol().lower()]
                    value += piece_value if piece.color == chess_lib.WHITE else -piece_value
            return value / 100  # Normalize

        features = self.extract_features(board)
        features_scaled = self.scaler.transform([features])
        return self.model.predict(features_scaled)[0]

    def get_best_move_mcts(self, board, time_limit=5.0):
        """
        Use Monte Carlo Tree Search to find best move
        """
        if not board.legal_moves:
            return None

        legal_moves = list(board.legal_moves)
        if len(legal_moves) == 1:
            return legal_moves[0]

        start_time = time.time()

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
                    node.children[move] = MCTSNode(new_board, parent=node, move=move)

            # Simulation
            sim_board = node.board.copy()
            depth = 0
            while not sim_board.is_game_over() and depth < 50:
                if random.random() < 0.1:  # 10% chance of random move
                    move = random.choice(list(sim_board.legal_moves))
                else:
                    # Use model evaluation to guide random play
                    moves = list(sim_board.legal_moves)
                    if moves:
                        move_values = []
                        for move in moves:
                            temp_board = sim_board.copy()
                            temp_board.push(move)
                            value = self.evaluate_position(temp_board)
                            move_values.append(value)
                        # Choose move with best evaluation for current player
                        if sim_board.turn == chess_lib.WHITE:
                            move = moves[np.argmax(move_values)]
                        else:
                            move = moves[np.argmin(move_values)]
                    else:
                        break

                sim_board.push(move)
                depth += 1

            # Backpropagation
            result = self.get_game_result(sim_board)
            node.backpropagate(result)

        # Return best move
        if root.children:
            best_move = max(root.children.items(),
                          key=lambda x: x[1].visits)[0]
            return best_move

        return random.choice(legal_moves)

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
            if opponent_agent and board.turn == chess_lib.BLACK:
                # Play against opponent
                move = opponent_agent.get_best_move_mcts(board, time_limit=2.0)
            else:
                # Self-play or white's turn
                move = self.get_best_move_mcts(board, time_limit=2.0)

            if move is None:
                break

            # Store position before move
            features = self.extract_features(board)
            game_history.append({
                'fen': board.fen(),
                'move': move.uci(),
                'features': features,
                'turn': board.turn
            })

            board.push(move)
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
        Train the model on a completed game
        """
        training_samples = []

        # Calculate target values using TD learning
        for i, move_data in enumerate(game_data['moves']):
            features = move_data['features']
            fen = move_data['fen']

            # Target is the final result with discount
            target = game_data['result']

            # Discount based on move number (later moves matter less)
            discount = 0.99 ** (len(game_data['moves']) - i - 1)
            target *= discount

            training_samples.append((features, target))

        # Add to memory
        self.memory.extend(training_samples)

        # Train model if we have enough samples
        if len(self.memory) >= self.batch_size:
            self._train_model()

    def _train_model(self):
        """Train the position evaluation model"""
        if len(self.memory) < self.batch_size:
            return

        # Sample batch
        batch = random.sample(list(self.memory), min(self.batch_size, len(self.memory)))
        X = np.array([sample[0] for sample in batch])
        y = np.array([sample[1] for sample in batch])

        # Fit scaler if not fitted
        if not hasattr(self.scaler, 'mean_'):
            self.scaler.fit(X)

        X_scaled = self.scaler.transform(X)

        # Train model
        self.model.fit(X_scaled, y)
        logger.info(f"Trained model on {len(batch)} samples")

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
    def __init__(self, board, parent=None, move=None):
        self.board = board.copy()
        self.parent = parent
        self.move = move
        self.children = {}
        self.visits = 0
        self.value = 0.0

    def ucb1(self, total_visits):
        if self.visits == 0:
            return float('inf')
        exploitation = self.value / self.visits
        exploration = 1.4 * np.sqrt(np.log(total_visits) / self.visits)
        return exploitation + exploration

    def backpropagate(self, result):
        self.visits += 1
        self.value += result
        if self.parent:
            self.parent.backpropagate(result)


def main():
    """Main training function"""
    agent = ChessRLAgent()

    # Train through self-play
    agent.train_self_play(num_games=50, save_interval=5)

    # Generate final report
    final_report = agent.generate_report()

    # Print summary
    print("Training completed!")
    print(f"Final ELO: {agent.elo_rating}")
    print(f"Games played: {agent.games_played}")
    print(f"Win/Loss/Draw: {agent.wins}/{agent.losses}/{agent.draws}")

    return agent, final_report


if __name__ == "__main__":
    print("Starting Chess RL Agent Training...")
    print("Target: Reach 2000 ELO rating")
    print("=" * 50)

    agent, report = main()

    print("=" * 50)
    print("Training Summary:")
    print(f"Final ELO Rating: {report['elo_rating']}")
    print(f"Games Played: {report['games_played']}")
    print(f"Win Rate: {report['win_rate']:.2%}")
    print(f"Training Games: {report['training_games_count']}")
    print(f"Model Memory Size: {report['memory_size']}")

    if report['elo_rating'] >= 2000:
        print("🎉 SUCCESS: Agent reached 2000 ELO!")
    else:
        print(f"Current ELO: {report['elo_rating']} - Need {2000 - report['elo_rating']} more points to reach 2000")
