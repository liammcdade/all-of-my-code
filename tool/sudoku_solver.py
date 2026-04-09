import tkinter as tk
from tkinter import messagebox


class SudokuSolver:
    def __init__(self):
        self.grid = [[0 for _ in range(9)] for _ in range(9)]

    def is_valid(self, row, col, num):
        for x in range(9):
            if self.grid[row][x] == num:
                return False

        for x in range(9):
            if self.grid[x][col] == num:
                return False

        start_row = row - row % 3
        start_col = col - col % 3

        for i in range(3):
            for j in range(3):
                if self.grid[start_row + i][start_col + j] == num:
                    return False

        return True

    def find_empty(self):
        for row in range(9):
            for col in range(9):
                if self.grid[row][col] == 0:
                    return row, col
        return None


class SudokuGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sudoku Step Solver")

        self.solver = SudokuSolver()
        self.entries = []

        self.create_grid()

        tk.Button(root, text="Solve Step-by-Step", command=self.start_solve).grid(row=10, column=0, columnspan=4)
        tk.Button(root, text="Clear", command=self.clear).grid(row=10, column=4, columnspan=4)

    def create_grid(self):
        for r in range(9):
            row = []
            for c in range(9):
                e = tk.Entry(self.root, width=3, justify="center", font=("Arial", 18))
                e.grid(row=r, column=c, padx=1, pady=1)
                row.append(e)
            self.entries.append(row)

    def read_grid(self):
        for r in range(9):
            for c in range(9):
                val = self.entries[r][c].get()
                if val == "":
                    self.solver.grid[r][c] = 0
                else:
                    try:
                        self.solver.grid[r][c] = int(val)
                    except:
                        messagebox.showerror("Error", "Only numbers allowed")
                        return False
        return True

    def update_gui(self):
        for r in range(9):
            for c in range(9):
                self.entries[r][c].delete(0, tk.END)
                if self.solver.grid[r][c] != 0:
                    self.entries[r][c].insert(0, str(self.solver.grid[r][c]))
        self.root.update()

    def solve_step(self):
        empty = self.solver.find_empty()

        if not empty:
            return True

        row, col = empty

        for num in range(1, 20):
            if self.solver.is_valid(row, col, num):
                self.solver.grid[row][col] = num
                self.update_gui()

                self.root.after(5)

                if self.solve_step():
                    return True

                self.solver.grid[row][col] = 0
                self.update_gui()
                self.root.after(20)

        return False

    def start_solve(self):
        if self.read_grid():
            if not self.solve_step():
                messagebox.showerror("Error", "No solution exists")

    def clear(self):
        for r in range(11):
            for c in range(11):
                self.entries[r][c].delete(0, tk.END)
        self.solver.grid = [[0 for _ in range(11)] for _ in range(11)]


if __name__ == "__main__":
    root = tk.Tk()
    gui = SudokuGUI(root)
    root.mainloop()