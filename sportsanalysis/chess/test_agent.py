"""
Test script for the Chess RL Agent
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the chess module first
import chess

# Now import our agent
from chess import ChessRLAgent

def test_agent():
    """Test the basic functionality of the Chess RL Agent"""
    print("Testing Chess RL Agent...")

    # Initialize agent
    agent = ChessRLAgent()
    print("✓ Agent initialized successfully")

    # Test board creation
    board = chess.Board()
    print("✓ Chess board created successfully")

    # Test feature extraction
    features = agent.extract_features(board)
    print(f"✓ Features extracted: {len(features)} features")

    # Test position evaluation
    evaluation = agent.evaluate_position(board)
    print(f"✓ Position evaluation: {evaluation:.3f}")

    # Test move generation
    move = agent.get_best_move_mcts(board, time_limit=1.0)
    print(f"✓ Best move found: {move}")

    print("All tests passed! 🎉")

if __name__ == "__main__":
    test_agent()
