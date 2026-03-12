import pygame
import sys
import copy
import time
import math
import random

# Constants
WIDTH, HEIGHT = 600, 700
GRID_SIZE = 600
CELL_SIZE = GRID_SIZE // 9
SMALL_BOARD_SIZE = GRID_SIZE // 3
LINE_WIDTH = 2
THICK_LINE_WIDTH = 5

# Colors
WHITE = (245, 245, 245)
BLACK = (20, 20, 20)
GRAY = (200, 200, 200)
BLUE = (50, 120, 220)
RED = (220, 60, 60)
HIGHLIGHT_COLOR = (255, 255, 100, 100) # Semi-transparent yellow
RECOMMEND_COLOR = (0, 255, 100) # Green for recommendation
WEIGHT_TEXT_COLOR = (0, 100, 0) # Dark green for weight numbers
WIN_BG_PLAYER1 = (200, 220, 255)
WIN_BG_PLAYER2 = (255, 220, 220)

# Game Constants
PLAYER_X = 1
PLAYER_O = -1
EMPTY = 0

class SmallBoard:
    def __init__(self):
        self.cells = [[EMPTY for _ in range(3)] for _ in range(3)]
        self.winner = EMPTY
        self.is_full = False

    def check_winner(self):
        # Rows and Columns
        for i in range(3):
            if abs(sum(self.cells[i])) == 3:
                self.winner = self.cells[i][0]
                return self.winner
            if abs(sum(self.cells[j][i] for j in range(3))) == 3:
                self.winner = self.cells[0][i]
                return self.winner
        
        # Diagonals
        if abs(sum(self.cells[i][i] for i in range(3))) == 3:
            self.winner = self.cells[0][0]
            return self.winner
        if abs(sum(self.cells[i][2-i] for i in range(3))) == 3:
            self.winner = self.cells[0][2]
            return self.winner
        
        # Check if full
        if all(cell != EMPTY for row in self.cells for cell in row):
            self.is_full = True
            
        return EMPTY

    def get_score(self, player):
        """Heuristic for a small board."""
        if self.winner == player: return 100
        if self.winner == -player: return -100
        if self.is_full: return 0
        
        score = 0
        # Simple heuristic: center is good, corners are okay
        if self.cells[1][1] == player: score += 5
        elif self.cells[1][1] == -player: score -= 5
        
        corners = [(0,0), (0,2), (2,0), (2,2)]
        for r, c in corners:
            if self.cells[r][c] == player: score += 2
            elif self.cells[r][c] == -player: score -= 2
            
        return score

class SuperBoard:
    def __init__(self):
        self.boards = [[SmallBoard() for _ in range(3)] for _ in range(3)]
        self.global_winner = EMPTY
        self.next_board = None # (r, c) or None for any
        self.current_player = PLAYER_X

    def get_valid_moves(self):
        moves = []
        if self.next_board:
            br, bc = self.next_board
            board = self.boards[br][bc]
            if board.winner == EMPTY and not board.is_full:
                for r in range(3):
                    for c in range(3):
                        if board.cells[r][c] == EMPTY:
                            moves.append((br, bc, r, c))
                return moves
        
        # If no forced board or forced board is finished, any empty cell in any non-won board
        for br in range(3):
            for bc in range(3):
                board = self.boards[br][bc]
                if board.winner == EMPTY and not board.is_full:
                    for r in range(3):
                        for c in range(3):
                            if board.cells[r][c] == EMPTY:
                                moves.append((br, bc, r, c))
        return moves

    def make_move(self, br, bc, r, c):
        board = self.boards[br][bc]
        board.cells[r][c] = self.current_player
        board.check_winner()
        
        self.check_global_winner()
        
        # Determine next board
        target_board = self.boards[r][c]
        if target_board.winner == EMPTY and not target_board.is_full:
            self.next_board = (r, c)
        else:
            self.next_board = None
            
        self.current_player *= -1

    def check_global_winner(self):
        # Rows and Columns
        for i in range(3):
            row_sum = sum(self.boards[i][j].winner for j in range(3) if self.boards[i][j].winner != EMPTY)
            # This is tricky because sum might be 0 even if there are winners. 
            # We need 3 of the SAME winner.
            if self.boards[i][0].winner != EMPTY and self.boards[i][0].winner == self.boards[i][1].winner == self.boards[i][2].winner:
                self.global_winner = self.boards[i][0].winner
                return self.global_winner
            
            if self.boards[0][i].winner != EMPTY and self.boards[0][i].winner == self.boards[1][i].winner == self.boards[2][i].winner:
                self.global_winner = self.boards[0][i].winner
                return self.global_winner

        # Diagonals
        if self.boards[0][0].winner != EMPTY and self.boards[0][0].winner == self.boards[1][1].winner == self.boards[2][2].winner:
            self.global_winner = self.boards[0][0].winner
            return self.global_winner
        if self.boards[0][2].winner != EMPTY and self.boards[0][2].winner == self.boards[1][1].winner == self.boards[2][0].winner:
            self.global_winner = self.boards[0][2].winner
            return self.global_winner

        # Draw check
        if all(self.boards[br][bc].winner != EMPTY or self.boards[br][bc].is_full for br in range(3) for bc in range(3)):
            self.global_winner = 0 # Draw handled by check
            # Actually we should return something to indicate draw if no winner
            
        return EMPTY

    def evaluate(self, player):
        if self.global_winner == player: return 10000
        if self.global_winner == -player: return -10000
        
        score = 0
        # Evaluate each small board
        for br in range(3):
            for bc in range(3):
                board_score = self.boards[br][bc].get_score(player)
                # Multiply board score based on position in super board
                weight = 1
                if (br, bc) == (1, 1): weight = 3
                elif (br, bc) in [(0,0), (0,2), (2,0), (2,2)]: weight = 2
                score += board_score * weight
                
        # Also look for 2-in-a-row on the super board
        # (Simplified implementation here)
        return score

class AI:
    def __init__(self, depth=4):
        self.depth = depth

    def minimax(self, board, depth, alpha, beta, is_maximizing, player):
        winner = board.check_global_winner()
        if winner != EMPTY or depth == 0 or not board.get_valid_moves():
            return board.evaluate(player)

        if is_maximizing:
            max_eval = -math.inf
            for move in board.get_valid_moves():
                temp_board = copy.deepcopy(board)
                temp_board.make_move(*move)
                eval = self.minimax(temp_board, depth - 1, alpha, beta, False, player)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = math.inf
            for move in board.get_valid_moves():
                temp_board = copy.deepcopy(board)
                temp_board.make_move(*move)
                eval = self.minimax(temp_board, depth - 1, alpha, beta, True, player)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def get_best_move(self, board):
        player = board.current_player
        moves = board.get_valid_moves()
        if not moves: return None
        
        best_move = None
        best_val = -math.inf
        
        random.shuffle(moves)
        for move in moves:
            temp_board = copy.deepcopy(board)
            temp_board.make_move(*move)
            val = self.minimax(temp_board, self.depth - 1, -math.inf, math.inf, False, player)
            if val > best_val:
                best_val = val
                best_move = move
        return best_move

    def get_move_evaluations(self, board):
        player = board.current_player
        moves = board.get_valid_moves()
        if not moves: return {}
        
        evals = {}
        for move in moves:
            temp_board = copy.deepcopy(board)
            temp_board.make_move(*move)
            val = self.minimax(temp_board, self.depth - 1, -math.inf, math.inf, False, player)
            evals[move] = val
            
        # Normalize scores to 0-1 range
        if not evals: return {}
        
        min_score = min(evals.values())
        max_score = max(evals.values())
        
        normalized = {}
        if max_score > min_score:
            for move, score in evals.items():
                normalized[move] = (score - min_score) / (max_score - min_score)
        else:
            for move in evals:
                normalized[move] = 1.0
                
        return normalized

class GameGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Super Tic-Tac-Toe AI")
        self.font = pygame.font.SysFont("Arial", 24)
        self.big_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.reset()

    def reset(self):
        self.board = SuperBoard()
        self.ai = AI(depth=4)
        self.recommended_move = None
        self.move_weights = {} # (move) -> normalized_score
        self.game_over = False
        self.update_recommendation()

    def update_recommendation(self):
        if not self.game_over and self.board.current_player == PLAYER_X:
            # Get evaluations for all moves
            self.move_weights = self.ai.get_move_evaluations(self.board)
            if self.move_weights:
                self.recommended_move = max(self.move_weights, key=self.move_weights.get)
            else:
                self.recommended_move = None
        else:
            self.move_weights = {}
            self.recommended_move = None

    def draw_grid(self):
        self.screen.fill(WHITE)
        
        # Draw board backgrounds for winners
        for br in range(3):
            for bc in range(3):
                winner = self.board.boards[br][bc].winner
                rect = pygame.Rect(bc * SMALL_BOARD_SIZE, br * SMALL_BOARD_SIZE, SMALL_BOARD_SIZE, SMALL_BOARD_SIZE)
                if winner == PLAYER_X:
                    pygame.draw.rect(self.screen, WIN_BG_PLAYER1, rect)
                elif winner == PLAYER_O:
                    pygame.draw.rect(self.screen, WIN_BG_PLAYER2, rect)
                
                # Highlight active board
                if self.board.next_board == (br, bc) and not self.game_over:
                    pygame.draw.rect(self.screen, (230, 230, 255), rect)
                elif self.board.next_board is None and winner == EMPTY and not self.board.boards[br][bc].is_full and not self.game_over:
                     # If free move, don't necessarily highlight all, just wait for input
                     pass

        # Draw small lines
        for i in range(1, 9):
            width = THICK_LINE_WIDTH if i % 3 == 0 else LINE_WIDTH
            # Vertical
            pygame.draw.line(self.screen, GRAY if width == LINE_WIDTH else BLACK, (i * CELL_SIZE, 0), (i * CELL_SIZE, GRID_SIZE), width)
            # Horizontal
            pygame.draw.line(self.screen, GRAY if width == LINE_WIDTH else BLACK, (0, i * CELL_SIZE), (GRID_SIZE, i * CELL_SIZE), width)

        # Draw thick outer lines
        pygame.draw.line(self.screen, BLACK, (0, 0), (0, GRID_SIZE), THICK_LINE_WIDTH)
        pygame.draw.line(self.screen, BLACK, (GRID_SIZE, 0), (GRID_SIZE, GRID_SIZE), THICK_LINE_WIDTH)
        pygame.draw.line(self.screen, BLACK, (0, 0), (GRID_SIZE, 0), THICK_LINE_WIDTH)
        pygame.draw.line(self.screen, BLACK, (0, GRID_SIZE), (GRID_SIZE, GRID_SIZE), THICK_LINE_WIDTH)

        # Draw X and O
        for br in range(3):
            for bc in range(3):
                small_board = self.board.boards[br][bc]
                for r in range(3):
                    for c in range(3):
                        cell = small_board.cells[r][c]
                        center_x = bc * SMALL_BOARD_SIZE + c * CELL_SIZE + CELL_SIZE // 2
                        center_y = br * SMALL_BOARD_SIZE + r * CELL_SIZE + CELL_SIZE // 2
                        
                        if cell == PLAYER_X:
                            self.draw_x(center_x, center_y, CELL_SIZE // 3)
                        elif cell == PLAYER_O:
                            self.draw_o(center_x, center_y, CELL_SIZE // 3)
                
                # Draw big X/O for small board winner
                if small_board.winner != EMPTY:
                    bx = bc * SMALL_BOARD_SIZE + SMALL_BOARD_SIZE // 2
                    by = br * SMALL_BOARD_SIZE + SMALL_BOARD_SIZE // 2
                    if small_board.winner == PLAYER_X:
                        self.draw_x(bx, by, SMALL_BOARD_SIZE // 2.5, width=10, color=(50, 50, 255, 100))
                    else:
                        self.draw_o(bx, by, SMALL_BOARD_SIZE // 2.5, width=10, color=(255, 50, 50, 100))

        # Highlight recommendation and draw weights
        for move, weight in self.move_weights.items():
            br, bc, r, c = move
            x = bc * SMALL_BOARD_SIZE + c * CELL_SIZE
            y = br * SMALL_BOARD_SIZE + r * CELL_SIZE
            
            # Draw weight text
            weight_text = f"{weight:.2f}"
            weight_surface = self.font.render(weight_text, True, WEIGHT_TEXT_COLOR)
            text_rect = weight_surface.get_rect(center=(x + CELL_SIZE // 2, y + CELL_SIZE // 2))
            
            # Add a small semi-transparent background for the text to make it readable
            bg_rect = text_rect.inflate(4, 4)
            s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            s.fill((255, 255, 255, 180))
            self.screen.blit(s, bg_rect.topleft)
            self.screen.blit(weight_surface, text_rect)

        if self.recommended_move:
            br, bc, r, c = self.recommended_move
            rect = pygame.Rect(bc * SMALL_BOARD_SIZE + c * CELL_SIZE + 2, 
                               br * SMALL_BOARD_SIZE + r * CELL_SIZE + 2, 
                               CELL_SIZE - 4, CELL_SIZE - 4)
            pygame.draw.rect(self.screen, RECOMMEND_COLOR, rect, 3)

    def draw_x(self, x, y, size, width=3, color=BLUE):
        pygame.draw.line(self.screen, color, (x - size, y - size), (x + size, y + size), width)
        pygame.draw.line(self.screen, color, (x + size, y - size), (x - size, y + size), width)

    def draw_o(self, x, y, size, width=3, color=RED):
        pygame.draw.circle(self.screen, color, (x, y), size, width)

    def draw_ui(self):
        # Bottom area
        ui_rect = pygame.Rect(0, GRID_SIZE, WIDTH, HEIGHT - GRID_SIZE)
        pygame.draw.rect(self.screen, (240, 240, 240), ui_rect)
        pygame.draw.line(self.screen, BLACK, (0, GRID_SIZE), (WIDTH, GRID_SIZE), 2)
        
        status_text = ""
        if self.game_over:
            if self.board.global_winner == PLAYER_X:
                status_text = "Human (X) Wins!"
            elif self.board.global_winner == PLAYER_O:
                status_text = "AI (O) Wins!"
            else:
                status_text = "It's a Draw!"
        else:
            status_text = f"Current Player: {'Human (X)' if self.board.current_player == PLAYER_X else 'AI (O)'}"
        
        txt_surface = self.font.render(status_text, True, BLACK)
        self.screen.blit(txt_surface, (20, GRID_SIZE + 20))
        
        if not self.game_over and self.board.current_player == PLAYER_X:
            rec_text = "Move Weights (0.0 - 1.0): 1.0 is Best"
            rec_surface = self.font.render(rec_text, True, (0, 100, 0))
            self.screen.blit(rec_surface, (20, GRID_SIZE + 50))
            
        # Restart Button
        self.restart_rect = pygame.Rect(WIDTH - 120, GRID_SIZE + 25, 100, 40)
        pygame.draw.rect(self.screen, (100, 100, 100), self.restart_rect)
        restart_txt = self.font.render("Restart", True, WHITE)
        self.screen.blit(restart_txt, (WIDTH - 105, GRID_SIZE + 32))

    def handle_click(self, pos):
        if self.restart_rect.collidepoint(pos):
            self.reset()
            return

        if self.game_over or self.board.current_player != PLAYER_X:
            return

        x, y = pos
        if y >= GRID_SIZE: return

        bc, br = x // SMALL_BOARD_SIZE, y // SMALL_BOARD_SIZE
        c, r = (x % SMALL_BOARD_SIZE) // CELL_SIZE, (y % SMALL_BOARD_SIZE) // CELL_SIZE
        
        move = (br, bc, r, c)
        if move in self.board.get_valid_moves():
            self.board.make_move(*move)
            if self.board.global_winner != EMPTY or not self.board.get_valid_moves():
                self.game_over = True
            
            self.move_weights = {}
            self.recommended_move = None # Clear while AI thinks
            return True
        return False

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.handle_click(pygame.mouse.get_pos()):
                        # Human just moved, draw state before AI thinks
                        self.draw_grid()
                        self.draw_ui()
                        pygame.display.flip()
                        
            # AI Move
            if not self.game_over and self.board.current_player == PLAYER_O:
                # Small delay for visual feedback
                time.sleep(0.5)
                ai_move = self.ai.get_best_move(self.board)
                if ai_move:
                    self.board.make_move(*ai_move)
                
                if self.board.global_winner != EMPTY or not self.board.get_valid_moves():
                    self.game_over = True
                
                self.update_recommendation()

            self.draw_grid()
            self.draw_ui()
            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    game = GameGUI()
    game.run()
