import itertools
import collections

given_cells = {
    (0,0): 27, (0,6): 105, (0,12): 12,
    (2,0): 5, (2,2): 4, (2,4): 20, (2,9): 12,
    (4,2): 32, (4,4): 92,
    (8,8): 4,
    (10,0): 46, (10,10): 13,
    (12,0): 8,
    (14,4): 8, (14,8): 28
}

green_numbers = [
    112, 11, 37, 2, 9, 1, 4, 9,
    8, 60, 4, 2, 17, 1, 15, 1,
    2, 12, 13, 28, 7, 15, 9
]

pool_counts = collections.Counter(green_numbers)
pool_list = sorted(pool_counts.elements())

variables = []
for r in range(15):
    for c in range(15):
        if (r, c) not in given_cells:
            variables.append((r, c))

variable_names = {}
for i, v in enumerate(variables):
    variable_names[v] = f"V{i}"

equations = []

equations.append(([(0,0), (2,0)], '+', (4,0)))
equations.append(([(4,0), (6,0)], '+', (8,0)))
equations.append(([(0,0), (0,2)], '*', (0,6)))
equations.append(([(0,2), (2,2)], '*', (2,4)))
equations.append(([(0,2), (2,2), (4,2)], '*', (4,4)))
equations.append(([(0,6), (2,6)], '-', (0,8)))
equations.append(([(0,8), (0,10)], '-', (0,12)))
equations.append(([(0,12), (2,12)], '+', (2,10)))
equations.append(([(2,10), (4,10)], '-', (4,10)))
equations.append(([(4,4), (6,4)], '+', (8,4)))
equations.append(([(4,6), (6,6)], '*', (6,8)))
equations.append(([(6,6), (6,8)], '*', (6,10)))
equations.append(([(6,8), (6,10)], '/', (8,10)))
equations.append(([(8,8), (10,8)], '-', (12,8)))
equations.append(([(10,0), (10,2)], '-', (10,4)))
equations.append(([(10,4), (10,6)], '+', (10,8)))
equations.append(([(10,8), (10,10)], '+', (10,12)))
equations.append(([(10,10), (12,10)], '-', (14,10)))
equations.append(([(12,0), (12,2)], '-', (12,4)))
equations.append(([(12,4), (12,6)], '+', (12,8)))
equations.append(([(12,8), (12,10)], '-', (12,12)))
equations.append(([(14,0), (14,2)], '-', (14,4)))
equations.append(([(14,4), (14,6)], '-', (14,8)))
equations.append(([(14,8), (14,10)], '-', (14,12)))

def evaluate(vals, op):
    if op == '+':
        return sum(vals)
    elif op == '-':
        return vals[0] - vals[1]
    elif op == '*':
        res = 1
        for v in vals:
            res *= v
        return res
    elif op == '/':
        return vals[0] // vals[1] if vals[1] != 0 else None
    return None

def solve():
    var_list = list(variable_names.keys())
    n = len(var_list)
    assignment = {}
    used_numbers = collections.Counter()
    
    def backtrack(idx):
        if idx == n:
            return True
        
        r, c = var_list[idx]
        
        if (r, c) in given_cells:
            assignment[(r, c)] = given_cells[(r, c)]
            if backtrack(idx + 1):
                return True
            del assignment[(r, c)]
            return False
        
        for num in pool_counts.keys():
            if used_numbers[num] < pool_counts[num]:
                assignment[(r, c)] = num
                used_numbers[num] += 1
                
                valid = True
                for eq_vars, op, res_cell in equations:
                    all_assigned = True
                    for v in eq_vars:
                        if v not in assignment and v not in given_cells:
                            all_assigned = False
                            break
                    if res_cell not in assignment and res_cell not in given_cells:
                        all_assigned = False
                    
                    if all_assigned:
                        vals = []
                        for v in eq_vars:
                            if v in given_cells:
                                vals.append(given_cells[v])
                            else:
                                vals.append(assignment[v])
                        res_val = given_cells[res_cell] if res_cell in given_cells else assignment[res_cell]
                        
                        expected = evaluate(vals, op)
                        if expected is None or expected != res_val:
                            valid = False
                            break
                
                if valid:
                    if backtrack(idx + 1):
                        return True
                
                used_numbers[num] -= 1
                del assignment[(r, c)]
        
        return False

    if backtrack(0):
        return assignment
    return None

solution = solve()
if solution:
    for (r, c), val in sorted(solution.items()):
        print(f"Row {r}, Col {c}: {val}")
else:
    print("No solution found")