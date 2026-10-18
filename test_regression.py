import importlib.util
spec = importlib.util.spec_from_file_location(
    "mod",
    "C:/Users/liam/Documents/GitHub/all-of-my-code/sportsanalysis/premier-league/26-27-season.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Run a quick simulation
r = mod.run_simulation(n_sims=3, seed=123)
print("Simulation completed!")
print(f"PL teams: {len(r['pl_teams_set'])}")
print(f"PL Elo sample: {dict(list(r['pl_elos'].items())[:3])}")
print(f"UCL winner: {r['ucl_winner']}")
print(f"UEL winner: {r['uel_winner']}")
print(f"UECL winner: {r['uecl_winner']}")
print(f"English three comp: {r['english_three_comp_prob']:.1f}%")