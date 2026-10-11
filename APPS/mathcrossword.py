import tkinter as tk
from tkinter import ttk
import random
import time
import sys

# ================= CONFIGURATION =================
GRID_SIZE = 20          # 20x20 visual grid cells
NUM_SIZE = 10           # Logical 10x10 number matrix
OPS = ['+', '-', '÷']
UPDATE_MS = 200         # Update rate (5 fps)
GIVEN_PERCENTAGE = 0.30 # 30% of numbers are given
MAX_VAL = 50            # Max number value to keep it clean
MIN_VAL = 1             # Min number value
# =================================================

class MathCrossword:
    def __init__(self, root):
        self.root = root
        self.root.title("Math Crossword 20x20")
        
        # Full screen setup
        self.root.state('zoomed') 
        self.root.configure(bg="#f8f9fa")
        
        # Data structures
        self.numbers = [[0]*NUM_SIZE for _ in range(NUM_SIZE)] # The solution
        self.h_ops = [['']*NUM_SIZE for _ in range(NUM_SIZE)]  # Horizontal ops
        self.v_ops = [['']*NUM_SIZE for _ in range(NUM_SIZE)]  # Vertical ops
        
        # UI Elements storage
        self.entries = {} # Map (r,c) -> Entry widget
        self.labels = {}  # Map (r,c) -> Label widget (for ops/equals)
        self.given_cells = set()
        
        self.generate_puzzle()
        self.build_ui()
        self.start_timer()
        
    def generate_puzzle(self):
        """Generates a valid interconnected 10x10 number grid."""
        # We use a backtracking approach to fill the 10x10 logical grid
        # ensuring all horizontal and vertical equations hold.
        
        # Initialize with zeros
        self.numbers = [[0]*NUM_SIZE for _ in range(NUM_SIZE)]
        self.h_ops = [['']*NUM_SIZE for _ in range(NUM_SIZE)]
        self.v_ops = [['']*NUM_SIZE for _ in range(NUM_SIZE)]
        
        # Helper to check if a number is valid
        def is_valid(n):
            return MIN_VAL <= n <= MAX_VAL and n == int(n)
            
        # Recursive backtracking solver
        def solve(idx):
            if idx == NUM_SIZE * NUM_SIZE:
                return True
            
            r, c = divmod(idx, NUM_SIZE)
            
            # Determine possible values based on previous neighbors
            candidates = list(range(MIN_VAL, MAX_VAL + 1))
            random.shuffle(candidates) # Randomize to get different puzzles
            
            for val in candidates:
                self.numbers[r][c] = val
                
                # Check constraints imposed by LEFT neighbor (Horizontal Eq)
                if c >= 2:
                    # Equation: N[r][c-2] op N[r][c-1] = N[r][c]
                    a = self.numbers[r][c-2]
                    b = self.numbers[r][c-1]
                    
                    # Try to find an operator that makes this true
                    valid_h_op = None
                    if a + b == val: valid_h_op = '+'
                    elif a - b == val: valid_h_op = '-'
                    elif b != 0 and a % b == 0 and a // b == val: valid_h_op = '÷'
                    
                    if not valid_h_op: continue
                    self.h_ops[r][c-1] = valid_h_op # Store op between c-2 and c-1? 
                    # Wait, standard notation: Cell(0) Op Cell(1) = Cell(2).
                    # So Op is at index 1 relative to the triplet.
                    # In our grid, Ops are stored logically. 
                    # Let's store H_Op[r][c-1] as the op between c-2 and c-1? 
                    # No, let's store H_Op[r][c-1] as the op BEFORE cell c?
                    # Actually, simpler: The op is physically located between numbers.
                    # If we are at c, the op involved is at logical position c-1 (between c-2 and c-1?? No).
                    # Triplet: c-2, c-1, c. Op is between c-2 and c-1.
                    self.h_ops[r][c-1] = valid_h_op # Assign op for the slot ending at c
                    
                # Check constraints imposed by TOP neighbor (Vertical Eq)
                if r >= 2:
                    # Equation: N[r-2][c] op N[r-1][c] = N[r][c]
                    a = self.numbers[r-2][c]
                    b = self.numbers[r-1][c]
                    
                    valid_v_op = None
                    if a + b == val: valid_v_op = '+'
                    elif a - b == val: valid_v_op = '-'
                    elif b != 0 and a % b == 0 and a // b == val: valid_v_op = '÷'
                    
                    if not valid_v_op: continue
                    self.v_ops[r-1][c] = valid_v_op

                # If we passed checks, recurse
                if solve(idx + 1):
                    return True
                    
            # Backtrack
            self.numbers[r][c] = 0
            return False

        # Start solving
        solved = solve(0)
        if not solved:
            print("Error: Could not generate a valid puzzle. Retrying...")
            # In a real app, we'd loop until success. For now, we assume success or crash.
            sys.exit()

    def build_ui(self):
        # --- Header ---
        header_frame = tk.Frame(self.root, bg="#f8f9fa", pady=10)
        header_frame.pack(fill=tk.X)
        
        title_lbl = tk.Label(header_frame, text="Math Crossword", 
                             font=("Segoe UI", 24, "bold"), bg="#f8f9fa", fg="#2c3e50")
        title_lbl.pack(side=tk.LEFT, padx=20)
        
        self.timer_lbl = tk.Label(header_frame, text="Time: 00:00", 
                                  font=("Segoe UI", 14), bg="#f8f9fa", fg="#7f8c8d")
        self.timer_lbl.pack(side=tk.RIGHT, padx=20)

        # --- Main Grid Area ---
        main_frame = tk.Frame(self.root, bg="#ffffff")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Canvas for scrolling if needed (though 20x20 fits most screens)
        canvas = tk.Canvas(main_frame, bg="#ffffff", highlightthickness=0)
        scrollbar_y = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollbar_x = tk.Scrollbar(main_frame, orient="horizontal", command=canvas.xview)
        
        grid_container = tk.Frame(canvas, bg="#ffffff")
        
        # Configure grid weights for uniform sizing
        for i in range(GRID_SIZE):
            grid_container.grid_rowconfigure(i, weight=1, minsize=30)
            grid_container.grid_columnconfigure(i, weight=1, minsize=30)
            
        canvas.create_window((0, 0), window=grid_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")

        # --- Populate Grid ---
        # Visual Grid Mapping:
        # Even Row, Even Col -> Number
        # Even Row, Odd Col  -> Horizontal Operator
        # Odd Row, Even Col  -> Vertical Operator
        # Odd Row, Odd Col   -> Equals Sign (=)
        
        # Determine Givens
        all_cells = [(r, c) for r in range(NUM_SIZE) for c in range(NUM_SIZE)]
        random.shuffle(all_cells)
        num_givens = int(len(all_cells) * GIVEN_PERCENTAGE)
        given_set_coords = set(all_cells[:num_givens])
        
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                # Determine logical coordinates
                log_r, log_c = r // 2, c // 2
                
                if r % 2 == 0 and c % 2 == 0:
                    # NUMBER CELL
                    val = self.numbers[log_r][log_c]
                    is_given = (log_r, log_c) in given_set_coords
                    
                    if is_given:
                        lbl = tk.Label(grid_container, text=str(val),
                                       font=("Consolas", 14, "bold"),
                                       bg="#ffffff", fg="#2c3e50",
                                       relief="solid", borderwidth=1,
                                       width=3, height=1)
                        lbl.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                        self.given_cells.add((log_r, log_c))
                    else:
                        ent = tk.Entry(grid_container, font=("Consolas", 14),
                                       justify="center", width=3,
                                       bg="#ffffff", fg="#000",
                                       relief="solid", borderwidth=1)
                        ent.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                        # Store reference for scoring
                        self.entries[(log_r, log_c)] = ent
                        
                elif r % 2 == 0 and c % 2 == 1:
                    # HORIZONTAL OPERATOR
                    # Located between log_c-1 and log_c? 
                    # Visual: [N] [Op] [N] [Eq] [N]
                    # Indices: 0   1    2   3    4
                    # Log C:   0        1        2
                    # Op at visual col 1 corresponds to h_ops[log_r][log_c] ??
                    # Let's map: Visual Col 1 is Op for Eq ending at Visual Col 2 (Log C 1).
                    # So Op is h_ops[log_r][log_c].
                    op_char = self.h_ops[log_r][log_c]
                    lbl = tk.Label(grid_container, text=op_char,
                                   font=("Segoe UI", 16, "bold"),
                                   bg="#ffffff", fg="#00a896") # Teal color
                    lbl.grid(row=r, column=c, sticky="nsew")
                    
                elif r % 2 == 1 and c % 2 == 0:
                    # VERTICAL OPERATOR
                    # Visual Row 1 is Op for Eq ending at Visual Row 2 (Log R 1).
                    op_char = self.v_ops[log_r][log_c]
                    lbl = tk.Label(grid_container, text=op_char,
                                   font=("Segoe UI", 16, "bold"),
                                   bg="#ffffff", fg="#00a896")
                    lbl.grid(row=r, column=c, sticky="nsew")
                    
                elif r % 2 == 1 and c % 2 == 1:
                    # EQUALS SIGN
                    lbl = tk.Label(grid_container, text="=",
                                   font=("Segoe UI", 16, "bold"),
                                   bg="#ffffff", fg="#00a896")
                    lbl.grid(row=r, column=c, sticky="nsew")

        # --- Footer / Progress ---
        footer_frame = tk.Frame(self.root, bg="#f8f9fa", pady=15)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(footer_frame, variable=self.progress_var, 
                                            maximum=100, length=400)
        self.progress_bar.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)
        
        self.score_lbl = tk.Label(footer_frame, text="0.00000 / 100", 
                                  font=("Segoe UI", 12, "bold"), 
                                  bg="#f8f9fa", fg="#2c3e50")
        self.score_lbl.pack(side=tk.RIGHT, padx=20)
        
        btn_clear = tk.Button(footer_frame, text="Clear All", 
                              command=self.clear_entries,
                              bg="#e0e0e0", fg="#333", relief="flat", padx=10)
        btn_clear.pack(side=tk.RIGHT, padx=10)

    def clear_entries(self):
        for ent in self.entries.values():
            ent.delete(0, tk.END)

    def start_timer(self):
        self.start_time = time.time()
        self.update_loop()

    def update_loop(self):
        # Update Timer
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        self.timer_lbl.config(text=f"Time: {mins:02d}:{secs:02d}")
        
        # Calculate Score
        score = self.calculate_score()
        self.progress_var.set(score)
        self.score_lbl.config(text=f"{score:.5f} / 100")
        
        # Schedule next update (5 FPS)
        self.root.after(UPDATE_MS, self.update_loop)

    def calculate_score(self):
        total_equations = 0
        total_score = 0.0
        
        # Check Horizontal Equations
        for r in range(NUM_SIZE):
            for c in range(2, NUM_SIZE): # Equations end at index 2, 4, etc? 
                # Wait, our generation logic was: N[c-2] op N[c-1] = N[c]
                # This creates a chain. 
                # We need to verify every triplet defined by our ops.
                
                # Get values
                n1 = self.get_val(r, c-2)
                n2 = self.get_val(r, c-1)
                n3 = self.get_val(r, c)
                op = self.h_ops[r][c-1] # Op stored at the middle index of the triplet logic?
                # Actually, in build_ui, we mapped visual col 1 (log c=0?? No)
                # Let's re-verify mapping.
                # Visual Col 0 (Log 0), Visual Col 1 (Op), Visual Col 2 (Log 1).
                # So Op at Visual 1 connects Log 0 and Log 1? 
                # But equation is A op B = C.
                # In a chain: A op B = C, then C op D = E.
                # The op is BETWEEN the first two numbers.
                
                # Let's just iterate through the explicit equations generated.
                pass 

        # Simpler Scoring: Iterate through all logical equations explicitly
        # Horizontal: For each row, for each step of 2? 
        # No, the generation created a dependency chain.
        # Eq 1: N[0] op N[1] = N[2]
        # Eq 2: N[2] op N[3] = N[4]
        
        eq_count = 0
        correct_sum = 0.0
        
        # Horizontal Checks
        for r in range(NUM_SIZE):
            for start_c in range(0, NUM_SIZE - 2, 2):
                # Triplet: start_c, start_c+1, start_c+2
                # Op is associated with the result at start_c+2? 
                # In generate_puzzle, we stored h_ops[r][c-1] when filling c.
                # So for triplet ending at c, op is at c-1.
                c_end = start_c + 2
                op = self.h_ops[r][c_end-1] 
                
                v1 = self.get_val(r, start_c)
                v2 = self.get_val(r, start_c+1)
                v3 = self.get_val(r, c_end)
                
                if v1 is not None and v2 is not None and v3 is not None:
                    eq_count += 1
                    target = self.apply_op(v1, v2, op)
                    if target is not None:
                        err = abs(target - v3)
                        if err < 0.001:
                            correct_sum += 1.0
                        else:
                            # Partial credit
                            correct_sum += max(0, 1.0 - (err / 10.0))

        # Vertical Checks
        for c in range(NUM_SIZE):
            for start_r in range(0, NUM_SIZE - 2, 2):
                r_end = start_r + 2
                op = self.v_ops[r_end-1][c]
                
                v1 = self.get_val(start_r, c)
                v2 = self.get_val(start_r+1, c)
                v3 = self.get_val(r_end, c)
                
                if v1 is not None and v2 is not None and v3 is not None:
                    eq_count += 1
                    target = self.apply_op(v1, v2, op)
                    if target is not None:
                        err = abs(target - v3)
                        if err < 0.001:
                            correct_sum += 1.0
                        else:
                            correct_sum += max(0, 1.0 - (err / 10.0))
                            
        if eq_count == 0: return 0.0
        return (correct_sum / eq_count) * 100

    def get_val(self, r, c):
        # Check if it's a given
        if (r, c) in self.given_cells:
            return self.numbers[r][c]
        
        # Check entry
        ent = self.entries.get((r, c))
        if ent:
            txt = ent.get().strip()
            if txt == "": return None
            try:
                return float(txt)
            except ValueError:
                return None
        return None

    def apply_op(self, a, b, op):
        if op == '+': return a + b
        if op == '-': return a - b
        if op == '÷': 
            if b == 0: return None
            return a / b
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = MathCrossword(root)
    root.mainloop()