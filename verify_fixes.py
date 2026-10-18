#!/usr/bin/env python3
import ast

try:
    with open('C:\\Users\\liam\\Documents\\GitHub\\all-of-my-code\\sportsanalysis\\premier-league\\26-27-season.py', 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    print('Syntax check passed')
    
    # Check if the key functions exist
    simulate_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name == 'simulate':
                # Check if this simulate method is inside EuropeanCompetition class
                parent = node
                while parent and not isinstance(parent, ast.ClassDef):
                    parent = getattr(parent, 'parent', None)
                if parent and parent.name == 'EuropeanCompetition':
                    simulate_found = True
                    print(f'  Found simulate method: {node.name}')
                    break
    
    if simulate_found:
        print('All syntax checks completed successfully')
    else:
        print('ERROR: simulate method not found in EuropeanCompetition class')
        exit(1)
    
except SyntaxError as e:
    print(f'Syntax error: {e}')
    print(f'  Line {e.lineno}: {e.text}')
    print(f'  Error: {e.msg}')
    exit(1)
