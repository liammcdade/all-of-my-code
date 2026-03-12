import tkinter as tk
from tkinter import messagebox
import copy

def check_win(board, player):
    # Check rows
    for row in board:
        if all(cell == player for cell in row):
            return True
    # Check columns
    for col in range(3):
        if all(board[row][col] == player for row in range(3)):
            return True
    # Check diagonals
    if all(board[i][i] == player for i in range(3)):
        return True
    if all(board[i][2 - i] == player for i in range(3)):
        return True
    return False

def is_full(board):
    return all(all(cell != " " for cell in row) for row in board)

def opponent(p):
    return "O" if p == "X" else "X"

def win_prob(board, turn, player, cache):
    key = (tuple(tuple(row) for row in board), turn)
    if key in cache:
        return cache[key]
    
    if check_win(board, player):
        cache[key] = 1.0
        return 1.0
    if check_win(board, opponent(player)):
        cache[key] = 0.0
        return 0.0
    if is_full(board):
        cache[key] = 0.0
        return 0.0
    
    empties = [(i, j) for i in range(3) for j in range(3) if board[i][j] == " "]
    
    if not empties:
        cache[key] = 0.0
        return 0.0
    
    prob = 0.0
    for pos in empties:
        new_board = copy.deepcopy(board)
        new_board[pos[0]][pos[1]] = turn
        new_turn = opponent(turn)
        prob += win_prob(new_board, new_turn, player, cache)
    prob /= len(empties)
    
    cache[key] = prob
    return prob

class TicTacToe:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tic-Tac-Toe with Move Suggestions")
        
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        self.current_player = "X"
        
        self.buttons = [[None for _ in range(3)] for _ in range(3)]
        for i in range(3):
            for j in range(3):
                self.buttons[i][j] = tk.Button(self.root, text="", font=("Helvetica", 24), width=6, height=3,
                                               command=lambda x=i, y=j: self.make_move(x, y))
                self.buttons[i][j].grid(row=i, column=j)
        
        self.update_suggestions()
        self.root.mainloop()
    
    def make_move(self, i, j):
        if self.board[i][j] != " ":
            return
        
        self.board[i][j] = self.current_player
        self.buttons[i][j].config(text=self.current_player)
        
        if check_win(self.board, self.current_player):
            messagebox.showinfo("Game Over", f"{self.current_player} wins!")
            self.root.quit()
            return
        
        if is_full(self.board):
            messagebox.showinfo("Game Over", "It's a draw!")
            self.root.quit()
            return
        
        self.current_player = opponent(self.current_player)
        self.update_suggestions()
    
    def update_suggestions(self):
        for i in range(3):
            for j in range(3):
                if self.board[i][j] != " ":
                    self.buttons[i][j].config(text=self.board[i][j])
                else:
                    self.buttons[i][j].config(text="")
        
        if check_win(self.board, "X") or check_win(self.board, "O") or is_full(self.board):
            return
        
        empties = [(i, j) for i in range(3) for j in range(3) if self.board[i][j] == " "]
        cache = {}
        
        for pos in empties:
            new_board = copy.deepcopy(self.board)
            new_board[pos[0]][pos[1]] = self.current_player
            opp = opponent(self.current_player)
            
            # Check immediate win or draw after hypothetical move
            if check_win(new_board, self.current_player):
                percent = 100
            elif is_full(new_board):
                percent = 0
            else:
                prob = win_prob(new_board, opp, self.current_player, cache)
                percent = int(prob * 100)
            
            self.buttons[pos[0]][pos[1]].config(text=f"{percent}%")

if __name__ == "__main__":
    TicTacToe()