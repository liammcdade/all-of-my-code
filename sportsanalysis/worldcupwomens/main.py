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
    "AFC": {"slots": 6, "inter_conf_slots": 2, "teams": ["Australia", "China", "Japan", "North Korea", "Philippines", "South Korea"], "inter_conf_teams": ["Uzbekistan", "Chinese Taipei"], "inter_conf_mode": "final_phase_bye"},
    "CAF": {"slots": 4, "inter_conf_slots": 2, "teams": [], "inter_conf_mode": "preliminary_phase"},
    "CONCACAF": {"slots": 4, "inter_conf_slots": 2, "teams": [], "inter_conf_mode": "preliminary_phase"},
    "CONMEBOL": {"slots": 3, "inter_conf_slots": 2, "teams": ["Argentina", "Colombia", "Brazil"], "inter_conf_teams": ["Venezuela", "Ecuador"], "inter_conf_mode": "ranking_bye"},
    "OFC": {"slots": 1, "inter_conf_slots": 1, "teams": ["New Zealand"], "inter_conf_team": "Papua New Guinea", "inter_conf_mode": "preliminary_phase"},
    "UEFA": {"slots": 11, "inter_conf_slots": 1, "teams": ["Denmark", "France", "Germany", "Spain"], "inter_conf_mode": "final_phase_seeded"},
}

N_SIMS = 10000

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

def simulate_inter_conf_playoff():
    inter_conf_teams = []
    for conf, data in SLOT_ALLOCATION.items():
        if "inter_conf_team" in data:
            inter_conf_teams.append(data["inter_conf_team"])
        if "inter_conf_teams" in data:
            inter_conf_teams.extend(data["inter_conf_teams"])
    if len(inter_conf_teams) < 2:
        return inter_conf_teams
    random.shuffle(inter_conf_teams)
    qualified = []
    for _ in range(3):
        if len(inter_conf_teams) < 2:
            break
        team1 = inter_conf_teams.pop()
        team2 = inter_conf_teams.pop()
        winner = simulate_win(team1, team2)
        qualified.append(winner)
    return qualified

wc_qualifiers = defaultdict(int)
inter_conf_wc_qualifiers = defaultdict(int)

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

    winners = sorted([r2_1, r2_2, r2_3, r2_4, r2_5, r2_6, r2_7, r2_8],
                     key=lambda t: ELO[t], reverse=True)

    for i in range(7):
        wc_qualifiers[winners[i]] += 1

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

    concacaf_inter_conf = [concacaf_p1, concacaf_p2]
    ofc_inter_conf = ["Papua New Guinea"]
    afc_inter_conf = ["Uzbekistan", "Chinese Taipei"]
    conmebol_inter_conf = ["Venezuela", "Ecuador"]

    all_inter_conf = concacaf_inter_conf + conmebol_inter_conf + ofc_inter_conf + afc_inter_conf
    inter_conf_wc = simulate_inter_conf_playoff()

    for team in inter_conf_wc:
        inter_conf_wc_qualifiers[team] += 1

    # CAF qualification
    caf_groups = {
        "Group A": ["Morocco", "Algeria", "Senegal", "Kenya"],
        "Group B": ["South Africa", "Ivory Coast", "Burkina Faso", "Tanzania"],
        "Group C": ["Nigeria", "Zambia", "Egypt", "Malawi"],
        "Group D": ["Ghana", "Cameroon", "Mali", "Cape Verde"],
    }

    caf_group_winners = {}
    caf_group_runners = {}
    for group_name, teams in caf_groups.items():
        group_stats = {team: {"pts": 0} for team in teams}
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                home = teams[i]
                away = teams[j]
                result = simulate_match(home, away)
                if result == home:
                    group_stats[home]["pts"] += 3
                elif result == away:
                    group_stats[away]["pts"] += 3
                else:
                    group_stats[home]["pts"] += 1
                    group_stats[away]["pts"] += 1
        ranked = sorted(teams, key=lambda t: (group_stats[t]["pts"], ELO[t]), reverse=True)
        caf_group_winners[group_name] = ranked[0]
        caf_group_runners[group_name] = ranked[1]

    caf_qf1 = simulate_win(caf_group_winners["Group A"], caf_group_runners["Group B"])
    caf_qf2 = simulate_win(caf_group_winners["Group B"], caf_group_runners["Group A"])
    caf_qf3 = simulate_win(caf_group_winners["Group C"], caf_group_runners["Group D"])
    caf_qf4 = simulate_win(caf_group_winners["Group D"], caf_group_runners["Group C"])

    wc_qualifiers[caf_qf1] += 1
    wc_qualifiers[caf_qf2] += 1
    wc_qualifiers[caf_qf3] += 1
    wc_qualifiers[caf_qf4] += 1

    caf_sf1 = simulate_win(caf_qf1, caf_qf4)
    caf_sf2 = simulate_win(caf_qf2, caf_qf3)

    loser_qf1 = caf_qf1 if caf_qf1 != caf_sf1 and caf_qf1 != caf_sf2 else caf_qf4
    loser_qf2 = caf_qf2 if caf_qf2 != caf_sf1 and caf_qf2 != caf_sf2 else caf_qf3
    loser_qf3 = caf_qf3 if caf_qf3 != caf_sf1 and caf_qf3 != caf_sf2 else caf_qf2
    loser_qf4 = caf_qf4 if caf_qf4 != caf_sf1 and caf_qf4 != caf_sf2 else caf_qf1

qualification_prob = defaultdict(float)

for team in ALREADY_QUALIFIED:
    qualification_prob[team] = 1.0

for team in wc_qualifiers:
    qualification_prob[team] += wc_qualifiers[team] / N_SIMS

for team in inter_conf_wc_qualifiers:
    qualification_prob[team] += inter_conf_wc_qualifiers[team] / N_SIMS

print(f"\rProgress: 100%", file=sys.stderr)

all_qualifiers = sorted(qualification_prob.items(), key=lambda x: x[1], reverse=True)
top_32 = all_qualifiers[:32]
certainty = sum(prob for _, prob in top_32) / 32 * 100

print(f"\nQUALIFICATION CERTAINTY: {certainty:.2f}%")
print(f"(Average probability of the 32 most likely qualifiers)\n")

print(f"\nWORLD CUP QUALIFICATIONProbability (direct + inter-conf)\n")
for team, prob in all_qualifiers:
    print(f"{team:25s}{prob*100:6.2f}%")
