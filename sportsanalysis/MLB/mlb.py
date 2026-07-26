import csv
import math
import random
import os
from tqdm import tqdm
from collections import Counter, defaultdict

PYTHAGOREAN_EXPONENT = 1.83  # Bill James Pythagorean expectation exponent for MLB
HOME_ADVANTAGE_ELO = 24.0  # Standard MLB home-field advantage (equivalent to ~53.5% home win rate)
NUM_SIMULATIONS = 1000
K_FACTOR = 25  # MLB-standard Elo K-factor for regular season games

# Current 2026 Regular Season Records (as of Jul 22, 2026)
RAW_STANDINGS = {
    # AL East
    'Tampa Bay Rays': {'w': 58, 'l': 42, 'div': 'AL East', 'league': 'AL', 'rs': 454, 'ra': 424},
    'New York Yankees': {'w': 56, 'l': 44, 'div': 'AL East', 'league': 'AL', 'rs': 475, 'ra': 387},
    'Boston Red Sox': {'w': 51, 'l': 48, 'div': 'AL East', 'league': 'AL', 'rs': 419, 'ra': 373},
    'Baltimore Orioles': {'w': 49, 'l': 52, 'div': 'AL East', 'league': 'AL', 'rs': 464, 'ra': 478},
    'Toronto Blue Jays': {'w': 46, 'l': 55, 'div': 'AL East', 'league': 'AL', 'rs': 400, 'ra': 461},

    # AL Central
    'Chicago White Sox': {'w': 53, 'l': 47, 'div': 'AL Central', 'league': 'AL', 'rs': 479, 'ra': 437},
    'Cleveland Guardians': {'w': 54, 'l': 48, 'div': 'AL Central', 'league': 'AL', 'rs': 410, 'ra': 410},
    'Minnesota Twins': {'w': 49, 'l': 53, 'div': 'AL Central', 'league': 'AL', 'rs': 485, 'ra': 521},
    'Detroit Tigers': {'w': 47, 'l': 54, 'div': 'AL Central', 'league': 'AL', 'rs': 428, 'ra': 404},
    'Kansas City Royals': {'w': 42, 'l': 60, 'div': 'AL Central', 'league': 'AL', 'rs': 433, 'ra': 530},

    # AL West
    'Texas Rangers': {'w': 51, 'l': 50, 'div': 'AL West', 'league': 'AL', 'rs': 425, 'ra': 453},
    'Seattle Mariners': {'w': 51, 'l': 51, 'div': 'AL West', 'league': 'AL', 'rs': 412, 'ra': 393},
    'Houston Astros': {'w': 49, 'l': 54, 'div': 'AL West', 'league': 'AL', 'rs': 468, 'ra': 516},
    'Athletics': {'w': 43, 'l': 58, 'div': 'AL West', 'league': 'AL', 'rs': 453, 'ra': 565},
    'Los Angeles Angels': {'w': 41, 'l': 61, 'div': 'AL West', 'league': 'AL', 'rs': 442, 'ra': 499},

    # NL East
    'Atlanta Braves': {'w': 58, 'l': 42, 'div': 'NL East', 'league': 'NL', 'rs': 495, 'ra': 391},
    'Philadelphia Phillies': {'w': 56, 'l': 46, 'div': 'NL East', 'league': 'NL', 'rs': 443, 'ra': 454},
    'Miami Marlins': {'w': 52, 'l': 50, 'div': 'NL East', 'league': 'NL', 'rs': 455, 'ra': 441},
    'Washington Nationals': {'w': 51, 'l': 51, 'div': 'NL East', 'league': 'NL', 'rs': 559, 'ra': 541},
    'New York Mets': {'w': 43, 'l': 59, 'div': 'NL East', 'league': 'NL', 'rs': 416, 'ra': 479},

    # NL Central
    'Milwaukee Brewers': {'w': 63, 'l': 38, 'div': 'NL Central', 'league': 'NL', 'rs': 510, 'ra': 378},
    'Chicago Cubs': {'w': 57, 'l': 44, 'div': 'NL Central', 'league': 'NL', 'rs': 519, 'ra': 450},
    'Pittsburgh Pirates': {'w': 52, 'l': 49, 'div': 'NL Central', 'league': 'NL', 'rs': 538, 'ra': 487},
    'St. Louis Cardinals': {'w': 51, 'l': 49, 'div': 'NL Central', 'league': 'NL', 'rs': 447, 'ra': 448},
    'Cincinnati Reds': {'w': 46, 'l': 54, 'div': 'NL Central', 'league': 'NL', 'rs': 418, 'ra': 483},

    # NL West
    'Los Angeles Dodgers': {'w': 64, 'l': 38, 'div': 'NL West', 'league': 'NL', 'rs': 526, 'ra': 373},
    'Arizona Diamondbacks': {'w': 52, 'l': 49, 'div': 'NL West', 'league': 'NL', 'rs': 441, 'ra': 454},
    'San Diego Padres': {'w': 50, 'l': 51, 'div': 'NL West', 'league': 'NL', 'rs': 415, 'ra': 443},
    'San Francisco Giants': {'w': 42, 'l': 59, 'div': 'NL West', 'league': 'NL', 'rs': 413, 'ra': 476},
    'Colorado Rockies': {'w': 41, 'l': 62, 'div': 'NL West', 'league': 'NL', 'rs': 495, 'ra': 588},
}


def calculate_realistic_elo(wins: int, losses: int, runs_scored: int = None, runs_allowed: int = None) -> int:
    if runs_scored is not None and runs_allowed is not None and runs_scored > 0 and runs_allowed > 0:
        win_pct = 1.0 / (1.0 + (runs_allowed / runs_scored) ** PYTHAGOREAN_EXPONENT)
        return round(1500 + 400 * math.log10(win_pct / (1.0 - win_pct)))
    if wins <= 0 or losses <= 0:
        return 1500
    return round(1500 + 400 * math.log10(wins / losses))


# Dynamically generate CURRENT_STANDINGS with realistic Elo ratings
CURRENT_STANDINGS = {}
for team, data in RAW_STANDINGS.items():
    calculated_elo = calculate_realistic_elo(data['w'], data['l'], data.get('rs'), data.get('ra'))
    CURRENT_STANDINGS[team] = {
        'w': data['w'],
        'l': data['l'],
        'div': data['div'],
        'league': data['league'],
        'elo': calculated_elo
    }


def win_prob(rating1, rating2):
    diff = rating1 - rating2
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def update_elo(winner_rating: float, loser_rating: float) -> tuple[float, float]:
    expected_winner = win_prob(winner_rating, loser_rating)
    expected_loser = 1.0 - expected_winner
    new_winner = winner_rating + K_FACTOR * (1.0 - expected_winner)
    new_loser = loser_rating + K_FACTOR * (0.0 - expected_loser)
    return round(new_winner), round(new_loser)


def sim_series(home_team, away_team, best_of, elo_ratings):
    wins_needed = (best_of // 2) + 1
    home_wins, away_wins = 0, 0

    if best_of == 7:
        game_locations = [True, True, False, False, True, False, True]
    elif best_of == 5:
        game_locations = [True, True, False, False, True]
    elif best_of == 3:
        game_locations = [True, False, True]
    else:
        game_locations = [True] * best_of

    for game_idx in range(best_of):
        is_home = game_locations[game_idx]
        if is_home:
            elo_home = elo_ratings[home_team] + HOME_ADVANTAGE_ELO
            elo_away = elo_ratings[away_team]
        else:
            elo_home = elo_ratings[away_team] + HOME_ADVANTAGE_ELO
            elo_away = elo_ratings[home_team]

        p_home_win = win_prob(elo_home, elo_away)

        if random.random() < p_home_win:
            if is_home:
                home_wins += 1
            else:
                away_wins += 1
        else:
            if is_home:
                away_wins += 1
            else:
                home_wins += 1

        if home_wins == wins_needed or away_wins == wins_needed:
            break

    return home_team if home_wins == wins_needed else away_team


def load_schedule(filepath):
    games = []
    if not os.path.exists(filepath):
        print(f"Warning: Schedule file '{filepath}' not found.")
        return games

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            away = row.get('away_team') or row.get('away_name') or row.get('away') or row.get('Away_Team')
            home = row.get('home_team') or row.get('home_name') or row.get('home') or row.get('Home_Team')
            
            if away == 'Oakland Athletics': away = 'Athletics'
            if home == 'Oakland Athletics': home = 'Athletics'

            if home and away:
                games.append({'away': away, 'home': home})
    return games


def run_monte_carlo(schedule, num_sims=NUM_SIMULATIONS):
    make_playoffs = Counter()
    league_champions = Counter()
    world_series_champions = Counter()
    total_projected_wins = defaultdict(float)

    divisions = defaultdict(list)
    leagues = defaultdict(list)
    for team, data in CURRENT_STANDINGS.items():
        divisions[data['div']].append(team)
        leagues[data['league']].append(team)

    base_elo = {team: data['elo'] for team, data in CURRENT_STANDINGS.items()}

    print(f"\nSimulating {num_sims:,} seasons & complete playoff brackets...")

    for i in tqdm(range(num_sims), desc='Simulating', unit='sim'):
        sim_elo = base_elo.copy()
        sim_wins = {team: data['w'] for team, data in CURRENT_STANDINGS.items()}

        for game in schedule:
            home = game['home']
            away = game['away']
            h_elo = sim_elo[home] + HOME_ADVANTAGE_ELO
            a_elo = sim_elo[away]
            p_home_win = win_prob(h_elo, a_elo)

            if random.random() < p_home_win:
                sim_wins[home] += 1
                winner, loser = home, away
            else:
                sim_wins[away] += 1
                winner, loser = away, home

            sim_elo[winner], sim_elo[loser] = update_elo(sim_elo[winner], sim_elo[loser])

        for team, w in sim_wins.items():
            total_projected_wins[team] += w

        # --- PLAYOFF SEEDING & TOURNAMENT ---
        lg_pennant_winners = []

        for lg_name in ['AL', 'NL']:
            div_winners = []
            non_div_teams = []

            for div_name in [d for d in divisions if d.startswith(lg_name)]:
                div_teams = divisions[div_name]
                winner = max(div_teams, key=lambda t: (sim_wins[t], random.random()))
                div_winners.append(winner)
                make_playoffs[winner] += 1

                for t in div_teams:
                    if t != winner:
                        non_div_teams.append(t)

            div_winners.sort(key=lambda t: (sim_wins[t], random.random()), reverse=True)
            seed1, seed2, seed3 = div_winners[0], div_winners[1], div_winners[2]

            non_div_teams.sort(key=lambda t: (sim_wins[t], random.random()), reverse=True)
            seed4, seed5, seed6 = non_div_teams[0], non_div_teams[1], non_div_teams[2]

            make_playoffs[seed4] += 1
            make_playoffs[seed5] += 1
            make_playoffs[seed6] += 1

            wc1_winner = sim_series(seed3, seed6, best_of=3, elo_ratings=sim_elo)
            wc2_winner = sim_series(seed4, seed5, best_of=3, elo_ratings=sim_elo)

            ds1_winner = sim_series(seed1, wc2_winner, best_of=5, elo_ratings=sim_elo)
            ds2_winner = sim_series(seed2, wc1_winner, best_of=5, elo_ratings=sim_elo)

            if sim_wins[ds1_winner] >= sim_wins[ds2_winner]:
                league_champ = sim_series(ds1_winner, ds2_winner, best_of=7, elo_ratings=sim_elo)
            else:
                league_champ = sim_series(ds2_winner, ds1_winner, best_of=7, elo_ratings=sim_elo)

            league_champions[league_champ] += 1
            lg_pennant_winners.append(league_champ)

        # World Series
        al_champ, nl_champ = lg_pennant_winners[0], lg_pennant_winners[1]
        if sim_wins[al_champ] >= sim_wins[nl_champ]:
            world_champ = sim_series(al_champ, nl_champ, best_of=7, elo_ratings=sim_elo)
        else:
            world_champ = sim_series(nl_champ, al_champ, best_of=7, elo_ratings=sim_elo)

        world_series_champions[world_champ] += 1

    return total_projected_wins, make_playoffs, league_champions, world_series_champions, num_sims


if __name__ == "__main__":
    csv_filename = "mlb_remaining_schedule_2026.csv"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, csv_filename) if not os.path.isabs(csv_filename) else csv_filename

    schedule = load_schedule(csv_path)

    proj_wins, playoffs, pennants, world_series, sims = run_monte_carlo(schedule, NUM_SIMULATIONS)

    # Sort all 30 teams by World Series % descending
    all_teams = list(CURRENT_STANDINGS.keys())
    all_teams.sort(key=lambda t: (world_series[t], pennants[t], playoffs[t]), reverse=True)

    print("\n" + "=" * 115)
    print(f"2026 MLB PROJECTIONS (REALISTIC RECORD ELO) - SORTED BY WORLD SERIES % ({sims:,} SIMS)")
    print("=" * 115)
    print(f"{'Rank':<5} | {'Team':<22} | {'Elo':<5} | {'Current':<8} | {'Proj W-L':<10} | {'Proj Win %':<11} | {'Make Playoffs %':<17} | {'Win League %':<14} | {'Win World Series %'}")
    print("-" * 115)

    for rank, team in enumerate(all_teams, start=1):
        elo = CURRENT_STANDINGS[team]['elo']
        curr_w = CURRENT_STANDINGS[team]['w']
        curr_l = CURRENT_STANDINGS[team]['l']
        avg_w = proj_wins[team] / sims
        avg_l = 162.0 - avg_w
        
        playoff_pct = (playoffs[team] / sims) * 100
        league_pct = (pennants[team] / sims) * 100
        ws_pct = (world_series[team] / sims) * 100

        print(f"{rank:<5} | {team:<22} | {elo:<5} | {curr_w:2d}-{curr_l:<5d} | {avg_w:4.2f}-{avg_l:<4.2f} | {avg_w/162.0 * 100:9.2f}% | {playoff_pct:13.2f}% | {league_pct:12.2f}% | {ws_pct:14.2f}%")