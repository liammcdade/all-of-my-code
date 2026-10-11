import random

# 1. Hardcoded Elo ratings from the provided CSV data
elo_ratings = {
    "Man City": 2010.7836367639238,
    "Arsenal": 1989.3611057333628,
    "Liverpool": 1860.7279670985145,
    "Man United": 1850.8891970173254,
    "Brighton": 1841.0211575935816,
    "Bournemouth": 1824.0609850918595,
    "Brentford": 1821.5243401977068,
    "Aston Villa": 1786.127671831527,
    "Leeds": 1775.3342197987322,
    "Everton": 1767.6484544799212,
    "Newcastle": 1764.9138653134823,
    "Chelsea": 1762.583783993479,
    "Nott'm Forest": 1747.7984777256838,
    "Fulham": 1711.9018852380646,
    "Crystal Palace": 1699.5569009945032,
    "West Ham": 1681.5692755637274,
    "Sunderland": 1672.8181922794574,
    "Tottenham": 1639.3816342781274,
    "Wolves": 1547.9475992242556,
    "Ipswich": 1532.5831519737835,
    "Coventry": 1504.3809028862806,
    "Burnley": 1500.9217078231452,
    "Southampton": 1447.6563255960123,
    "Hull": 1436.602469710685,
    "Lincoln": 1417.8185712259785,
    "Millwall": 1395.4777264514241,
    "Middlesbrough": 1350.2234625213373,
    "Norwich": 1334.1518789628956,
    "Wrexham": 1327.6505571747773,
    "Derby": 1304.6505604221713,
    "Swansea": 1304.5265381809784,
    "Birmingham": 1304.1358066488485,
    "Cardiff": 1303.6074095037484,
    "Sheffield United": 1286.6149271597833,
    "Plymouth": 1275.6565204656315,
    "Luton": 1273.998562783496,
    "Portsmouth": 1261.4982564324473,
    "Stockport": 1256.6657496463106,
    "Bolton": 1250.5291959079238,
    "Bristol City": 1247.496621117459,
    "Blackburn": 1236.4502820647497,
    "West Brom": 1233.4181670128185,
    "Mansfield": 1230.4205520583453,
    "Leicester": 1228.5432051115192,
    "Stevenage": 1221.0605594655588,
    "Milton Keynes Dons": 1218.284411630823,
    "Bromley": 1217.8090646204216,
    "Bradford": 1213.6029718526481,
    "QPR": 1212.8887412208367,
    "Preston": 1212.7451552629345,
    "Charlton": 1207.2216735987472,
    "Oxford": 1197.4328769980957,
    "Cambridge": 1197.0425123612229,
    "Wycombe": 1195.170639123425,
    "Chesterfield": 1193.1123525684566,
    "Blackpool": 1192.8340257602906,
    "Huddersfield": 1190.2318512622132,
    "Reading": 1186.2473475007585,
    "Watford": 1185.3055164175332,
    "Grimsby": 1181.0298872693552,
    "Salford": 1174.9622003277593,
    "Barnet": 1174.093806044488,
    "Stoke": 1167.1772717066501,
    "Doncaster": 1165.6987476475947,
    "Notts County": 1161.5672800815744,
    "Bury": 1150.2025934752996,
    "Wigan": 1139.4908831553203,
    "Burton": 1132.1021596493315,
    "Barnsley": 1128.175953658714,
    "Leyton Orient": 1121.873228643075,
    "Swindon": 1115.8737617595834,
    "Colchester": 1114.3899557534487,
    "Bristol Rvs": 1107.0769802556172,
    "Oldham": 1105.142695211731,
    "Port Vale": 1100.9617836837888,
    "Peterboro": 1095.2031553596712,
    "Exeter": 1092.601831334788,
    "Wimbledon": 1090.0873060346191,
    "Kidderminster": 1088.4040827224283,
    "Crewe": 1086.7678170767635,
    "Fleetwood Town": 1078.006687370749,
    "AFC Wimbledon": 1066.2836822296788,
    "Walsall": 1055.9740039532194,
    "Rotherham": 1038.8180537371202,
    "Aldershot": 1028.0711340564974,
    "Sutton": 1024.153951117176,
    "Sheffield Weds": 1023.0331018110688,
    "Scarborough": 1021.0215515684511,
    "Cheltenham": 1020.1317567750524,
    "Hereford": 1018.2144177180269,
    "Southend": 1015.7681099281735,
    "Accrington": 1000.2484328619208,
    "Gillingham": 999.9154533450713,
    "Hartlepool": 996.0150027099122,
    "Carlisle": 994.4381977078381,
    "Crawley Town": 994.0393658529027,
    "Shrewsbury": 993.945127351084,
    "Torquay": 991.0809360931482,
    "Rochdale": 985.9930267575577,
    "Newport County": 981.8853419911738,
    "Boston": 980.8713456843165,
    "Rushden & D": 979.6498467696737,
    "Macclesfield": 979.0637709111596,
    "Forest Green": 979.0550230154435,
    "Harrogate": 976.2396044856182,
    "Northampton": 959.8689781377024,
    "York": 955.7216475475888,
    "Dag and Red": 948.8543031624317,
    "Halifax": 945.0602120106844,
    "Darlington": 944.045409328075,
    "Tranmere": 942.6429782827647,
    "Barrow": 933.5254193209282,
    "Morecambe": 931.2309537577223,
    "Yeovil": 924.1398432835155,
    "Chester": 917.062405028551,
    "Scunthorpe": 847.0195044912501
}

# 2. Map the team names from the fixtures to the hardcoded dictionary names
name_mapping = {
    "Bradford City": "Bradford",
    "Peterborough United": "Peterboro",
    "Manchester City": "Man City",
    "Brighton & Hove Albion": "Brighton",
    "Newcastle United": "Newcastle"
}

def get_elo(team_name):
    """Retrieve Elo rating, applying name mapping if necessary."""
    csv_name = name_mapping.get(team_name, team_name)
    return elo_ratings.get(csv_name, 1500.0)

# 3. Simulate a single knockout match
def simulate_match(team_a, team_b):
    """Simulates a match and returns the winner based on Elo probabilities."""
    elo_a = get_elo(team_a)
    elo_b = get_elo(team_b)
    
    # Calculate expected score for Team A
    exp_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    
    # Randomly determine the winner (since it's a knockout, no draws)
    if random.random() < exp_a:
        return team_a
    else:
        return team_b

# 4. Define the 4th Round fixtures from the image
round_4_fixtures = [
    ("Bradford City", "Peterborough United"),
    ("Fleetwood Town", "Arsenal"),
    ("Manchester City", "Brighton & Hove Albion"),
    ("Bournemouth", "Aston Villa"),
    ("Fulham", "Crystal Palace"),
    ("Sunderland", "Brentford"),
    ("Liverpool", "Chelsea"),
    ("Everton", "Newcastle United")
]

def run_single_tournament():
    """Runs one full tournament from the 4th round and returns the winner and finalists."""
    # 4th Round (Fixed fixtures based on the image)
    quarter_finalists = []
    for team_a, team_b in round_4_fixtures:
        winner = simulate_match(team_a, team_b)
        quarter_finalists.append(winner)
        
    # Quarter-Finals (Random Draw)
    random.shuffle(quarter_finalists) # <--- Random draw!
    semi_finalists = []
    for i in range(0, len(quarter_finalists), 2):
        winner = simulate_match(quarter_finalists[i], quarter_finalists[i+1])
        semi_finalists.append(winner)
        
    # Semi-Finals (Random Draw)
    random.shuffle(semi_finalists) # <--- Random draw!
    finalists = []
    for i in range(0, len(semi_finalists), 2):
        winner = simulate_match(semi_finalists[i], semi_finalists[i+1])
        finalists.append(winner)
        
    # Final
    winner = simulate_match(finalists[0], finalists[1])
    
    return winner, finalists

def run_monte_carlo_simulation(num_simulations=10000):
    # Get unique list of teams in the 4th round for tracking
    starting_teams = set()
    for team_a, team_b in round_4_fixtures:
        starting_teams.add(team_a)
        starting_teams.add(team_b)
        
    # Initialize trackers
    win_counts = {team: 0 for team in starting_teams}
    final_counts = {team: 0 for team in starting_teams}
    
    # Run simulations
    for _ in range(num_simulations):
        winner, finalists = run_single_tournament()
        
        win_counts[winner] += 1
        for finalist in finalists:
            final_counts[finalist] += 1
            
    # Prepare and sort results by win percentage (descending)
    results = []
    for team in starting_teams:
        win_pct = (win_counts[team] / num_simulations) * 100
        final_pct = (final_counts[team] / num_simulations) * 100
        elo = get_elo(team)
        results.append((team, elo, final_pct, win_pct))
        
    results.sort(key=lambda x: x[3], reverse=True)
    
    # Print formatted results
    print(f"\n{'='*65}")
    print(f" EFL CUP SIMULATION RESULTS ({num_simulations:,} simulations)")
    print(f"{'='*65}")
    print(f"{'Team':<20} | {'Elo':<6} | {'Final %':<10} | {'Win %':<10}")
    print(f"{'-'*65}")
    
    for team, elo, final_pct, win_pct in results:
        print(f"{team:<20} | {elo:<6.0f} | {final_pct:>8.2f}% | {win_pct:>8.2f}%")
        
    print(f"{'='*65}\n")

if __name__ == "__main__":
    run_monte_carlo_simulation(10000)