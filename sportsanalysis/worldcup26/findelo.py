import csv
import math
import re
import os

def calculate_expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def update_elo(rating_a, rating_b, home_score, away_score, exp_a, exp_b, k_factor=32):
    """
    Updates ratings for Team A and Team B based on the new goal-difference multiplier.
    G = ln(GD + 1) * (1 / (1 + |dR|/400)) * U
    """
    gd = abs(home_score - away_score)
    dr = abs(rating_a - rating_b)
    
    # Base actual results (1 for win, 0.5 for draw, 0 for loss)
    if home_score > away_score:
        actual_a, actual_b = 1.0, 0.0
    elif home_score < away_score:
        actual_a, actual_b = 0.0, 1.0
    else:
        actual_a, actual_b = 0.5, 0.5

    # 1. Base Goal-Difference Term (or fallback for draws)
    if gd == 0:
        g = 1.0
    else:
        g_gd = math.log(gd + 1)
        
        # 2. Expectation Adjustment Term
        d = dr / 400
        g_adj = 1 / (1 + d)
        
        # 3. Surprise Amplifier
        # Underdog wins if they had lower rating but higher score
        underdog_won_a = (rating_a < rating_b and home_score > away_score)
        underdog_won_b = (rating_b < rating_a and away_score > home_score)
        
        u = (1 + d) if (underdog_won_a or underdog_won_b) else 1.0
        
        # Final Multiplier
        g = g_gd * g_adj * u
        # Cap G at 2.5 for stability
        g = min(g, 2.5)

    new_rating_a = rating_a + k_factor * (actual_a - exp_a) * g
    new_rating_b = rating_b + k_factor * (actual_b - exp_b) * g
    
    return new_rating_a, new_rating_b

def update_utils_py_ratings(ratings, utils_py_path):
    """
    Updates the ELO_RATINGS dictionary in utils.py with the new ratings.
    """
    if not os.path.exists(utils_py_path):
        print(f"Warning: {utils_py_path} not found. Skipping utils.py update.")
        return

    # Team name mapping: CSV_Name -> Main_Py_Name
    name_mapping = {
        "United States": "USA",
        "China PR": "China",
        "Republic of Ireland": "Ireland",
        "DR Congo": "Congo DR",
        "Saint Kitts and Nevis": "St. Kitts and Nevis",
        "Saint Lucia": "St. Lucia",
        "Réunion": "Reunion",
        "São Tomé and Príncipe": "Sao Tome e Principe",
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

    # Read utils.py
    with open(utils_py_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generate new teams_ratings dictionary string
    dict_entries = []
    for team, rating in sorted_updated:
        # Format as float with 2 decimal places to preserve precision
        dict_entries.append(f"    '{team}': {round(rating, 2)},")
    
    new_dict_content = "teams_ratings = {\n" + "\n".join(dict_entries) + "\n}"

    # Use regex to find the teams_ratings block
    pattern = r"teams_ratings = \{.*?\}"
    new_content = re.sub(pattern, new_dict_content, content, flags=re.DOTALL)

    # Write back to fullsim.py
    with open(utils_py_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Successfully updated ELO_RATINGS in {utils_py_path}")

def main():
    csv_file_path = r'c:\Users\liam\Documents\GitHub\All-code-in-one\sportsanalysis\worldcup26\results.csv'
    output_file_path = r'c:\Users\liam\Documents\GitHub\All-code-in-one\sportsanalysis\worldcup26\elo_ratings.txt'
    utils_py_path = r'c:\Users\liam\Documents\GitHub\All-code-in-one\sportsanalysis\worldcup26\fullsim.py'
    
    # Initialize team ratings
    ratings = {}
    
    # K-factor can be adjusted based on tournament importance, but using 32 as a standard
    K = 32
    # Home field advantage adjustment (approx 100 points is common in football Elo)
    HOME_ADVANTAGE = 100

    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                home_team = row['home_team']
                away_team = row['away_team']
                home_score = int(row['home_score'])
                away_score = int(row['away_score'])
                neutral = row['neutral'].strip().upper() == 'TRUE'
                
                # Initialize teams if not present
                if home_team not in ratings:
                    ratings[home_team] = 1500.0
                if away_team not in ratings:
                    ratings[away_team] = 1500.0
                
                r_home = ratings[home_team]
                r_away = ratings[away_team]
                
                # Apply home advantage if not neutral
                effective_r_home = r_home + (0 if neutral else HOME_ADVANTAGE)
                
                # Calculate expected scores
                exp_home = calculate_expected_score(effective_r_home, r_away)
                exp_away = calculate_expected_score(r_away, effective_r_home)
                
                # Update ratings using the new complex multiplier
                new_r_home, new_r_away = update_elo(
                    r_home, r_away, 
                    home_score, away_score, 
                    exp_home, exp_away, 
                    K
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
