import os
import glob
import re
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
import matplotlib.pyplot as plt
from tqdm import tqdm

# ==========================================
# 1. TEAM NAME NORMALIZATION
# ==========================================
TEAM_ALIASES = {
    'manchester united fc': 'Manchester United', 'manchester united': 'Manchester United',
    'newton heath fc': 'Manchester United',
    'chelsea fc': 'Chelsea', 'chelsea': 'Chelsea',
    'arsenal fc': 'Arsenal', 'arsenal': 'Arsenal',
    'liverpool fc': 'Liverpool', 'liverpool': 'Liverpool',
    'manchester city fc': 'Manchester City', 'manchester city': 'Manchester City',
    'ardwick fc': 'Manchester City',
    'tottenham hotspur fc': 'Tottenham Hotspur', 'tottenham hotspur': 'Tottenham Hotspur',
    'tottenham': 'Tottenham Hotspur',
    'newcastle united fc': 'Newcastle United', 'newcastle united': 'Newcastle United',
    'newcastle utd': 'Newcastle United', 'newcastle': 'Newcastle United',
    'west ham united fc': 'West Ham United', 'west ham united': 'West Ham United',
    'west ham': 'West Ham United',
    'everton fc': 'Everton', 'everton': 'Everton',
    'aston villa fc': 'Aston Villa', 'aston villa': 'Aston Villa',
    'leeds united fc': 'Leeds United', 'leeds united': 'Leeds United', 'leeds': 'Leeds United',
    'leicester city fc': 'Leicester City', 'leicester city': 'Leicester City', 'leicester': 'Leicester City',
    'sunderland afc': 'Sunderland', 'sunderland': 'Sunderland',
    'charlton athletic fc': 'Charlton Athletic', 'charlton athletic': 'Charlton Athletic',
    'charlton': 'Charlton Athletic',
    'wolverhampton wanderers fc': 'Wolverhampton Wanderers',
    'wolverhampton wanderers': 'Wolverhampton Wanderers', 'wolves': 'Wolverhampton Wanderers',
    'blackburn rovers fc': 'Blackburn Rovers', 'blackburn rovers': 'Blackburn Rovers',
    'blackburn': 'Blackburn Rovers',
    'bolton wanderers fc': 'Bolton Wanderers', 'bolton wanderers': 'Bolton Wanderers',
    'bolton': 'Bolton Wanderers',
    'fulham fc': 'Fulham', 'fulham': 'Fulham',
    'southampton fc': 'Southampton', 'southampton': 'Southampton',
    'coventry city fc': 'Coventry City', 'coventry city': 'Coventry City', 'coventry': 'Coventry City',
    'nottingham forest fc': 'Nottingham Forest', 'nottingham forest': 'Nottingham Forest',
    'derby county fc': 'Derby County', 'derby county': 'Derby County', 'derby': 'Derby County',
    'ipswich town fc': 'Ipswich Town', 'ipswich town': 'Ipswich Town', 'ipswich': 'Ipswich Town',
    'middlesbrough fc': 'Middlesbrough', 'middlesbrough': 'Middlesbrough',
    'crystal palace fc': 'Crystal Palace', 'crystal palace': 'Crystal Palace',
    'watford fc': 'Watford', 'watford': 'Watford',
    'brighton & hove albion fc': 'Brighton & Hove Albion',
    'brighton & hove albion': 'Brighton & Hove Albion', 'brighton': 'Brighton & Hove Albion',
    'qpr': 'Queens Park Rangers', 'queens park rangers fc': 'Queens Park Rangers',
    'queens park rangers': 'Queens Park Rangers',
    'wimbledon fc': 'AFC Wimbledon', 'afc wimbledon': 'AFC Wimbledon',
    'small heath fc': 'Birmingham City', 'birmingham city fc': 'Birmingham City',
    'birmingham city': 'Birmingham City', 'birmingham': 'Birmingham City',
    'burslem port vale fc': 'Port Vale', 'port vale fc': 'Port Vale', 'port vale': 'Port Vale',
    'walsall town swifts fc': 'Walsall', 'walsall fc': 'Walsall', 'walsall': 'Walsall',
    'sheffield wednesday fc': 'Sheffield Wednesday', 'sheffield wednesday': 'Sheffield Wednesday',
    'the wednesday fc': 'Sheffield Wednesday', 'sheffield wed': 'Sheffield Wednesday',
    'sheffield united fc': 'Sheffield United', 'sheffield united': 'Sheffield United',
    'sheffield utd': 'Sheffield United',
    'west bromwich albion fc': 'West Bromwich Albion', 'west bromwich albion': 'West Bromwich Albion',
    'west brom': 'West Bromwich Albion',
    'norwich city fc': 'Norwich City', 'norwich city': 'Norwich City', 'norwich': 'Norwich City',
    'cardiff city fc': 'Cardiff City', 'cardiff city': 'Cardiff City', 'cardiff': 'Cardiff City',
    'swansea city afc': 'Swansea City', 'swansea city': 'Swansea City', 'swansea': 'Swansea City',
    'hull city afc': 'Hull City', 'hull city': 'Hull City', 'hull': 'Hull City',
    'bristol city fc': 'Bristol City', 'bristol city': 'Bristol City',
    'millwall fc': 'Millwall', 'millwall': 'Millwall',
    'luton town fc': 'Luton Town', 'luton town': 'Luton Town', 'luton': 'Luton Town',
    'oxford united fc': 'Oxford United', 'oxford united': 'Oxford United', 'oxford utd': 'Oxford United',
    'cambridge united': 'Cambridge United', 'cambridge utd': 'Cambridge United',
    'wigan athletic fc': 'Wigan Athletic', 'wigan athletic': 'Wigan Athletic', 'wigan': 'Wigan Athletic',
    'preston north end fc': 'Preston North End', 'preston north end': 'Preston North End',
    'preston': 'Preston North End',
    'grimsby town fc': 'Grimsby Town', 'grimsby town': 'Grimsby Town', 'grimsby': 'Grimsby Town',
    'stockport county': 'Stockport County', 'stockport': 'Stockport County',
    'tranmere rovers': 'Tranmere Rovers', 'tranmere': 'Tranmere Rovers',
    'southend united': 'Southend United', 'southend': 'Southend United',
    'colchester united': 'Colchester United', 'colchester': 'Colchester United',
    'brentford fc': 'Brentford', 'brentford': 'Brentford',
    'reading fc': 'Reading', 'reading': 'Reading',
    'plymouth argyle fc': 'Plymouth Argyle', 'plymouth argyle': 'Plymouth Argyle',
    'plymouth': 'Plymouth Argyle',
    'barnsley fc': 'Barnsley', 'barnsley': 'Barnsley',
    'burnley fc': 'Burnley', 'burnley': 'Burnley',
    'portsmouth fc': 'Portsmouth', 'portsmouth': 'Portsmouth',
    'blackpool fc': 'Blackpool', 'blackpool': 'Blackpool',
    'afc bournemouth': 'Bournemouth', 'bournemouth': 'Bournemouth',
    'stevenage fc': 'Stevenage', 'stevenage': 'Stevenage',
    'fleetwood town': 'Fleetwood Town', 'burton albion': 'Burton Albion',
    'accrington stanley': 'Accrington Stanley',
    'exeter city': 'Exeter City', 'exeter': 'Exeter City',
    'doncaster rovers': 'Doncaster Rovers',
    'scunthorpe united': 'Scunthorpe United', 'scunthorpe': 'Scunthorpe United',
    'carlisle united': 'Carlisle United', 'carlisle': 'Carlisle United',
    'mansfield town': 'Mansfield Town', 'mansfield': 'Mansfield Town',
    'cheltenham town': 'Cheltenham Town', 'cheltenham': 'Cheltenham Town',
    'harrogate town': 'Harrogate Town',
    'barrow afc': 'Barrow', 'barrow': 'Barrow',
    'forest green rovers': 'Forest Green Rovers',
    'sutton united': 'Sutton United',
    'wealdstone fc': 'Wealdstone', 'wealdstone': 'Wealdstone',
    'wrexham afc': 'Wrexham', 'wrexham fc': 'Wrexham', 'wrexham': 'Wrexham',
    'gateshead fc': 'Gateshead', 'gateshead': 'Gateshead',
    'solihull moors': 'Solihull Moors',
    'eastleigh fc': 'Eastleigh', 'eastleigh': 'Eastleigh',
    'halifax town': 'Halifax Town', 'halifax': 'Halifax Town',
    'hartlepool united': 'Hartlepool United', 'hartlepool': 'Hartlepool United',
    'yeovil town': 'Yeovil Town', 'yeovil': 'Yeovil Town',
    'boreham wood': 'Boreham Wood', 'braintree town': 'Braintree Town',
    'maidstone united': 'Maidstone United',
    'woking fc': 'Woking', 'woking': 'Woking',
    'tamworth fc': 'Tamworth', 'tamworth': 'Tamworth',
    'altrincham fc': 'Altrincham', 'altrincham': 'Altrincham',
    'salford city': 'Salford City',
    'morecambe fc': 'Morecambe', 'morecambe': 'Morecambe',
    'boston united': 'Boston United',
    'york city': 'York City', 'york': 'York City',
    'darlington fc': 'Darlington', 'darlington': 'Darlington',
    'torquay united': 'Torquay United', 'torquay': 'Torquay United',
    'rochdale afc': 'Rochdale', 'rochdale': 'Rochdale',
    'leyton orient': 'Leyton Orient',
    'northampton town': 'Northampton Town', 'northampton': 'Northampton Town',
    'crawley town': 'Crawley Town',
    'newport county': 'Newport County',
    'milton keynes dons': 'Milton Keynes Dons',
    'gillingham fc': 'Gillingham', 'gillingham': 'Gillingham',
    'bristol rovers': 'Bristol Rovers',
    'barnet fc': 'Barnet', 'barnet': 'Barnet',
    'shrewsbury town': 'Shrewsbury Town', 'shrewsbury': 'Shrewsbury Town',
    'ebbsfleet united': 'Ebbsfleet United',
    'dover athletic': 'Dover Athletic',
    'dorking wanderers': 'Dorking Wanderers',
    "king's lynn": 'Kings Lynn', 'king\'s lynn': 'Kings Lynn',
    'weymouth fc': 'Weymouth', 'weymouth': 'Weymouth',
    'havant & waterlooville': 'Havant & Waterlooville',
    'north ferriby united': 'North Ferriby United',
    'welling united fc': 'Welling United',
    'chorley fc': 'Chorley', 'chorley': 'Chorley',
    'oxford city': 'Oxford City',
    'hereford united': 'Hereford United',
    'scarborough fc': 'Scarborough',
    'kidderminster harriers': 'Kidderminster Harriers',
    'macclesfield town': 'Macclesfield Town', 'macclesfield': 'Macclesfield Town',
    'guiseley afc': 'Guiseley', 'guiseley': 'Guiseley',
    'southport fc': 'Southport', 'southport': 'Southport',
    'stoke city fc': 'Stoke City', 'stoke city': 'Stoke City',
    'stoke fc': 'Stoke City', 'stoke': 'Stoke City',
    'bury fc': 'Bury', 'bury': 'Bury',
    'bromley fc': 'Bromley', 'bromley': 'Bromley',
    'dagenham & redbridge': 'Dagenham & Redbridge',
    'aldershot town': 'Aldershot Town',
    'oldham athletic afc': 'Oldham Athletic', 'oldham athletic': 'Oldham Athletic',
    'oldham': 'Oldham Athletic',
    'huddersfield town afc': 'Huddersfield Town', 'huddersfield town': 'Huddersfield Town',
    'huddersfield': 'Huddersfield Town',
    'crewe alexandra fc': 'Crewe Alexandra', 'crewe alexandra': 'Crewe Alexandra',
    'crewe': 'Crewe Alexandra',
    'swindon town fc': 'Swindon Town', 'swindon town': 'Swindon Town', 'swindon': 'Swindon Town',
    'wycombe wanderers fc': 'Wycombe Wanderers', 'wycombe wanderers': 'Wycombe Wanderers',
    'wycombe': 'Wycombe Wanderers',
    'rotherham united fc': 'Rotherham United', 'rotherham united': 'Rotherham United',
    'rotherham': 'Rotherham United',
    'peterborough united fc': 'Peterborough United', 'peterborough united': 'Peterborough United',
    'peterborough': 'Peterborough United',
    'notts county fc': 'Notts County', 'notts county': 'Notts County',
    'lincoln city fc': 'Lincoln City', 'lincoln city': 'Lincoln City',
    'rushden & diamonds fc': 'Rushden & Diamonds',
    'northwich victoria fc': 'Northwich Victoria',
    'bradford': 'Bradford City', 'bradford city afc': 'Bradford City',
}


def normalize_team(name: str) -> str:
    cleaned = name.strip().lower()
    return TEAM_ALIASES.get(cleaned, name.strip())


# ==========================================
# 2. ROBUST MATCH PARSING
# ==========================================
def parse_all_matches(directory_path):
    matches = []
    match_pattern = re.compile(
        r'^(?!.*\s+v\s+)(?!\()'
        r'(?:\d{1,2}:\d{2}\s+)?'
        r'([A-Za-z][\w\s.&\'-]+?)'
        r'\s+(\d+)-(\d+)'
        r'(?:\s+\(\d+-\d+\))?'
        r'\s+([A-Za-z][\w\s.&\'-]+)$'
    )
    date_pattern = re.compile(
        r'^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+'
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})$'
    )
    month_map = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }

    file_paths = glob.glob(os.path.join(directory_path, '**/*.txt'), recursive=True)
    print(f"Found {len(file_paths)} league files.")

    for file_path in tqdm(file_paths, desc="Parsing files", unit="file"):
        current_month = None
        current_day = None
        source = os.path.basename(file_path).lower()

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                date_match = date_pattern.match(line)
                if date_match:
                    current_month = month_map[date_match.group(1)]
                    current_day = int(date_match.group(2))
                    continue

                m = match_pattern.match(line)
                if m and current_month is not None:
                    home_raw = m.group(1).strip()
                    away_raw = m.group(4).strip()
                    if ' v ' in home_raw or ' v ' in away_raw:
                        continue
                    if home_raw.startswith('(') or away_raw.startswith('('):
                        continue

                    home = normalize_team(home_raw)
                    away = normalize_team(away_raw)
                    year = 2000 if current_month >= 8 else 2001
                    try:
                        match_date = datetime(year, current_month, current_day)
                    except ValueError:
                        match_date = datetime(2000, 1, 1)

                    matches.append({
                        'date': match_date,
                        'home': home,
                        'away': away,
                        'home_goals': int(m.group(2)),
                        'away_goals': int(m.group(3)),
                        'source': source,
                    })

    matches.sort(key=lambda x: x['date'])
    return matches


# ==========================================
# 3. ELO RATING SYSTEM
# ==========================================
class EloSystem:
    def __init__(self, k=32, default_rating=1500, home_advantage=50, use_gd_mult=True):
        self.k = k
        self.default_rating = default_rating
        self.home_advantage = home_advantage
        self.use_gd_mult = use_gd_mult
        self.ratings = {}
        self.history = defaultdict(list)

    def reset(self, seed_ratings: dict):
        """Reset ratings with new seeds; clear history."""
        self.ratings = dict(seed_ratings)
        self.history = defaultdict(list)

    def get_or_init_rating(self, team, initial_rating=None):
        if team not in self.ratings:
            self.ratings[team] = (
                initial_rating if initial_rating is not None
                else self.default_rating
            )
        return self.ratings[team]

    def expected_score(self, rating_home, rating_away):
        diff = rating_away - (rating_home + self.home_advantage)
        return 1 / (1 + 10 ** (diff / 400.0))

    @staticmethod
    def goal_diff_multiplier(goal_diff):
        """Scale K by margin of victory (FiveThirtyEight methodology)."""
        abs_diff = abs(goal_diff)
        if abs_diff <= 1:
            return 1.0
        elif abs_diff == 2:
            return 1.5
        else:
            return 1.75 + ((abs_diff - 3) * 0.25)

    def update(self, match_index, home_team, away_team,
               home_goals, away_goals, tier_rating=None):
        home_team = normalize_team(home_team)
        away_team = normalize_team(away_team)

        r_home = self.get_or_init_rating(home_team, tier_rating)
        r_away = self.get_or_init_rating(away_team, tier_rating)

        e_home = self.expected_score(r_home, r_away)
        e_away = 1 - e_home

        if home_goals > away_goals:
            s_home, s_away = 1.0, 0.0
        elif home_goals < away_goals:
            s_home, s_away = 0.0, 1.0
        else:
            s_home, s_away = 0.5, 0.5

        # Apply goal difference multiplier only when enabled
        if self.use_gd_mult:
            gd_mult = self.goal_diff_multiplier(home_goals - away_goals)
            effective_k = self.k * gd_mult
        else:
            effective_k = self.k

        self.ratings[home_team] = r_home + effective_k * (s_home - e_home)
        self.ratings[away_team] = r_away + effective_k * (s_away - e_away)

        self.history[home_team].append((match_index, self.ratings[home_team]))
        self.history[away_team].append((match_index, self.ratings[away_team]))


# ==========================================
# 4. TWO-PASS DYNAMIC CALIBRATION
# ==========================================
def compute_league_powers(matches, elo_pass1):
    """Derive League Power = avg(club Elo) / avg(PL Elo) from Pass 1."""
    PL_BASELINE = 1800

    league_teams = defaultdict(set)
    for match in matches:
        league_teams[match['source']].add(match['home'])
        league_teams[match['source']].add(match['away'])

    league_avgs = {}
    for source, teams in league_teams.items():
        elos = [elo_pass1.ratings.get(t, 1500) for t in teams]
        league_avgs[source] = sum(elos) / len(elos) if elos else 1500

    pl_key = next((k for k in league_avgs if 'premierleague' in k), None)
    if pl_key is None:
        pl_key = max(league_avgs, key=league_avgs.get)

    pl_avg = league_avgs[pl_key]

    print(f"\n📊 PASS 1 CALIBRATION (baseline: {pl_key} = {pl_avg:.1f})")
    print(f"{'League File':<35} {'Avg Elo':>8} {'Power':>8} {'Seed':>6}")
    print("-" * 62)

    seed_ratings = {}
    for src, avg in sorted(league_avgs.items(), key=lambda x: -x[1]):
        power = avg / pl_avg
        tier_seed = int(PL_BASELINE * power)
        print(f"{src:<35} {avg:>8.1f} {power:>8.3f} {tier_seed:>6}")
        for team in league_teams[src]:
            seed_ratings[team] = tier_seed

    return seed_ratings


# ==========================================
# 5. AUTOMATED VALIDATION
# ==========================================
def validate_team_integrity(elo_system):
    teams = list(elo_system.ratings.keys())
    suspicious_pairs = []
    for i, t1 in enumerate(teams):
        for t2 in teams[i + 1:]:
            ratio = SequenceMatcher(None, t1.lower(), t2.lower()).ratio()
            if ratio > 0.70 and abs(elo_system.ratings[t1] - elo_system.ratings[t2]) > 50:
                suspicious_pairs.append((t1, t2, ratio))

    if suspicious_pairs:
        print("\n⚠️  POTENTIAL UNMERGED TEAMS:")
        for t1, t2, sim in sorted(suspicious_pairs, key=lambda x: -x[2]):
            print(f"   '{t1}' ({elo_system.ratings[t1]:.0f}) ↔ "
                  f"'{t2}' ({elo_system.ratings[t2]:.0f}) [{sim:.0%}]")
    else:
        print("\n✅ No suspicious team name duplicates detected.")


# ==========================================
# 6. MAIN EXECUTION
# ==========================================
def main():
    directory_path = (
        r'C:\Users\liam\Documents\GitHub\all-of-my-code'
        r'\sportsanalysis\ELO\england'
    )

    print(f"Scanning: {directory_path}\n")
    matches = parse_all_matches(directory_path)
    print(f"\nParsed & sorted {len(matches)} matches chronologically.\n")
    if not matches:
        return

    # --- PASS 1: Conservative Elo for calibration (no GD mult, standard K) ---
    print("=" * 62)
    print("PASS 1: Measuring empirical league strengths (all start 1500)")
    print("=" * 62)
    elo1 = EloSystem(k=20, home_advantage=65, use_gd_mult=False)
    for i, match in enumerate(tqdm(matches, desc="Pass 1 Elo", unit="match")):
        elo1.update(i + 1, match['home'], match['away'],
                     match['home_goals'], match['away_goals'])

    seed_ratings = compute_league_powers(matches, elo1)

    # --- PASS 2: Final Elo with calibrated seeds + expanded spread ---
    print("\n" + "=" * 62)
    print("PASS 2: Final Elo with dynamically calibrated tier seeds")
    print("=" * 62)
    elo2 = EloSystem(k=32, home_advantage=50, use_gd_mult=True)
    elo2.reset(seed_ratings)
    for i, match in enumerate(tqdm(matches, desc="Pass 2 Elo", unit="match")):
        elo2.update(i + 1, match['home'], match['away'],
                     match['home_goals'], match['away_goals'])

    # --- Print Final Standings ---
    print(f"\n{'Team':<30} | {'Final Elo':>9}")
    print("-" * 45)
    sorted_teams = sorted(elo2.ratings.items(), key=lambda x: x[1], reverse=True)
    for team, rating in sorted_teams:
        print(f"{team:<30} | {rating:>9.2f}")

    validate_team_integrity(elo2)

    # --- Plot Top 4 ---
    top_4 = [t for t, _ in sorted_teams[:4]]
    plt.figure(figsize=(12, 7))
    for team in top_4:
        idx, rats = zip(*elo2.history[team])
        plt.plot(idx, rats, label=team, linewidth=2)
    plt.axhline(1800, color='gray', linestyle='--', alpha=0.5, label='PL Baseline (1800)')
    plt.xlabel('Match Index (Chronological)', fontsize=12)
    plt.ylabel('Elo Rating', fontsize=12)
    plt.title('All England Leagues – Dynamically Calibrated Elo (Top 4)', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()