from ai import Agent, load_brains, DEFAULT_BRAINS
from tuning import load_tuners, TUNER_FILE
from engine import Engine, play_game

brains = load_brains(DEFAULT_BRAINS, 4)
tuners = load_tuners(TUNER_FILE, 4)
agents = [Agent(i, brains[i], tuners[i]) for i in range(4)]
eng = Engine(agents=agents, turn_limit=400, verbose=True)
play_game(eng)

winner = eng.winner
wname = eng.players[winner].name if winner is not None else "nobody"
print(f"Game over: winner = {wname}")
print(f"Turns: {eng.turn}")
for p in eng.players:
    print(f"  {p.name}: cash £{p.cash}, bankrupt={p.bankrupt}")
print(f"House stock: {eng.house_stock}, Hotel stock: {eng.hotel_stock}")
