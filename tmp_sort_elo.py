import ast

with open('sportsanalysis/worldcupwomens/main.py', 'r') as f:
    content = f.read()

s = content.find('ELO = {')
e = content.find('\n}\n\n', s) + 1
elo_str = content[s + 7:e].lstrip()
print("EXTRACTED:")
print(repr(elo_str[:200]))
print("---")
elo_dict = ast.literal_eval('{' + elo_str + '}')

sorted_elo = dict(sorted(elo_dict.items(), key=lambda x: x[1], reverse=True))

lines = ['ELO = {']
items = list(sorted_elo.items())
for i, (k, v) in enumerate(items):
    comma = ',' if i < len(items) - 1 else ''
    lines.append(f'    "{k}": {v}{comma}')
lines.append('}')

new_elo = '\n'.join(lines)
print(new_elo)
