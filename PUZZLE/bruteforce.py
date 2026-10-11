import itertools, re, string, collections, heapq, math

# ----------------------------------------------------------------------
# Word list
# ----------------------------------------------------------------------
def load_words():
    """Try to load a system word list, else use a small fallback."""
    for path in ['/usr/share/dict/words', '/usr/share/dict/american-english']:
        try:
            with open(path, encoding='utf-8', errors='ignore') as f:
                return set(w.strip().lower() for w in f if w.strip().isalpha())
        except Exception:
            pass
    # Fallback: a few thousand common words is usually enough for these puzzles.
    # In practice, use /usr/share/dict/words or `nltk.corpus.words`.
    fallback = """
    special secret message answer puzzle christmas challenge gchq
    acting suspiciously robber police house route door colour colored
    driftwood stream water river amazon hidden missing gift santa
    wrapped pairs letter word code cipher solve four letter words
    appropriate right place wrong present absent value digit number
    """.split()
    return set(w.lower() for w in fallback)

WORDS = load_words()

# ----------------------------------------------------------------------
# Puzzle 1 – special seven-letter word
# ----------------------------------------------------------------------
def puzzle1():
    print("Puzzle 1 – special seven-letter word")
    for w in WORDS:
        if len(w) != 7:
            continue
        if len(set(w)) != 7:
            continue
        # no pair of letters adjacent in the alphabet
        ok = True
        for i, a in enumerate(w):
            for b in w[i+1:]:
                if abs(ord(a) - ord(b)) == 1:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            print("  candidate:", w)
    # The intended answer is literally in the question: SPECIAL
    print("  intended answer: SPECIAL\n")

# ----------------------------------------------------------------------
# Puzzle 2 – robber’s route
# ----------------------------------------------------------------------
def puzzle2():
    print("Puzzle 2 – robber’s route")
    # Nodes are rooms.  Edges are (neighbour, colour, arrow_direction).
    # arrow_direction: 'both', '->', '<-'
    # You must update this from the image.  Example graph:
    graph = {
        'E': [('G','blue','both'), ('I','red','both')],
        'G': [('E','blue','both'), ('T','blue','both'), ('I','red','both')],
        'T': [('G','blue','both'), ('H','blue','both'), ('N','red','both')],
        'H': [('T','blue','both'), ('N','blue','both')],
        'I': [('E','red','both'), ('G','red','both'), ('N','blue','both'), ('R','red','both')],
        'N': [('T','red','both'), ('H','blue','both'), ('I','blue','both'), ('B','red','both'), ('K','blue','both')],
        'R': [('I','red','both'), ('A','red','both'), ('D','red','both')],
        'A': [('R','red','both'), ('B','blue','both'), ('F','red','both')],
        'B': [('A','blue','both'), ('N','red','both'), ('K','blue','both'), ('Q','blue','both')],
        'K': [('B','blue','both'), ('N','blue','both'), ('C','blue','both')],
        'D': [('R','red','both'), ('F','red','both')],
        'F': [('A','red','both'), ('D','red','both'), ('Q','blue','both')],
        'Q': [('B','blue','both'), ('F','blue','both'), ('C','blue','both')],
        'C': [('K','blue','both'), ('Q','blue','both')],
    }
    start, goal = 'R', 'N'   # robber starts near R, police near N
    # BFS state: (room, last_door_colour)
    q = collections.deque([(start, None, [start])])
    seen = set()
    while q:
        room, last_colour, path = q.popleft()
        if room == goal:
            print("  path:", ' -> '.join(path))
            return
        for nxt, colour, arrow in graph.get(room, []):
            if last_colour == colour:
                continue
            if arrow == '->' and nxt == room:
                continue
            if arrow == '<-' and room == nxt:
                continue
            key = (nxt, colour)
            if key in seen:
                continue
            seen.add(key)
            q.append((nxt, colour, path + [nxt]))
    print("  graph needs updating from the PDF image.\n")

# ----------------------------------------------------------------------
# Puzzle 3 – driftwood in streams
# ----------------------------------------------------------------------
def puzzle3():
    print("Puzzle 3 – driftwood in streams")
    # Letters copied from the two streams.  The exact order can be adjusted.
    left = "AZSNIMAONEE LGAGNESEM"
    right = "IENHHDNTUERE NAIABUE"
    streams = [left, right]
    for s in streams:
        s = re.sub(r'\s+', '', s).lower()
        for i in range(len(s)):
            for j in range(i+3, len(s)+1):
                w = s[i:j]
                if w in WORDS:
                    print("  found:", w)
    print("  (update letter strings from the image if needed.)\n")

# ----------------------------------------------------------------------
# Puzzle 4 – gifts wrapped in pairs
# ----------------------------------------------------------------------
def puzzle4():
    print("Puzzle 4 – gifts wrapped in pairs")
    # Grid of pairs, each cell has top-left and bottom-right letters
    grid = [
        [('L','S'),('I','W'),('E','P'),('A','P'),('E','T'),('E','R'),('R','S')],
        [('C','C'),('M','O'),('N','P'),('S','U'),('O','T'),('E','L'),('E','R')],
        [('N','P'),('E','E'),('K','N'),('D','L'),('A','A'),('C','N'),('E','T')],
        [('C','J'),('O','O'),('O','U'),('B','R'),('N','O'),('A','O'),('K','L')],
        [('H','S'),('A','H'),('A','N'),('D','M'),('O','P'),('A','O'),('O','P')],
    ]
    # Read two ways: top-lefts and bottom-rights
    top = ''.join(cell[0] for row in grid for cell in row)
    bot = ''.join(cell[1] for row in grid for cell in row)
    print("  top-lefts:", top)
    print("  bottom-rights:", bot)
    # The missing pair is often found by XOR / set difference.
    # This is deliberately left for visual inspection.
    print("  inspect the two strings and the card for the missing pair.\n")

# ----------------------------------------------------------------------
# Puzzle 5 – alphametic
# ----------------------------------------------------------------------
def puzzle5():
    print("Puzzle 5 – alphametic")
    letters = "TWOUVPAIRS"   # T W O U V P A I R S
    assert len(set(letters)) == 10
    for perm in itertools.permutations('0123456789', 10):
        d = dict(zip(letters, perm))
        if d['U'] == '0' or d['V'] == '0' or d['S'] == '0' or d['R'] == '0':
            continue
        UV = int(d['U'] + d['V'])
        VAR = int(d['V'] + d['A'] + d['R'])
        if 2 * UV + int(d['V']) != VAR:
            continue
        R, P, A, I = int(d['R']), int(d['P']), int(d['A']), int(d['I'])
        if R * P * P != int(d['A'] + d['I'] + d['R']):
            continue
        SO = int(d['S'] + d['O'])
        VOW = int(d['V'] + d['O'] + d['W'])
        if 2 * SO != VOW:
            continue
        print("  solution:", d)
        # "What is 1234567?" – map digits back to letters
        inv = {v:k for k,v in d.items()}
        print("  1234567 ->", ''.join(inv.get(ch, '?') for ch in '1234567'))
        return
    print("  no solution found – check equations.\n")

# ----------------------------------------------------------------------
# Puzzle 6 – substitution cipher
# ----------------------------------------------------------------------
def word_pattern(w):
    d, out, n = {}, [], 0
    for ch in w:
        if ch not in d:
            d[ch] = str(n); n += 1
        out.append(d[ch])
    return ''.join(out)

def puzzle6():
    print("Puzzle 6 – substitution cipher")
    cipher = """
PIGMHM DRP MHSIAMA QDMPM MBNDQ UTTL- FMQQML NBLFP HRGMP: LTOY, ILFR, PRLR, ROOY, GRYR, TPDR, HILL, ARHB. PDM FMUQ R SFTM QI DML IWH HRGM OTQ SRH YIT WILE BQ ITQ?
""".strip().upper().split()
    # Build pattern dictionary
    pat2words = collections.defaultdict(list)
    for w in WORDS:
        if len(w) >= 2:
            pat2words[word_pattern(w.upper())].append(w.upper())
    # Backtracking substitution solver
    mapping = {}
    used_plain = set()
    def solve(idx):
        if idx == len(cipher):
            return True
        cw = cipher[idx]
        pat = word_pattern(cw)
        for pw in pat2words.get(pat, []):
            if len(pw) != len(cw):
                continue
            new_map = {}
            ok = True
            for c, p in zip(cw, pw):
                if c in mapping and mapping[c] != p:
                    ok = False; break
                if p in used_plain and mapping.get(c) != p:
                    ok = False; break
                new_map[c] = p
            if not ok:
                continue
            # apply tentatively
            added_c, added_p = [], []
            for c, p in new_map.items():
                if c not in mapping:
                    mapping[c] = p; used_plain.add(p); added_c.append(c); added_p.append(p)
            if solve(idx+1):
                return True
            # backtrack
            for c in added_c:
                del mapping[c]
            for p in added_p:
                used_plain.discard(p)
        return False
    if solve(0):
        print("  plaintext:", ' '.join(mapping.get(c, '?') for w in cipher for c in w))
    else:
        print("  need a larger word list.\n")

# ----------------------------------------------------------------------
# Puzzle 7 – Wordle-like
# ----------------------------------------------------------------------
def puzzle7():
    print("Puzzle 7 – Wordle-like 7-letter word")
    # Each row: (flag, guess, feedback)
    # feedback: '✓' = right place, '?' = present wrong place, ' ' = absent
    # You must transcribe the flags/feedback from the image.
    rows = [
        # ('🇩🇰', '???????', '  ?  ✓ '),
        # ('🇩🇪', '???????', '  ?  ?✓'),
        # ('🇫🇷', '???????', '  ???  '),
        # ('🇱🇹', '???????', ' ??  ✓✓'),
        # ('🇭🇷', '???????', '✓?? ✓  '),
    ]
    candidates = [w for w in WORDS if len(w) == 7]
    for flag, guess, fb in rows:
        guess = guess.upper()
        new = []
        for w in candidates:
            ok = True
            for i, ch in enumerate(guess):
                if fb[i] == '✓' and w[i] != ch:
                    ok = False; break
                if fb[i] == '?' and (ch not in w or w[i] == ch):
                    ok = False; break
                if fb[i] == ' ' and ch in w:
                    ok = False; break
            if ok:
                new.append(w)
        candidates = new
    print("  candidates:", candidates)
    print("  (update rows from the PDF image for an exact answer.)\n")

# ----------------------------------------------------------------------
if __name__ == "__main__":
    puzzle1()
    puzzle2()
    puzzle3()
    puzzle4()
    puzzle5()
    puzzle6()
    puzzle7()