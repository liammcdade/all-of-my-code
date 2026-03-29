import csv
import math
import re
import os

def calculate_expected_score(rating_a, rating_b):
    """
    Calculate expected score using Elo formula.
    We = 1 / (10^(-dr/400) + 1)
    where dr = rating difference
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def get_k_factor(tournament):
    """
    Get base K-factor based on tournament type.
    60 for World Cup finals;
    50 for continental championship finals and major intercontinental tournaments;
    40 for World Cup and continental qualifiers and major tournaments;
    30 for all other tournaments;
    20 for friendly matches.
    """
    tournament_lower = tournament.lower()
    
    # World Cup finals
    if 'world cup' in tournament_lower and 'qualifier' not in tournament_lower:
        return 60
    
    # Continental championship finals and major intercontinental tournaments
    if any(term in tournament_lower for term in ['euro', 'afcon', 'copa america', 'asian cup', 'confederations', 'olympics']):
        if 'qualifier' not in tournament_lower and 'group' not in tournament_lower:
            return 50
    
    # World Cup and continental qualifiers and major tournaments
    if 'qualifier' in tournament_lower:
        return 40
    
    if any(term in tournament_lower for term in ['world cup', 'euro', 'afcon', 'copa america', 'asian cup', 'confederations cup', 'olympics']):
        return 40
    
    # All other tournaments
    if any(term in tournament_lower for term in ['tournament', 'championship', 'league', 'cup']):
        return 30
    
    # Friendly matches (default)
    return 20

def adjust_k_for_goal_difference(k, goal_difference):
    """
    Adjust K based on goal difference.
    - Increased by half if a game is won by two goals
    - Increased by 3/4 if a game is won by three goals
    - Increased by 3/4 + (N-3)/8 if the game is won by four or more goals
    """
    if goal_difference <= 1:
        return k
    elif goal_difference == 2:
        return k * 1.5  # increased by half
    elif goal_difference == 3:
        return k * 1.75  # increased by 3/4
    else:
        # 3/4 + (N-3)/8 = 0.75 + (N-3)/8
        adjustment = 0.75 + (goal_difference - 3) / 8
        return k * (1 + adjustment)

def update_elo(rating_a, rating_b, home_score, away_score, exp_a, exp_b, k_factor):
    """
    Updates ratings using standard World Football Elo formulas.
    Rn = Ro + K × (W - We)
    
    K is adjusted for goal difference.
    """
    # Determine actual result (1 for win, 0.5 for draw, 0 for loss)
    if home_score > away_score:
        actual_a, actual_b = 1.0, 0.0
    elif home_score < away_score:
        actual_a, actual_b = 0.0, 1.0
    else:
        actual_a, actual_b = 0.5, 0.5
    
    # Calculate goal difference for K adjustment
    goal_diff = abs(home_score - away_score)
    adjusted_k = adjust_k_for_goal_difference(k_factor, goal_diff)
    
    # Update ratings
    new_rating_a = rating_a + adjusted_k * (actual_a - exp_a)
    new_rating_b = rating_b + adjusted_k * (actual_b - exp_b)
    
    return new_rating_a, new_rating_b

def update_utils_py_ratings(ratings, utils_py_path):
    """
    Updates the BASE_TEAM_RATINGS dictionary in fullsim.py with the new ratings.
    """
    if not os.path.exists(utils_py_path):
        print(f"Warning: {utils_py_path} not found. Skipping fullsim.py update.")
        return

    # Team name mapping: CSV_Name -> Main_Py_Name
    name_mapping = {
        "United States": "United States",
        "China PR": "China",
        "Republic of Ireland": "Ireland",
        "DR Congo": "Congo DR",
        "Saint Kitts and Nevis": "St. Kitts and Nevis",
        "Saint Lucia": "St. Lucia",
        "Réunion": "Reunion",
        "São Tomé and Príncipe": "Sao Tome and Principe",
        "Saint Vincent and the Grenadines": "St. Vincent / Grenadines",
        "Czech Republic": "Czech Republic",
        "South Korea": "South Korea",
        "North Korea": "North Korea"
    }

    # Apply mapping and keep as floats
    updated_ratings = {}
    for team, rating in ratings.items():
        mapped_name = name_mapping.get(team, team)
        updated_ratings[mapped_name] = float(rating)

    # Sort by rating descending
    sorted_updated = sorted(updated_ratings.items(), key=lambda x: x[1], reverse=True)

    # Read fullsim.py
    with open(utils_py_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generate new BASE_TEAM_RATINGS dictionary string
    dict_entries = []
    for team, rating in sorted_updated:
        # Format as float with 2 decimal places to preserve precision
        dict_entries.append(f"    '{team}': {round(rating, 2)},")
    
    new_dict_content = "BASE_TEAM_RATINGS = {\n" + "\n".join(dict_entries) + "\n}"

    # Use regex to find the BASE_TEAM_RATINGS block
    pattern = r"BASE_TEAM_RATINGS = \{.*?\}"
    new_content = re.sub(pattern, new_dict_content, content, flags=re.DOTALL)

    # Write back to fullsim.py
    with open(utils_py_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Successfully updated BASE_TEAM_RATINGS in {utils_py_path}")

def main():
    csv_file_path = 'sportsanalysis/worldcup26/results.csv'
    output_file_path = 'sportsanalysis/worldcup26/elo_ratings.txt'
    utils_py_path = 'sportsanalysis/worldcup26/fullsim.py'
    
    # Initialize team ratings
    ratings = {}
    
    # Home field advantage adjustment (100 points for team playing at home)
    HOME_ADVANTAGE = 100

    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                home_team = row['home_team']
                away_team = row['away_team']
                home_score = int(row['home_score'])
                away_score = int(row['away_score'])
                tournament = row['tournament']
                neutral = row['neutral'].strip().upper() == 'TRUE'
                
                # Initialize teams if not present
                if home_team not in ratings:
                    ratings[home_team] = 1500.0
                if away_team not in ratings:
                    ratings[away_team] = 1500.0
                
                r_home = ratings[home_team]
                r_away = ratings[away_team]
                
                # Apply home advantage if not neutral (add 100 points for home team)
                effective_r_home = r_home + (0 if neutral else HOME_ADVANTAGE)
                
                # Calculate expected scores
                exp_home = calculate_expected_score(effective_r_home, r_away)
                exp_away = calculate_expected_score(r_away, effective_r_home)
                
                # Get K-factor based on tournament type
                k_factor = get_k_factor(tournament)
                
                # Update ratings using standard World Football Elo formulas
                new_r_home, new_r_away = update_elo(
                    r_home, r_away, 
                    home_score, away_score, 
                    exp_home, exp_away, 
                    k_factor
                )
                ratings[home_team] = new_r_home
                ratings[away_team] = new_r_away
                
        # Sort ratings by score descending for the text file
        sorted_ratings = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
        
        # Print and write to file
        with open(output_file_path, 'w', encoding='utf-8') as out_file:
            header = f"{'Rank':<5} {'Team':<25} {'Elo Rating':<10}"
            # print(header) # Commented out to avoid cluttering terminal
            out_file.write(header + '\n')
            # print("-" * 40)
            out_file.write("-" * 40 + '\n')
            
            for i, (team, rating) in enumerate(sorted_ratings, 1):
                line = f"{i:<5} {team:<25} {rating:^10.2f}"
                out_file.write(line + '\n')
                
        print(f"Elo ratings successfully written to {output_file_path}")

        # Automatically update utils.py
        update_utils_py_ratings(ratings, utils_py_path)

    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
