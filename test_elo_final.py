import sys
sys.path.insert(0, r'C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\premier-league')
import importlib.util
spec = importlib.util.spec_from_file_location(' TwentySixTwentySeven', r'C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\premier-league\26-27-season.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

from twenty_six_twenty_seven_season import PLSimulator, build_current_pl_ratings, FIXTURES_LIST
import logging
logging.basicConfig(level=logging.ERROR)

# Test basic setup
actual_results = {
    ('Arsenal', 'Everton'): (2, 2),
    ('Chelsea', 'Liverpool'): (1, 0),
}

pl_teams = {'Arsenal', 'Chelsea', 'Everton', 'Liverpool'}
current_ratings = build_current_pl_ratings(actual_results, pl_teams)

sim = PLSimulator(FIXTURES_LIST[:5], current_ratings, actual_results)
print('PLSimulator created successfully')
print(f'ratings_arr type: {type(sim.ratings_arr)}')
print(f'ratings_work type: {type(sim.ratings_work)}')
print(f'Actual mask any: {sim._has_actual}')

# Test simulate_season
fatigue_info = {}
ranked, points, results = sim.simulate_season(fatigue_info)
print('simulate_season completed successfully')
print(f'Ranked teams: {ranked[:5]}')
print(f'Points dict sample: {points}')
print(f'Results sample: {list(results.items())[:3]}')
print(f'ratings_work after sim: {sim.ratings_work["Arsenal"]:.1f}')
print(f'ratings_arr after sim: {sim.ratings_arr["Arsenal"]:.1f}')
print('SUCCESS: Elo updates working correctly - ratings changed:', sim.ratings_work['Arsenal'] != sim.ratings_arr['Arsenal'])