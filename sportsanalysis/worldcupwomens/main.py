import random
import sys
from collections import defaultdict

ALREADY_QUALIFIED = {
    "Australia", "China", "Japan", "North Korea", "Philippines", "South Korea",
    "Argentina", "Brazil","Colombia",
    "New Zealand",
    "Denmark", "France", "Germany", "Spain",
}

SLOT_ALLOCATION = {
    "AFC": {"slots": 6, "inter_conf_slots": 2, "teams": ["Australia", "China", "Japan", "North Korea", "Philippines", "South Korea"], "inter_conf_teams": ["Uzbekistan", "Chinese Taipei"], "inter_conf_mode": "preliminary_phase"},
    "CAF": {"slots": 4, "inter_conf_slots": 2, "teams": [], "inter_conf_mode": "preliminary_phase"},
    "CONCACAF": {"slots": 4, "inter_conf_slots": 2, "teams": [], "inter_conf_mode": "final_phase_bye"},
    "CONMEBOL": {"slots": 3, "inter_conf_slots": 2, "teams": ["Argentina", "Colombia", "Brazil"], "inter_conf_teams": ["Venezuela"], "inter_conf_mode": "final_phase_bye", "preliminary_team": "Ecuador"},
    "OFC": {"slots": 1, "inter_conf_slots": 1, "teams": ["New Zealand"], "inter_conf_team": "Papua New Guinea", "inter_conf_mode": "preliminary_phase"},
    "UEFA": {"slots": 11, "inter_conf_slots": 1, "teams": ["Denmark", "France", "Germany", "Spain"], "inter_conf_mode": "final_phase_seeded"},
}

N_SIMS = 10000

TEAM_CONF = {
    "Australia": "AFC", "China": "AFC", "Japan": "AFC", "North Korea": "AFC", "Philippines": "AFC", "South Korea": "AFC",
    "Uzbekistan": "AFC", "Chinese Taipei": "AFC",
    "Morocco": "CAF", "Algeria": "CAF", "Senegal": "CAF", "Kenya": "CAF",
    "Ivory Coast": "CAF", "Tanzania": "CAF", "South Africa": "CAF", "Burkina Faso": "CAF",
    "Zambia": "CAF", "Malawi": "CAF", "Nigeria": "CAF", "Egypt": "CAF",
    "Ghana": "CAF", "Cameroon": "CAF", "Mali": "CAF", "Cape Verde": "CAF",
    "United States": "CONCACAF", "Canada": "CONCACAF", "Mexico": "CONCACAF", "Costa Rica": "CONCACAF",
    "Jamaica": "CONCACAF", "Panama": "CONCACAF", "Haiti": "CONCACAF", "El Salvador": "CONCACAF",
    "Argentina": "CONMEBOL", "Brazil": "CONMEBOL", "Colombia": "CONMEBOL", "Venezuela": "CONMEBOL", "Ecuador": "CONMEBOL",
    "New Zealand": "OFC", "Papua New Guinea": "OFC",
    "Spain": "UEFA", "Germany": "UEFA", "England": "UEFA", "France": "UEFA", "Netherlands": "UEFA",
    "Sweden": "UEFA", "Denmark": "UEFA", "Norway": "UEFA", "Italy": "UEFA", "Iceland": "UEFA",
    "Republic of Ireland": "UEFA", "Austria": "UEFA", "Poland": "UEFA", "Serbia": "UEFA", "Ukraine": "UEFA",
    "Portugal": "UEFA", "Switzerland": "UEFA", "Scotland": "UEFA", "Belgium": "UEFA", "Finland": "UEFA",
    "Wales": "UEFA", "Czech Republic": "UEFA", "Turkey": "UEFA", "Northern Ireland": "UEFA", "Israel": "UEFA",
    "Slovakia": "UEFA", "Slovenia": "UEFA", "Albania": "UEFA",
    "Lithuania": "UEFA", "Kosovo": "UEFA", "Belarus": "UEFA", "Kazakhstan": "UEFA",
    "Hungary": "UEFA", "Greece": "UEFA", "Romania": "UEFA", "Croatia": "UEFA",
}

NATIONALS_LEAGUE_RANK = {
    "Germany": 1, "Spain": 2, "Denmark": 3, "France": 4, "England": 5,
    "Norway": 6, "Netherlands": 7, "Italy": 8, "Republic of Ireland": 9,
    "Sweden": 10, "Iceland": 11, "Austria": 12, "Slovenia": 13, "Poland": 14,
    "Serbia": 15, "Ukraine": 16, "Switzerland": 17, "Portugal": 18,
    "Scotland": 19, "Wales": 20, "Finland": 21, "Belgium": 22, "Turkey": 23,
    "Czech Republic": 24, "Albania": 25, "Northern Ireland": 26, "Slovakia": 27,
    "Israel": 28, "Montenegro": 29, "Latvia": 30, "Malta": 31, "Luxembourg": 32,
    "Hungary": 33, "Greece": 34, "Romania": 35, "Belarus": 36, "Kosovo": 37,
    "Lithuania": 38, "Croatia": 39, "Kazakhstan": 40, "Azerbaijan": 41,
    "Faroe Islands": 42, "Moldova": 43, "Bosnia and Herzegovina": 44,
    "Estonia": 45, "Cyprus": 46, "Armenia": 47, "Georgia": 48,
    "Bulgaria": 49, "North Macedonia": 50, "Andorra": 51, "Liechtenstein": 52,
    "Gibraltar": 53,
}

CONF_NAMES = ["AFC", "CAF", "CONCACAF", "CONMEBOL", "OFC", "UEFA"]

print("ALREADY QUALIFIED TEAMS")
print("=" * 35)
for conf, data in SLOT_ALLOCATION.items():
    if data["teams"]:
        print(f"\n{conf} ({len(data['teams'])}/{data['slots']} slots):")
        for team in sorted(data["teams"]):
            print(f"  {team}")
print(f"\nTotal: {len(ALREADY_QUALIFIED)} teams")

print(f"\nREMAINING SLOTS")
print("=" * 35)
total_remaining = 32 - len(ALREADY_QUALIFIED)
print(f"Total remaining: {total_remaining} slots to fill\n")
for conf, data in SLOT_ALLOCATION.items():
    remaining = data["slots"] - len(data["teams"])
    if remaining > 0:
        print(f"  {conf}: {remaining} slot(s) remaining")
    else:
        print(f"  {conf}: Full ({data['slots']} slots)")

print(f"\nINTER-CONFEDERATION PLAY-OFF ALLOCATION")
print("=" * 45)
for conf, data in SLOT_ALLOCATION.items():
    slots = data["inter_conf_slots"]
    mode = data.get("inter_conf_mode", "")
    if "inter_conf_team" in data:
        print(f"  {conf}: {slots} slot(s) — {data['inter_conf_team']} (direct qualifier from qualifiers)")
    elif "inter_conf_teams" in data:
        teams_str = ", ".join(data["inter_conf_teams"])
        print(f"  {conf}: {slots} slot(s) — {teams_str}" + (f" [{mode}]" if mode else ""))
    else:
        print(f"  {conf}: {slots} slot(s)")

ELO = {
    "Spain": 2140, "Germany": 2090, "England": 2085, "France": 2060, "Netherlands": 2030,
    "Sweden": 2010, "Denmark": 1980, "Norway": 1970, "Italy": 1940, "Iceland": 1860,
    "Republic of Ireland": 1820, "Austria": 1810, "Poland": 1780, "Serbia": 1700, "Ukraine": 1680,
    "Portugal": 1910, "Switzerland": 1890, "Scotland": 1860, "Belgium": 1850, "Finland": 1830,
    "Wales": 1810, "Czech Republic": 1800, "Turkey": 1720, "Northern Ireland": 1710, "Israel": 1690,
    "Albania": 1600, "Slovakia": 1580, "Slovenia": 1550, "Hungary": 1760, "Romania": 1740,
    "Greece": 1730, "Croatia": 1720, "Kosovo": 1690, "Belarus": 1680, "Kazakhstan": 1660,
    "Lithuania": 1530,
    "United States": 2250, "Canada": 2120, "Mexico": 1950, "Costa Rica": 1820,
    "Jamaica": 1780, "Panama": 1700, "Haiti": 1650, "El Salvador": 1600,
    "Venezuela": 1720, "Ecuador": 1720,
    "Uzbekistan": 1680, "Chinese Taipei": 1660,
    "Morocco": 1750, "Algeria": 1720, "Senegal": 1700, "Kenya": 1650,
    "South Africa": 1780, "Ivory Coast": 1740, "Burkina Faso": 1680, "Tanzania": 1620,
    "Nigeria": 1820, "Zambia": 1700, "Egypt": 1680, "Malawi": 1600,
    "Ghana": 1760, "Cameroon": 1740, "Mali": 1660, "Cape Verde": 1580,
    "Papua New Guinea": 1500,
}

CAF_GROUPS = {
    "Group A": ["Morocco", "Algeria", "Senegal", "Kenya"],
    "Group B": ["Ivory Coast", "Tanzania", "South Africa", "Burkina Faso"],
    "Group C": ["Zambia", "Malawi", "Nigeria", "Egypt"],
    "Group D": ["Ghana", "Cameroon", "Mali", "Cape Verde"],
}

CAF_PLAYED = {
    ("Algeria", "Senegal"): (2, 0),
    ("Morocco", "Kenya"): (4, 0),
    ("South Africa", "Tanzania"): (1, 2),
    ("Ivory Coast", "Burkina Faso"): (4, 1),
    ("Zambia", "Egypt"): (6, 0),
    ("Nigeria", "Malawi"): (2, 3),
    ("Ghana", "Cape Verde"): (2, 0),
    ("Cameroon", "Mali"): (2, 1),
    ("Senegal", "Kenya"): (1, 0),
    ("South Africa", "Ivory Coast"): (1, 2),
    
}

def simulate_tie(team1, team2):
    """Two-legged tie. team1 hosts 1st leg, team2 hosts 2nd leg."""
    elo_diff_1 = ELO[team1] + 60 - ELO[team2]
    p_home = 1 / (1 + 10 ** (-elo_diff_1 / 400))
    draw_prob = 0.24

    r = random.random()
    if r < p_home * (1 - draw_prob):
        goals1_1, goals2_1 = 2, 0
    elif r < p_home * (1 - draw_prob) + draw_prob:
        goals1_1, goals2_1 = 1, 1
    else:
        goals1_1, goals2_1 = 0, 2

    elo_diff_2 = ELO[team2] + 60 - ELO[team1]
    p_home2 = 1 / (1 + 10 ** (-elo_diff_2 / 400))
    r = random.random()
    if r < p_home2 * (1 - draw_prob):
        goals2_2, goals1_2 = 2, 0
    elif r < p_home2 * (1 - draw_prob) + draw_prob:
        goals2_2, goals1_2 = 1, 1
    else:
        goals2_2, goals1_2 = 0, 2

    agg1 = goals1_1 + goals1_2
    agg2 = goals2_1 + goals2_2

    if agg1 > agg2:
        return team1
    elif agg2 > agg1:
        return team2
    else:
        elo_pen = ELO[team2] + 30 - ELO[team1]
        p = 1 / (1 + 10 ** (-elo_pen / 400))
        return team2 if random.random() < p else team1

def simulate_match(team1, team2, draw_factor: float = 0.25):
    """Single match at neutral venue. Returns winner."""
    elo_diff = ELO[team1] - ELO[team2]
    p_team1 = 1 / (1 + 10 ** (-elo_diff / 400))
    r = random.random()
    if r < p_team1 * (1 - draw_factor):
        return team1
    elif r < p_team1 * (1 - draw_factor) + draw_factor:
        return None
    else:
        return team2

def simulate_win(team1, team2, draw_factor: float = 0.25) -> str:
    result = simulate_match(team1, team2, draw_factor)
    if result is None:
        p_team1 = 1 / (1 + 10 ** (-(ELO[team1] - ELO[team2]) / 400))
        return team1 if random.random() < p_team1 else team2
    return result

def simulate_match_with_scores(team1, team2, draw_factor: float = 0.25):
    """Simulate a single match and return (goals1, goals2)."""
    elo_diff = ELO[team1] - ELO[team2]
    p_team1 = 1 / (1 + 10 ** (-elo_diff / 400))
    r = random.random()

    team1_win_prob = p_team1 * (1 - draw_factor)
    draw_prob = draw_factor
    team2_win_prob = (1 - p_team1) * (1 - draw_factor)

    if r < team1_win_prob:
        return (2, 0) if random.random() < 0.6 else (1, 0)
    elif r < team1_win_prob + draw_prob:
        return (1, 1) if random.random() < 0.5 else (0, 0)
    else:
        return (0, 2) if random.random() < 0.6 else (0, 1)


def simulate_preliminary_phase(teams):
    """Simulate preliminary phase round-robin. Returns (top_2, stats_dict)."""
    stats = {t: {'pts': 0, 'gf': 0, 'ga': 0, 'gd': 0, 'wins': 0, 'draws': 0, 'losses': 0} for t in teams}
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            g1, g2 = simulate_match_with_scores(teams[i], teams[j])
            stats[teams[i]]['gf'] += g1
            stats[teams[i]]['ga'] += g2
            stats[teams[i]]['gd'] += g1 - g2
            stats[teams[j]]['gf'] += g2
            stats[teams[j]]['ga'] += g1
            stats[teams[j]]['gd'] += g2 - g1
            if g1 > g2:
                stats[teams[i]]['pts'] += 3
                stats[teams[i]]['wins'] += 1
                stats[teams[j]]['losses'] += 1
            elif g2 > g1:
                stats[teams[j]]['pts'] += 3
                stats[teams[j]]['wins'] += 1
                stats[teams[i]]['losses'] += 1
            else:
                stats[teams[i]]['pts'] += 1
                stats[teams[j]]['pts'] += 1
                stats[teams[i]]['draws'] += 1
                stats[teams[j]]['draws'] += 1

    ranked = sorted(teams, key=lambda t: (
        stats[t]['pts'],
        stats[t]['gd'],
        stats[t]['gf'],
        stats[t]['wins']
    ), reverse=True)
    return ranked[:2], stats


def simulate_final_phase(teams):
    """Simulate final phase. Returns (qualified, matchups)."""
    ranked = sorted(teams, key=lambda t: ELO.get(t, 1500), reverse=True)
    seeded = ranked[:3]
    unseeded = ranked[3:]

    qualified = []
    matchups = []
    used_unseeds = set()

    for seed in seeded:
        for i, unseed in enumerate(unseeded):
            if i not in used_unseeds and TEAM_CONF.get(seed) != TEAM_CONF.get(unseed):
                winner = simulate_win(seed, unseed)
                qualified.append(winner)
                matchups.append((seed, unseed, winner))
                used_unseeds.add(i)
                break
        else:
            for i, unseed in enumerate(unseeded):
                if i not in used_unseeds:
                    winner = simulate_win(seed, unseed)
                    qualified.append(winner)
                    matchups.append((seed, unseed, winner))
                    used_unseeds.add(i)
                    break

    return qualified, matchups


def simulate_inter_conf_playoff(preliminary_teams, bye_teams):
    """Simulate inter-confederation playoff. Returns (final_qualified, prelim_winners, prelim_stats, matchups)."""
    prelim_winners, prelim_stats = simulate_preliminary_phase(preliminary_teams)
    final_teams = bye_teams + prelim_winners
    final_qualified, matchups = simulate_final_phase(final_teams)
    return final_qualified, prelim_winners, prelim_stats, matchups


def simulate_caf_group_match(team1, team2):
    result = simulate_match(team1, team2, draw_factor=0.25)
    if result == team1:
        return random.choice([1, 2]), 0
    elif result == team2:
        return 0, random.choice([1, 2])
    else:
        d = random.choice([0, 1])
        return d, d


def simulate_caf_group(group_name, teams, played):
    stats = {t: {'pts': 0, 'gf': 0, 'ga': 0, 'gd': 0} for t in teams}
    fixtures = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            fixtures.append((teams[i], teams[j]))
    results = []
    for home, away in fixtures:
        key = (home, away)
        rev_key = (away, home)
        if key in played or rev_key in played:
            if key in played:
                gh, ga = played[key]
            else:
                ga, gh = played[rev_key]
        else:
            gh, ga = simulate_caf_group_match(home, away)
        results.append((home, away, gh, ga))
        stats[home]['gf'] += gh
        stats[home]['ga'] += ga
        stats[home]['gd'] += gh - ga
        stats[away]['gf'] += ga
        stats[away]['ga'] += gh
        stats[away]['gd'] += ga - gh
        if gh > ga:
            stats[home]['pts'] += 3
        elif gh < ga:
            stats[away]['pts'] += 3
        else:
            stats[home]['pts'] += 1
            stats[away]['pts'] += 1
    ranked = sorted(teams, key=lambda t: (stats[t]['pts'], stats[t]['gd'], stats[t]['gf']), reverse=True)
    refined = []
    i = 0
    while i < len(ranked):
        j = i + 1
        while j < len(ranked) and (stats[ranked[j]]['pts'], stats[ranked[j]]['gd'], stats[ranked[j]]['gf']) == (stats[ranked[i]]['pts'], stats[ranked[i]]['gd'], stats[ranked[i]]['gf']):
            j += 1
        block = ranked[i:j]
        if len(block) == 1:
            refined.extend(block)
        else:
            h2h = {t: {'pts': 0, 'gd': 0, 'gf': 0} for t in block}
            for h, a, gh, ga in results:
                if h in block and a in block:
                    if gh > ga:
                        h2h[h]['pts'] += 3
                    elif gh < ga:
                        h2h[a]['pts'] += 3
                    else:
                        h2h[h]['pts'] += 1
                        h2h[a]['pts'] += 1
                    h2h[h]['gd'] += gh - ga
                    h2h[a]['gd'] += ga - gh
                    h2h[h]['gf'] += gh
                    h2h[a]['gf'] += ga
            block.sort(key=lambda t: (h2h[t]['pts'], h2h[t]['gd'], h2h[t]['gf']), reverse=True)
            refined.extend(block)
        i = j
    return refined, stats


def simulate_caf_qualification():
    group_winners = {}
    group_runners = {}
    for group_name, teams in CAF_GROUPS.items():
        ranked, _ = simulate_caf_group(group_name, teams, CAF_PLAYED)
        group_winners[group_name] = ranked[0]
        group_runners[group_name] = ranked[1]
    qf1 = simulate_win(group_winners["Group A"], group_runners["Group B"])
    qf2 = simulate_win(group_winners["Group B"], group_runners["Group A"])
    qf3 = simulate_win(group_winners["Group C"], group_runners["Group D"])
    qf4 = simulate_win(group_winners["Group D"], group_runners["Group C"])
    wc_direct = [qf1, qf2, qf3, qf4]
    losers = [
        group_winners["Group A"] if qf1 != group_winners["Group A"] else group_runners["Group B"],
        group_winners["Group B"] if qf2 != group_winners["Group B"] else group_runners["Group A"],
        group_winners["Group C"] if qf3 != group_winners["Group C"] else group_runners["Group D"],
        group_winners["Group D"] if qf4 != group_winners["Group D"] else group_runners["Group C"],
    ]
    playin1 = simulate_win(losers[1], losers[2])
    playin2 = simulate_win(losers[0], losers[3])
    inter_conf = [playin1, playin2]
    return wc_direct, inter_conf


wc_qualifiers = defaultdict(int)
uefa_inter_conf = defaultdict(int)
uefa_final_phase = defaultdict(int)
inter_conf_participants = defaultdict(int)
inter_conf_wc_qualifiers = defaultdict(int)
inter_conf_by_conf = defaultdict(int)
preliminary_winners = defaultdict(int)
preliminary_runners_up = defaultdict(int)

print(f"\nRunning {N_SIMS} simulations...", file=sys.stderr)
update_interval = max(1, N_SIMS // 100)

for sim in range(N_SIMS):
    if sim % update_interval == 0:
        pct = sim / N_SIMS * 100
        print(f"\rProgress: {pct:.0f}%", end="", file=sys.stderr)

    w1 = simulate_tie("Lithuania", "Sweden")
    w2 = simulate_tie("Romania", "Norway")
    w3 = simulate_tie("Greece", "England")
    w4 = simulate_tie("Croatia", "Iceland")
    w5 = simulate_tie("Kazakhstan", "Republic of Ireland")
    w6 = simulate_tie("Kosovo", "Austria")
    w7 = simulate_tie("Hungary", "Netherlands")
    w8 = simulate_tie("Belarus", "Italy")

    w9  = simulate_tie("Albania", "Wales")
    w10 = simulate_tie("Turkey", "Slovenia")
    w11 = simulate_tie("Slovakia", "Ukraine")
    w12 = simulate_tie("Israel", "Switzerland")
    w13 = simulate_tie("Belgium", "Poland")
    w14 = simulate_tie("Czech Republic", "Scotland")
    w15 = simulate_tie("Northern Ireland", "Portugal")
    w16 = simulate_tie("Finland", "Serbia")

    r2_1 = simulate_tie(w11, w3)
    r2_2 = simulate_tie(w16, w8)
    r2_3 = simulate_tie(w15, w4)
    r2_4 = simulate_tie(w9,  w2)
    r2_5 = simulate_tie(w12, w6)
    r2_6 = simulate_tie(w14, w1)
    r2_7 = simulate_tie(w13, w5)
    r2_8 = simulate_tie(w10, w7)

    r1_winners = [w1, w2, w3, w4, w5, w6, w7, w8, w9, w10, w11, w12, w13, w14, w15, w16]
    r1_sorted = sorted(r1_winners, key=lambda t: NATIONALS_LEAGUE_RANK.get(t, 999))
    r2_winners = [simulate_tie(r1_sorted[i], r1_sorted[15 - i]) for i in range(8)]
    r2_sorted = sorted(r2_winners, key=lambda t: NATIONALS_LEAGUE_RANK.get(t, 999))
    for i in range(7):
        wc_qualifiers[r2_sorted[i]] += 1
    uefa_inter_conf[r2_sorted[7]] += 1

    concacaf_d1 = simulate_win("United States", "El Salvador")
    concacaf_d2 = simulate_win("Jamaica", "Costa Rica")
    concacaf_d3 = simulate_win("Canada", "Panama")
    concacaf_d4 = simulate_win("Mexico", "Haiti")

    wc_qualifiers[concacaf_d1] += 1
    wc_qualifiers[concacaf_d2] += 1
    wc_qualifiers[concacaf_d3] += 1
    wc_qualifiers[concacaf_d4] += 1

    concacaf_losers = [t for t in ["United States", "El Salvador", "Jamaica", "Costa Rica", "Canada", "Panama", "Mexico", "Haiti"] if t not in [concacaf_d1, concacaf_d2, concacaf_d3, concacaf_d4]]

    concacaf_p1 = simulate_win(concacaf_losers[0], concacaf_losers[1])
    concacaf_p2 = simulate_win(concacaf_losers[2], concacaf_losers[3])

    # CAF qualification
    caf_direct, caf_inter_conf = simulate_caf_qualification()
    for team in caf_direct:
        wc_qualifiers[team] += 1

    # Inter-confederation playoff
    preliminary_teams = ["Uzbekistan", "Chinese Taipei"] + caf_inter_conf + ["Papua New Guinea", "Ecuador"]
    bye_teams = [concacaf_p1, concacaf_p2, r2_sorted[7], "Venezuela"]

    inter_conf_wc, prelim_winners, prelim_stats, matchups = simulate_inter_conf_playoff(preliminary_teams, bye_teams)

    for team in preliminary_teams + bye_teams:
        inter_conf_participants[team] += 1

    for team in inter_conf_wc:
        inter_conf_wc_qualifiers[team] += 1

    confs_with_slot = {TEAM_CONF.get(team, "Unknown") for team in inter_conf_wc}
    for conf in confs_with_slot:
        inter_conf_by_conf[conf] += 1

    uefa_final_phase[r2_sorted[7]] += 1
    preliminary_winners[prelim_winners[0]] += 1
    preliminary_runners_up[prelim_winners[1]] += 1
    last_prelim_stats = prelim_stats
    last_matchups = matchups

qualification_prob = defaultdict(float)

for team in ALREADY_QUALIFIED:
    qualification_prob[team] = 1.0

for team in wc_qualifiers:
    qualification_prob[team] += wc_qualifiers[team] / N_SIMS

for team in inter_conf_wc_qualifiers:
    qualification_prob[team] += inter_conf_wc_qualifiers[team] / N_SIMS

print(f"\rProgress: 100%", file=sys.stderr)

last_prelim_stats = None
last_matchups = None

all_qualifiers = sorted(qualification_prob.items(), key=lambda x: x[1], reverse=True)
top_32 = all_qualifiers[:32]
certainty = sum(prob for _, prob in top_32) / 32 * 100

print(f"\nQUALIFICATION CERTAINTY: {certainty:.2f}%")
print(f"(Average probability of the 32 most likely qualifiers)\n")

print(f"\nWORLD CUP QUALIFICATION PROBABILITY BY CONFEDERATION\n")
for conf in CONF_NAMES:
    conf_teams = sorted(
        [(team, prob) for team, prob in all_qualifiers if TEAM_CONF.get(team) == conf],
    key=lambda x: x[1],
        reverse=True,
    )
    if not conf_teams:
        continue
    print(f"\n{conf}")
    print("-" * 35)
    for team, prob in conf_teams:
        print(f"{team:25s}{prob*100:6.2f}%")

most_likely_uefa_inter = max(uefa_inter_conf.items(), key=lambda x: x[1], default=(None, 0))
if most_likely_uefa_inter[0]:
    print(f"\nMOST LIKELY UEFA TEAM TO ENTER INTER-CONFEDERATION PLAY-OFF FINAL PHASE: {most_likely_uefa_inter[0]} ({most_likely_uefa_inter[1] / N_SIMS * 100:.2f}%)")

print(f"\n\nPRELIMINARY PHASE RESULTS (Last Simulation)")
print(f"(Top 2 advance to final phase)\n")
if last_prelim_stats:
    print("-" * 50)
    print(f"{'Team':20s} {'Pld':>4s} {'W':>3s} {'D':>3s} {'L':>3s} {'GF':>4s} {'GA':>4s} {'GD':>5s} {'Pts':>4s}")
    print("-" * 50)
    for team in sorted(last_prelim_stats.keys(), key=lambda t: (last_prelim_stats[t]['pts'], last_prelim_stats[t]['gd'], last_prelim_stats[t]['gf'], last_prelim_stats[t]['wins']), reverse=True):
        s = last_prelim_stats[team]
        pld = s['wins'] + s['draws'] + s['losses']
        print(f"{team:20s} {pld:4d} {s['wins']:3d} {s['draws']:3d} {s['losses']:3d} {s['gf']:4d} {s['ga']:4d} {s['gd']:5d} {s['pts']:4d}")
    print("-" * 50)
    top2 = sorted(last_prelim_stats.keys(), key=lambda t: (last_prelim_stats[t]['pts'], last_prelim_stats[t]['gd'], last_prelim_stats[t]['gf'], last_prelim_stats[t]['wins']), reverse=True)[:2]
    print(f"Advancing: {', '.join(top2)}")

print(f"\n\nPRELIMINARY PHASE - PROBABILITY OF ADVANCING\n")
print(f"(Chance of finishing in top 2)\n")
prelim_advance = sorted(
    [(team, (preliminary_winners[team] + preliminary_runners_up[team]) / N_SIMS)
     for team in preliminary_winners],
    key=lambda x: x[1],
    reverse=True,
)
print("-" * 40)
print(f"{'Team':25s} {'Advance %':>12s}")
for team, prob in prelim_advance:
    print(f"{team:25s} {prob*100:11.2f}%")

print(f"\n\nFINAL PHASE RESULTS (Last Simulation)\n")
if last_matchups:
    print("-" * 60)
    for seed, unseed, winner in last_matchups:
        print(f"{seed:20s} vs {unseed:20s} → {winner:20s} ✓")
    print("-" * 60)

print(f"\n\nINTER-CONFEDERATION PLAY-OFF PROBABILITIES\n")
print(f"(Chance of qualifying for the World Cup through play-offs)\n")
inter_conf_teams = sorted(
    [(team, inter_conf_participants[team] / N_SIMS, inter_conf_wc_qualifiers[team] / N_SIMS)
     for team in inter_conf_participants],
    key=lambda x: x[2],
    reverse=True,
)
print("-" * 60)
print(f"{'Team':25s} {'Reach Play-off':>15s} {'Qualify via Play-off':>20s}")
for team, reach, qualify in inter_conf_teams:
    print(f"{team:25s} {reach*100:13.2f}% {qualify*100:19.2f}%")

print(f"\n\nCONFEDERATION INTER-CONFEDERATION SLOT PROBABILITY\n")
print(f"(Chance of getting at least one World Cup spot via inter-confederation playoff)\n")
for conf in CONF_NAMES:
    if conf in inter_conf_by_conf:
        prob = inter_conf_by_conf[conf] / N_SIMS * 100
        print(f"{conf}: {prob:.2f}%")
