import csv
from collections import defaultdict

def parse_schedule(csv_filename):
    """
    Reads the NFL schedule CSV and returns a dictionary mapping week number
    to a list of (home_team, away_team) tuples.
    """
    games_by_week = defaultdict(list)

    with open(csv_filename, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        # The first columns are 'Team' and 'Abbreviation', then Week 1..Week 18
        weeks = [f"Week {i}" for i in range(1, 19)]

        for row in reader:
            team_abbr = row['Abbreviation']
            for week in weeks:
                opponent_cell = row[week].strip()
                if not opponent_cell:
                    continue
                # If the cell starts with '@', this team is away; otherwise home
                if opponent_cell.startswith('@'):
                    away_team = team_abbr
                    home_team = opponent_cell[1:]  # remove '@'
                else:
                    home_team = team_abbr
                    away_team = opponent_cell

                # Store the game under the correct week
                games_by_week[week].append((home_team, away_team))

    return games_by_week

def main():
    # Parse the schedule
    games = parse_schedule(r"c:\Users\liam\Pictures\apple its glowtime\iPhone 16\NFL_2026_Schedule_Grid.csv")

    # Print games per week
    for week in sorted(games.keys(), key=lambda w: int(w.split()[1])):
        print(f"\n{week}:")
        for home, away in games[week]:
            print(f"  {home} vs {away}")

if __name__ == "__main__":
    main()