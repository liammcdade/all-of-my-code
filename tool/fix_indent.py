path = r'C:\Users\liam\Documents\GitHub\all-of-my-code\tool\video.py'
with open(path, 'r') as f:
    lines = f.readlines()
# Dedent lines 1678 onwards (0-indexed: 1677+) by 4 spaces
for i in range(1677, len(lines)):
    if lines[i].startswith('    '):
        lines[i] = lines[i][4:]
    elif lines[i].strip() == '':
        pass  # keep blank lines as-is
with open(path, 'w') as f:
    f.writelines(lines)
print('Dedented lines 1678-end by 4 spaces')
