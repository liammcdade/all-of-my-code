import pandas as pd
import numpy as np
import random
from tqdm import tqdm

# ------------------------- 
# CONFIG / GROUPS
# -------------------------
GROUPS = {
    'A': {
        'teams': ['Morocco', 'Mali', 'Zambia', 'Comoros'],
        'matches': [
            ('Mali', 'Zambia'),
            ('Zambia', 'Comoros'),
            ('Morocco', 'Mali'),
            ('Zambia', 'Morocco'),
            ('Comoros', 'Mali')
        ]
    },
    'B': {
        'teams': ['Egypt', 'South Africa', 'Angola', 'Zimbabwe'],
        'matches': [
            ('Egypt', 'Zimbabwe'),
            ('South Africa', 'Angola'),
            ('Egypt', 'South Africa'),
            ('Angola', 'Zimbabwe'),
            ('Angola', 'Egypt'),
            ('Zimbabwe', 'South Africa')
        ]
    },
    'C': {
        'teams': ['Nigeria', 'Tunisia', 'Uganda', 'Tanzania'],
        'matches': [
            ('Nigeria', 'Tanzania'),
            ('Tunisia', 'Uganda'),
            ('Nigeria', 'Tunisia'),
            ('Uganda', 'Tanzania'),
            ('Uganda', 'Nigeria'),
            ('Tanzania', 'Tunisia')
        ]
    },
    'D': {
        'teams': ['Senegal', 'DR Congo', 'Benin', 'Botswana'],
        'matches': [
            ('Senegal', 'Botswana'),
            ('DR Congo', 'Benin'),
            ('Senegal', 'DR Congo'),
            ('Benin', 'Botswana'),
            ('Benin', 'Senegal'),
            ('Botswana', 'DR Congo')
        ]
    },
    'E': {
        'teams': ['Algeria', 'Burkina Faso', 'Equatorial Guinea', 'Sudan'],
        'matches': [
            ('Algeria', 'Sudan'),
            ('Burkina Faso', 'Equatorial Guinea'),
            ('Algeria', 'Burkina Faso'),
            ('Equatorial Guinea', 'Sudan'),
            ('Equatorial Guinea', 'Algeria'),
            ('Sudan', 'Burkina Faso')
        ]
    },
    'F': {
        'teams': ['Ivory Coast', 'Cameroon', 'Gabon', 'Mozambique'],
        'matches': [
            ('Ivory Coast', 'Mozambique'),
            ('Cameroon', 'Gabon'),
            ('Ivory Coast', 'Cameroon'),
            ('Gabon', 'Mozambique')
            # Note: Gabon vs Ivory Coast and Mozambique vs Cameroon not played due to tournament suspension
        ]
    }
}

# Played matches and their point results (3 for win, 1 for draw, 0 for loss)
played_matches = {
    'A': [
        ('Morocco', 'Comoros'), ('Mali', 'Zambia'), ('Zambia', 'Comoros'),
        ('Morocco', 'Mali'), ('Zambia', 'Morocco'), ('Comoros', 'Mali')
    ],
    'B': [
        ('South Africa', 'Angola'), ('Egypt', 'Zimbabwe'), ('Angola', 'Zimbabwe'),
        ('Egypt', 'South Africa'), ('Angola', 'Egypt'), ('Zimbabwe', 'South Africa')
    ],
    'C': [
        ('Nigeria', 'Tanzania'), ('Tunisia', 'Uganda'), ('Uganda', 'Tanzania'),
        ('Nigeria', 'Tunisia'), ('Uganda', 'Nigeria'), ('Tanzania', 'Tunisia')
    ],
    'D': [
        ('DR Congo', 'Benin'), ('Senegal', 'Botswana'), ('Benin', 'Botswana'),
        ('Senegal', 'DR Congo'), ('Benin', 'Senegal'), ('Botswana', 'DR Congo')
    ],
    'E': [
        ('Burkina Faso', 'Equatorial Guinea'), ('Algeria', 'Sudan'),
        ('Equatorial Guinea', 'Sudan'), ('Algeria', 'Burkina Faso'),
        ('Equatorial Guinea', 'Algeria'), ('Sudan', 'Burkina Faso')
    ],
    'F': [
        ('Ivory Coast', 'Mozambique'), ('Cameroon', 'Gabon'),
        ('Gabon', 'Mozambique'), ('Ivory Coast', 'Cameroon')
    ]
}

played_results = {
    # Group A
    ('Morocco', 'Comoros'): (2, 0),
    ('Mali', 'Zambia'): (1, 1),
    ('Zambia', 'Comoros'): (0, 0),
    ('Morocco', 'Mali'): (1, 1),
    ('Zambia', 'Morocco'): (0, 3),
    ('Comoros', 'Mali'): (0, 0),
    # Group B
    ('South Africa', 'Angola'): (2, 1),
    ('Egypt', 'Zimbabwe'): (2, 1),
    ('Angola', 'Zimbabwe'): (1, 1),
    ('Egypt', 'South Africa'): (1, 0),
    ('Angola', 'Egypt'): (0, 0),
    ('Zimbabwe', 'South Africa'): (2, 3),
    # Group C
    ('Nigeria', 'Tanzania'): (2, 1),
    ('Tunisia', 'Uganda'): (3, 1),
    ('Uganda', 'Tanzania'): (1, 1),
    ('Nigeria', 'Tunisia'): (3, 2),
    ('Uganda', 'Nigeria'): (1, 3),
    ('Tanzania', 'Tunisia'): (1, 1),
    # Group D
    ('DR Congo', 'Benin'): (1, 0),
    ('Senegal', 'Botswana'): (3, 0),
    ('Benin', 'Botswana'): (1, 0),
    ('Senegal', 'DR Congo'): (1, 1),
    ('Benin', 'Senegal'): (0, 3),
    ('Botswana', 'DR Congo'): (0, 3),
    # Group E
    ('Burkina Faso', 'Equatorial Guinea'): (2, 1),
    ('Algeria', 'Sudan'): (3, 0),
    ('Equatorial Guinea', 'Sudan'): (0, 1),
    ('Algeria', 'Burkina Faso'): (1, 0),
    ('Equatorial Guinea', 'Algeria'): (1, 3),
    ('Sudan', 'Burkina Faso'): (0, 2),
    # Group F
    ('Ivory Coast', 'Mozambique'): (1, 0),
    ('Cameroon', 'Gabon'): (1, 0),
    ('Gabon', 'Mozambique'): (2, 3),
    ('Ivory Coast', 'Cameroon'): (1, 1)
}

# -------------------------
# KNOCKOUT STAGE RESULTS
# -------------------------
# To add actual knockout match results, replace None with (score1, score2)
# Example: 'R1': (2, 1) means first team won 2-1
# The simulation will use actual results when available, otherwise simulate matches
#
# Round of 16 results: (team1, team2): (score1, score2)
# Use None for matches not yet played
knockout_results_played = {
    # Round of 16 (R1-R8) - Actual results from Round of 16
    'R1': (3, 1),  # Senegal 3-1 Sudan
    'R2': (1, 1, 'Mali'),  # Mali 1-1 Tunisia (Mali won on penalties)
    'R3': (1, 0),  # Morocco 1-0 Tanzania
    'R4': (1, 2),  # South Africa 1-2 Cameroon
    'R5': (3, 1),  # Egypt 3-1 Benin (a.e.t.)
    'R6': (4, 0),  # Nigeria 4-0 Mozambique
    'R7': (1, 0),  # Algeria vs DR Congo (06/01/26)
    'R8': (1, 0),  # Côte d'Ivoire vs Burkina Faso (06/01/26)

    # Quarter-finals (QF1-QF4)
    'QF1': (0, 1),  # Mali 0-1 Senegal
    'QF2': (0, 2),  # Cameroon 0-2 Morocco
    'QF3': (0, 2),  # Algeria 0-2 Nigeria
    'QF4': (3, 2),  # Egypt 3-2 Côte d'Ivoire

    # Semi-finals (SF1-SF2)
    'SF1': None,  # Winner QF1 vs Winner QF4 (Senegal vs Egypt)
    'SF2': None,  # Winner QF3 vs Winner QF2 (Morocco vs Nigeria)

    # Final
    'FINAL': None,  # Winner SF1 vs Winner SF2

    # Third place
    'THIRD': None   # Loser SF1 vs Loser SF2
}

# -------------------------
# TEAM RATINGS (Elo-like)
# -------------------------
teams_ratings = {
    'Morocco': 1830,
    'Comoros': 1387,
    'Egypt': 1631,
    'Tunisia': 1612,
    'Algeria': 1736,
    'Sudan': 1395,
    'Mali': 1612,
    'Zambia': 1364,
    'South Africa': 1530,
    'Angola': 1566,
    'Zimbabwe': 1352,
    'Nigeria': 1627,
    'Uganda': 1433,
    'Tanzania': 1325,
    'Senegal': 1803,
    'DR Congo': 1616,
    'Benin': 1436,
    'Botswana': 1319,
    'Burkina Faso': 1547,
    'Equatorial Guinea': 1438,
    'Ivory Coast': 1607,
    'Cameroon': 1559,
    'Gabon': 1467,
    'Mozambique': 1389
}

# -------------------------
# FAIR PLAY POINTS (lower is better)
# -------------------------
# Calculated as: -1 per yellow card, -3 per red card
# Only includes cards from group stage matches played so far
fair_play_points = {
    'Ivory Coast': -3,
    'Cameroon': -4,
    # Other teams: assume 0 for now (no cards recorded)
}

# ------------------------- 
# Helper functions
# -------------------------
def get_rating(team):
    return teams_ratings.get(team, 1500.0)

def get_fair_play_points(team):
    return fair_play_points.get(team, 0)  # Lower (more negative) is better

def get_win_probability(points_a, points_b):
    dr = points_a - points_b
    expected_result = 1 / (10**(-(dr) / 552) + 1)
    return expected_result

def simulate_score(team_a, team_b, allow_draw=True):
    rating_a = get_rating(team_a)
    rating_b = get_rating(team_b)
    base_eg = 1.5
    dr = rating_a - rating_b
    eg_a = base_eg * (1 + dr / 552)
    eg_b = base_eg * (1 - dr / 552)
    goals_a = np.random.poisson(eg_a)
    goals_b = np.random.poisson(eg_b)
    if not allow_draw and goals_a == goals_b:
        while goals_a == goals_b:
            goals_a += np.random.poisson(0.5)
            goals_b += np.random.poisson(0.5)
    return goals_a, goals_b

def simulate_knockout_match(team_a, team_b):
    goals_a, goals_b = simulate_score(team_a, team_b, allow_draw=False)
    if goals_a != goals_b:
        return team_a if goals_a > goals_b else team_b
    # Extra time
    extra_a = np.random.poisson(0.5)
    extra_b = np.random.poisson(0.5)
    goals_a += extra_a
    goals_b += extra_b
    if goals_a != goals_b:
        return team_a if goals_a > goals_b else team_b
    # Pens
    prob_a = get_win_probability(get_rating(team_a), get_rating(team_b))
    pens_prob_a = 0.5 + (prob_a - 0.5) * 0.5
    return team_a if random.random() < pens_prob_a else team_b

def get_knockout_match_result(match_key, team_a, team_b):
    """
    Returns the winner of a knockout match.
    Uses actual result if available, otherwise simulates the match.
    """
    result = knockout_results_played.get(match_key)
    if result is not None:
        # Use actual result
        if len(result) == 3:
            # Special case: (score_a, score_b, winner_team) for penalty shootouts
            score_a, score_b, winner = result
            return winner
        else:
            score_a, score_b = result
            if score_a > score_b:
                return team_a
            elif score_b > score_a:
                return team_b
            else:
                # Shouldn't happen in knockout, but fallback to simulation
                return simulate_knockout_match(team_a, team_b)
    else:
        # Simulate the match
        return simulate_knockout_match(team_a, team_b)

def get_h2h_stats(team, tied_teams, match_results):
    points = 0
    gf = 0
    ga = 0
    for other in tied_teams:
        if other == team: continue
        match_key = (team, other) if (team, other) in match_results else (other, team)
        if match_key in match_results:
            if match_key[0] == team:
                g_team, g_other = match_results[match_key]
            else:
                g_other, g_team = match_results[match_key]
            gf += g_team
            ga += g_other
            if g_team > g_other:
                points += 3
            elif g_team == g_other:
                points += 1
    gd = gf - ga
    return points, gd, gf

# ------------------------- 
# MAIN SIMULATION
# -------------------------
NUM_SIMULATIONS = 10000
results = {}
for group_key, group in GROUPS.items():
    results[group_key] = {team: {'Group_Winner': 0, 'Advance': 0, 'Advance_as_3rd': 0, 'total_points': 0, 'total_gd': 0, 'total_gf': 0, 'total_ga': 0, 'position_1': 0, 'position_2': 0, 'position_3': 0, 'position_4': 0} for team in group['teams']}

all_teams = [t for group in GROUPS.values() for t in group['teams']]
knockout_results = {team: {'Round of 16': 0, 'Quarterfinals': 0, 'Semifinals': 0, 'Final': 0, 'Winner': 0, 'Third': 0} for team in all_teams}

for _ in tqdm(range(NUM_SIMULATIONS)):
    group_standings = {}
    for group_key, group in GROUPS.items():
        teams = group['teams']
        group_stats = {team: {'points': 0, 'gf': 0, 'ga': 0} for team in teams}
        match_results = {}
        played = played_matches.get(group_key, [])
        for match in played:
            goals_a, goals_b = played_results[match]
            match_results[match] = (goals_a, goals_b)
            points_a = 3 if goals_a > goals_b else 1 if goals_a == goals_b else 0
            points_b = 3 if goals_b > goals_a else 1 if goals_a == goals_b else 0
            group_stats[match[0]]['points'] += points_a
            group_stats[match[0]]['gf'] += goals_a
            group_stats[match[0]]['ga'] += goals_b
            group_stats[match[1]]['points'] += points_b
            group_stats[match[1]]['gf'] += goals_b
            group_stats[match[1]]['ga'] += goals_a
        remaining_matches = [m for m in group['matches'] if m not in played]
        for team_a, team_b in remaining_matches:
            goals_a, goals_b = simulate_score(team_a, team_b)
            match_results[(team_a, team_b)] = (goals_a, goals_b)
            points_a = 3 if goals_a > goals_b else 1 if goals_a == goals_b else 0
            points_b = 3 if goals_b > goals_a else 1 if goals_a == goals_b else 0
            group_stats[team_a]['points'] += points_a
            group_stats[team_a]['gf'] += goals_a
            group_stats[team_a]['ga'] += goals_b
            group_stats[team_b]['points'] += points_b
            group_stats[team_b]['gf'] += goals_b
            group_stats[team_b]['ga'] += goals_a
        # Sort standings with proper AFCON tiebreakers
        standings_list = list(group_stats.items())

        # Function to resolve ties according to AFCON regulations
        def resolve_ties(tied_teams_data, match_results, original_tied_count):
            """
            Resolve ties according to AFCON tiebreaking rules:
            1. Head-to-head points
            2. Head-to-head goal difference
            3. Head-to-head goals scored
            4. If >2 teams originally tied and only 2 remain, reapply h2h criteria to those 2
            5. Overall goal difference
            6. Overall goals scored
            7. Fair play points (lower is better)
            8. Drawing of lots (random shuffle)
            """
            if len(tied_teams_data) == 1:
                return tied_teams_data

            # Get head-to-head stats for all tied teams
            h2h_list = []
            tied_team_names = [t[0] for t in tied_teams_data]
            for team, stats in tied_teams_data:
                h2h_p, h2h_gd, h2h_gf = get_h2h_stats(team, tied_team_names, match_results)
                h2h_list.append((team, h2h_p, h2h_gd, h2h_gf, stats))

            # Sort by head-to-head criteria (1-3)
            h2h_list.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)

            # Group teams that are still tied after h2h criteria
            remaining_tied_groups = []
            if h2h_list:
                current_group = [h2h_list[0]]
                for i in range(1, len(h2h_list)):
                    prev = h2h_list[i-1]
                    curr = h2h_list[i]
                    if (prev[1], prev[2], prev[3]) == (curr[1], curr[2], curr[3]):
                        current_group.append(curr)
                    else:
                        remaining_tied_groups.append(current_group)
                        current_group = [curr]
                remaining_tied_groups.append(current_group)

            # Process remaining tied groups
            final_list = []
            for group in remaining_tied_groups:
                if len(group) == 1:
                    final_list.extend(group)
                elif len(group) == 2 and original_tied_count > 2:
                    # Rule 4: If >2 teams originally tied and only 2 remain,
                    # reapply all h2h criteria exclusively to these 2 teams
                    team_data = [(t[0], t[4]) for t in group]  # (team_name, stats)
                    resolved = resolve_ties(team_data, match_results, 2)
                    final_list.extend([(t[0], t[1], t[2], t[3], t[4]) for t in resolved])
                else:
                    # Apply overall GD, GF, fair play points, then random shuffle (rules 5-7)
                    # Sort by GD, then GF, then fair play points (lower is better)
                    group_with_fp = [(team, h2h_p, h2h_gd, h2h_gf, stats, get_fair_play_points(team))
                                   for team, h2h_p, h2h_gd, h2h_gf, stats in group]
                    group_with_fp.sort(key=lambda x: (x[4]['gf'] - x[4]['ga'], x[4]['gf'], x[5]), reverse=True)

                    # Group by overall GD, GF, and fair play points
                    overall_tied_groups = []
                    if group_with_fp:
                        current = [group_with_fp[0]]
                        for item in group_with_fp[1:]:
                            prev_gd = current[0][4]['gf'] - current[0][4]['ga']
                            prev_gf = current[0][4]['gf']
                            prev_fp = current[0][5]
                            curr_gd = item[4]['gf'] - item[4]['ga']
                            curr_gf = item[4]['gf']
                            curr_fp = item[5]
                            if prev_gd == curr_gd and prev_gf == curr_gf and prev_fp == curr_fp:
                                current.append(item)
                            else:
                                if len(current) > 1:
                                    random.shuffle(current)
                                overall_tied_groups.extend(current)
                                current = [item]
                        if len(current) > 1:
                            random.shuffle(current)
                        overall_tied_groups.extend(current)

                    # Convert back to the expected format
                    final_list.extend([(team, h2h_p, h2h_gd, h2h_gf, stats)
                                     for team, h2h_p, h2h_gd, h2h_gf, stats, _ in overall_tied_groups])

            return final_list

        # Group teams by points, GD, GF (initial grouping)
        tied_groups = []
        if standings_list:
            current_group = [standings_list[0]]
            for i in range(1, len(standings_list)):
                prev_stats = standings_list[i-1][1]
                curr_stats = standings_list[i][1]
                prev_gd = prev_stats['gf'] - prev_stats['ga']
                curr_gd = curr_stats['gf'] - curr_stats['ga']
                if (prev_stats['points'] == curr_stats['points'] and
                    prev_gd == curr_gd and
                    prev_stats['gf'] == curr_stats['gf']):
                    current_group.append(standings_list[i])
                else:
                    tied_groups.append(current_group)
                    current_group = [standings_list[i]]
            tied_groups.append(current_group)

        # Process each tied group using AFCON tiebreaking rules
        final_standings = []
        for tg in tied_groups:
            if len(tg) == 1:
                final_standings.extend(tg)
            else:
                resolved = resolve_ties(tg, match_results, len(tg))
                final_standings.extend([(team, stats) for team, _, _, _, stats in resolved])

        standings = final_standings
        group_standings[group_key] = standings
        results[group_key][standings[0][0]]['Group_Winner'] += 1
        for i in range(2):
            results[group_key][standings[i][0]]['Advance'] += 1
        # Accumulate stats and positions
        for pos, (team, stats) in enumerate(standings):
            results[group_key][team][f'position_{pos+1}'] += 1
            results[group_key][team]['total_points'] += stats['points']
            results[group_key][team]['total_gf'] += stats['gf']
            results[group_key][team]['total_ga'] += stats['ga']
            results[group_key][team]['total_gd'] += stats['gf'] - stats['ga']

    # Advancing teams
    winners = {group: group_standings[group][0][0] for group in 'ABCDEF'}
    runners_up = {group: group_standings[group][1][0] for group in 'ABCDEF'}
    thirds = [(group, group_standings[group][2][0], group_standings[group][2][1]) for group in 'ABCDEF']
    # Sort thirds by points, gd, gf
    sorted_thirds = sorted(thirds, key=lambda x: (x[2]['points'], x[2]['gf'] - x[2]['ga'], x[2]['gf']), reverse=True)
    best_four_thirds = [t[1] for t in sorted_thirds[:4]]

    for team in best_four_thirds:
        for group_key in GROUPS:
            if team in results[group_key]:
                results[group_key][team]['Advance_as_3rd'] += 1
                break

    # Round of 16 matches as per AFCON bracket
    ro16_matches = [
        (winners['D'], best_four_thirds[0]),  # R1: Winner D vs 3rd B/E/F
        (runners_up['A'], runners_up['C']),   # R2: Runner-up A vs Runner-up C
        (winners['A'], best_four_thirds[1]),  # R3: Winner A vs 3rd C/D/E
        (runners_up['B'], runners_up['F']),   # R4: Runner-up B vs Runner-up F
        (winners['B'], best_four_thirds[2]),  # R5: Winner B vs 3rd A/C/D
        (winners['C'], best_four_thirds[3]),  # R6: Winner C vs 3rd A/B/F
        (winners['E'], runners_up['D']),      # R7: Winner E vs Runner-up D
        (winners['F'], runners_up['E'])       # R8: Winner F vs Runner-up E
    ]
    ro16_match_keys = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8']
    ro16_winners = []
    for i, (t1, t2) in enumerate(ro16_matches):
        winner = get_knockout_match_result(ro16_match_keys[i], t1, t2)
        ro16_winners.append(winner)
        knockout_results[t1]['Round of 16'] += 1
        knockout_results[t2]['Round of 16'] += 1

    # Quarter-finals
    qf_matches = [
        (ro16_winners[1], ro16_winners[0]),  # QF1: Winner R2 vs Winner R1
        (ro16_winners[3], ro16_winners[2]),  # QF2: Winner R4 vs Winner R3
        (ro16_winners[6], ro16_winners[5]),  # QF3: Winner R7 vs Winner R6
        (ro16_winners[4], ro16_winners[7])   # QF4: Winner R5 vs Winner R8
    ]
    qf_match_keys = ['QF1', 'QF2', 'QF3', 'QF4']
    qf_winners = []
    for i, (t1, t2) in enumerate(qf_matches):
        winner = get_knockout_match_result(qf_match_keys[i], t1, t2)
        qf_winners.append(winner)
        knockout_results[t1]['Quarterfinals'] += 1
        knockout_results[t2]['Quarterfinals'] += 1

    # Semi-finals
    sf_matches = [
        (qf_winners[0], qf_winners[3]),  # SF1: Winner QF1 vs Winner QF4
        (qf_winners[2], qf_winners[1])   # SF2: Winner QF3 vs Winner QF2
    ]
    sf_match_keys = ['SF1', 'SF2']
    sf_winners = []
    for i, (t1, t2) in enumerate(sf_matches):
        winner = get_knockout_match_result(sf_match_keys[i], t1, t2)
        sf_winners.append(winner)
        knockout_results[t1]['Semifinals'] += 1
        knockout_results[t2]['Semifinals'] += 1

    # Final
    finalist1 = sf_winners[0]
    finalist2 = sf_winners[1]
    final_winner = get_knockout_match_result('FINAL', finalist1, finalist2)
    knockout_results[final_winner]['Winner'] += 1
    knockout_results[finalist1]['Final'] += 1
    knockout_results[finalist2]['Final'] += 1

    # Third place
    loser_sf1 = qf_winners[0] if qf_winners[0] != sf_winners[0] else qf_winners[3]
    loser_sf2 = qf_winners[2] if qf_winners[2] != sf_winners[1] else qf_winners[1]
    third = get_knockout_match_result('THIRD', loser_sf1, loser_sf2)
    knockout_results[third]['Third'] += 1

# -------------------------
# OUTPUT
# -------------------------
for group_key in GROUPS:
    print(f"\n## Africa Cup of Nations Group {group_key} Probabilistic Prediction ({NUM_SIMULATIONS} Simulations)")
    print("\n---")
    final_percentages = {}
    for team, data in results[group_key].items():
        final_percentages[team] = {
            '% Chance of Winning Group': (data['Group_Winner'] / NUM_SIMULATIONS) * 100,
            '% Chance of Knockout Advancement': (data['Advance'] / NUM_SIMULATIONS) * 100,
            '% Chance of Advancing as 3rd': (data['Advance_as_3rd'] / NUM_SIMULATIONS) * 100
        }
    df_final = pd.DataFrame.from_dict(final_percentages, orient='index')
    df_final = df_final.sort_values(by='% Chance of Winning Group', ascending=False)
    df_final['% Chance of Winning Group'] = df_final['% Chance of Winning Group'].round(2).astype(str) + '%'
    df_final['% Chance of Knockout Advancement'] = df_final['% Chance of Knockout Advancement'].round(2).astype(str) + '%'
    df_final['% Chance of Advancing as 3rd'] = df_final['% Chance of Advancing as 3rd'].round(2).astype(str) + '%'
    print(f"**Teams:** {', '.join(GROUPS[group_key]['teams'])}")
    print(f"**Model Basis:** Simulations use team ratings and incorporate played match results.")
    print(f"### Predicted Group {group_key} Chances:")
    print(f"{'Team':<15} {'Win Group':<10} {'Advance':<10} {'Advance 3rd':<12}")
    print("-" * 47)
    for team in df_final.index:
        win = df_final.loc[team, '% Chance of Winning Group']
        adv = df_final.loc[team, '% Chance of Knockout Advancement']
        adv3 = df_final.loc[team, '% Chance of Advancing as 3rd']
        print(f"{team:<15} {win:<10} {adv:<10} {adv3:<12}")

    # Expected final standings table
    expected_standings = {}
    for team, data in results[group_key].items():
        expected_standings[team] = {
            'Avg Points': data['total_points'] / NUM_SIMULATIONS,
            'Avg GD': data['total_gd'] / NUM_SIMULATIONS,
            'Avg GF': data['total_gf'] / NUM_SIMULATIONS,
            'Avg GA': data['total_ga'] / NUM_SIMULATIONS,
            '% 1st': (data['position_1'] / NUM_SIMULATIONS) * 100,
            '% 2nd': (data['position_2'] / NUM_SIMULATIONS) * 100,
            '% 3rd': (data['position_3'] / NUM_SIMULATIONS) * 100,
            '% 4th': (data['position_4'] / NUM_SIMULATIONS) * 100
        }
    df_expected = pd.DataFrame.from_dict(expected_standings, orient='index')
    df_expected = df_expected.round({'Avg Points': 1, 'Avg GD': 1, 'Avg GF': 1, 'Avg GA': 1, '% 1st': 1, '% 2nd': 1, '% 3rd': 1, '% 4th': 1})
    for col in ['% 1st', '% 2nd', '% 3rd', '% 4th']:
        df_expected[col] = df_expected[col].astype(str) + '%'
    print(f"### Expected Final Group {group_key} Standings:")
    print(f"{'Team':<15} {'Avg Pts':<8} {'Avg GD':<7} {'Avg GF':<7} {'Avg GA':<7} {'% 1st':<6} {'% 2nd':<6} {'% 3rd':<6} {'% 4th':<6}")
    print("-" * 74)
    for team in df_expected.index:
        pts = df_expected.loc[team, 'Avg Points']
        gd = df_expected.loc[team, 'Avg GD']
        gf = df_expected.loc[team, 'Avg GF']
        ga = df_expected.loc[team, 'Avg GA']
        p1 = df_expected.loc[team, '% 1st']
        p2 = df_expected.loc[team, '% 2nd']
        p3 = df_expected.loc[team, '% 3rd']
        p4 = df_expected.loc[team, '% 4th']
        print(f"{team:<15} {pts:<8.1f} {gd:<7.1f} {gf:<7.1f} {ga:<7.1f} {p1:<6} {p2:<6} {p3:<6} {p4:<6}")

print("\n## Knockout Stage Matrix")
print("\n---")
stages = ['Round of 16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Third']
teams_reached = [team for team, data in knockout_results.items() if data['Round of 16'] > 0]
teams_reached.sort(key=lambda t: knockout_results[t]['Winner'], reverse=True)
print(f"{'Team':<15} {'R16':<6} {'QF':<5} {'SF':<5} {'Final':<7} {'Winner':<8} {'Third':<6}")
print("-" * 60)
for team in teams_reached:
    r16 = f"{(knockout_results[team]['Round of 16'] / NUM_SIMULATIONS * 100):.1f}%"
    qf = f"{(knockout_results[team]['Quarterfinals'] / NUM_SIMULATIONS * 100):.1f}%"
    sf = f"{(knockout_results[team]['Semifinals'] / NUM_SIMULATIONS * 100):.1f}%"
    fin = f"{(knockout_results[team]['Final'] / NUM_SIMULATIONS * 100):.1f}%"
    win = f"{(knockout_results[team]['Winner'] / NUM_SIMULATIONS * 100):.1f}%"
    third = f"{(knockout_results[team]['Third'] / NUM_SIMULATIONS * 100):.1f}%"
    print(f"{team:<15} {r16:<6} {qf:<5} {sf:<5} {fin:<7} {win:<8} {third:<6}")

print("\n## Complete List: % Chance of Winning the Africa Cup of Nations")
print("\n---")
winner_teams = sorted(knockout_results.items(), key=lambda x: x[1]['Winner'], reverse=True)
print(f"{'Team':<15} {'Win %':<8}")
print("-" * 24)
for team, data in winner_teams:
    pct = (data['Winner'] / NUM_SIMULATIONS) * 100
    if pct > 0:
        print(f"{team:<15} {pct:<8.2f}%")

print("\nSimulation complete.")
