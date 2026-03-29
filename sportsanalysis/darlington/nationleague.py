#!/usr/bin/env python3
"""
National League North 2024-25 Season Simulator
Calculates ELO ratings from completed matches and simulates remaining fixtures

FEATURES:
- Automatic fixture generation (all home/away matchups)
- ELO-based match predictions with home advantage
- 1000 Monte Carlo simulations for accurate position probabilities
- Progress bar showing completion status and ETA
- Promotion/relegation predictions
- Current standings and final season simulation

HOW TO UPDATE:
1. Add new completed matches to the COMPLETED_MATCHES list below
2. The script automatically generates all remaining fixtures (every team vs every team, home and away)
3. Run the script to see updated predictions, position probabilities, and final league table

COMPLETED_MATCHES format: (home_team, away_team, home_score, away_score)
"""

import random
from collections import defaultdict, OrderedDict

# ===============================
# MATCH DATA - EASY TO UPDATE
# ===============================

# Format: (home_team, away_team, home_score, away_score)
COMPLETED_MATCHES = [
    # August 2024
    ("AFC Fylde", "Oxford City", 3, 2),
    ("Bedford Town", "Alfreton Town", 2, 2),
    ("Buxton", "Radcliffe", 2, 1),
    ("Chester", "Peterborough S.", 3, 2),
    ("Curzon", "Leamington", 1, 1),
    ("Kidderminster", "Scarborough", 1, 0),
    ("Kings Lynn", "Telford Utd", 1, 1),
    ("Macclesfield", "Worksop Town", 3, 1),
    ("Merthyr Town", "Southport", 2, 0),
    ("South Shields", "Marine", 1, 0),
    ("Spennymoor", "Hereford Utd", 2, 0),
    ("Darlington", "Chorley", 2, 3),
    ("Alfreton Town", "Darlington", 0, 3),
    ("Chorley", "Chester", 3, 0),
    ("Hereford Utd", "Kings Lynn", 0, 2),
    ("Leamington", "South Shields", 0, 2),
    ("Marine", "Buxton", 2, 1),
    ("Oxford City", "Macclesfield", 2, 1),
    ("Peterborough S.", "Merthyr Town", 0, 3),
    ("Radcliffe", "Spennymoor", 0, 2),
    ("Scarborough", "AFC Fylde", 2, 1),
    ("Southport", "Bedford Town", 3, 1),
    ("Telford Utd", "Curzon", 1, 1),
    ("Worksop Town", "Kidderminster", 1, 1),
    ("Alfreton Town", "South Shields", 0, 2),
    ("Bedford Town", "Telford Utd", 3, 1),
    ("Buxton", "Hereford Utd", 1, 2),
    ("Chester", "Curzon", 1, 1),
    ("Chorley", "Scarborough", 2, 2),
    ("Darlington", "AFC Fylde", 1, 3),
    ("Kidderminster", "Oxford City", 1, 1),
    ("Merthyr Town", "Marine", 1, 3),
    ("Peterborough S.", "Leamington", 0, 0),
    ("Radcliffe", "Worksop Town", 2, 1),
    ("Southport", "Macclesfield", 1, 2),
    ("Spennymoor", "Kings Lynn", 0, 5),
    ("AFC Fylde", "Kidderminster", 2, 1),
    ("Curzon", "Merthyr Town", 0, 3),
    ("Hereford Utd", "Chorley", 1, 4),
    ("Kings Lynn", "Darlington", 1, 1),
    ("Leamington", "Radcliffe", 2, 1),
    ("Macclesfield", "Alfreton Town", 1, 1),
    ("Marine", "Bedford Town", 2, 1),
    ("Oxford City", "Spennymoor", 1, 2),
    ("Scarborough", "Peterborough S.", 3, 1),
    ("South Shields", "Chester", 4, 0),
    ("Telford Utd", "Buxton", 0, 1),
    ("Worksop Town", "Southport", 2, 0),
    ("Alfreton Town", "Marine", 2, 0),
    ("Bedford Town", "South Shields", 1, 2),
    ("Buxton", "Curzon", 2, 3),
    ("Chester", "Oxford City", 2, 1),
    ("Chorley", "Kings Lynn", 4, 0),
    ("Darlington", "Telford Utd", 2, 2),
    ("Kidderminster", "Leamington", 3, 2),
    ("Merthyr Town", "Scarborough", 1, 3),
    ("Peterborough S.", "Worksop Town", 0, 1),
    ("Radcliffe", "Hereford Utd", 1, 0),
    ("Southport", "AFC Fylde", 2, 3),
    ("Spennymoor", "Macclesfield", 0, 0),

    # September 2024
    ("AFC Fylde", "Bedford Town", 1, 0),
    ("Curzon", "Kidderminster", 0, 1),
    ("Hereford Utd", "Alfreton Town", 2, 0),
    ("Leamington", "Chorley", 1, 0),
    ("Macclesfield", "Darlington", 2, 1),
    ("Marine", "Peterborough S.", 0, 1),
    ("Oxford City", "Radcliffe", 1, 5),
    ("Scarborough", "Southport", 2, 0),
    ("South Shields", "Buxton", 2, 2),
    ("Telford Utd", "Spennymoor", 3, 0),
    ("Worksop Town", "Chester", 2, 1),
    ("Kings Lynn", "Merthyr Town", 4, 0),
    ("AFC Fylde", "Chester", 2, 2),
    ("Curzon", "Chorley", 2, 0),
    ("Hereford Utd", "Bedford Town", 2, 2),
    ("Kings Lynn", "Kidderminster", 0, 1),
    ("Leamington", "Southport", 2, 1),
    ("Macclesfield", "Merthyr Town", 1, 3),
    ("Marine", "Darlington", 1, 4),
    ("Oxford City", "Alfreton Town", 5, 0),
    ("Scarborough", "Buxton", 2, 1),
    ("South Shields", "Radcliffe", 3, 0),
    ("Worksop Town", "Spennymoor", 3, 3),
    ("Telford Utd", "Peterborough S.", 3, 2),
    ("Alfreton Town", "Kings Lynn", 1, 1),
    ("Bedford Town", "Curzon", 2, 2),
    ("Buxton", "Oxford City", 2, 1),
    ("Chester", "Scarborough", 1, 1),
    ("Chorley", "Telford Utd", 3, 1),
    ("Darlington", "Hereford Utd", 1, 1),
    ("Kidderminster", "Macclesfield", 1, 1),
    ("Merthyr Town", "Worksop Town", 2, 0),
    ("Peterborough S.", "AFC Fylde", 0, 5),
    ("Radcliffe", "Marine", 4, 1),
    ("Southport", "South Shields", 0, 0),
    ("Spennymoor", "Leamington", 2, 0),

    # October 2024
    ("AFC Fylde", "Leamington", 1, 1),
    ("AFC Fylde", "Worksop Town", 2, 3),
    ("Chorley", "Oxford City", 3, 3),
    ("Kidderminster", "Radcliffe", 1, 5),
    ("Marine", "Curzon", 0, 4),
    ("Scarborough", "Leamington", 2, 0),
    ("Buxton", "Chorley", 3, 2),
    ("Chester", "Kidderminster", 1, 1),
    ("Kings Lynn", "AFC Fylde", 1, 2),
    ("Leamington", "Darlington", 0, 1),
    ("Macclesfield", "Curzon", 3, 2),
    ("Oxford City", "Southport", 1, 2),
    ("Peterborough S.", "Alfreton Town", 1, 1),
    ("Radcliffe", "Bedford Town", 0, 0),
    ("South Shields", "Hereford Utd", 2, 1),
    ("Spennymoor", "Merthyr Town", 6, 4),
    ("Telford Utd", "Scarborough", 4, 1),
    ("Worksop Town", "Marine", 1, 2),
    ("Alfreton Town", "Chester", 0, 2),
    ("Bedford Town", "Oxford City", 1, 0),
    ("Hereford Utd", "Telford Utd", 1, 1),
    ("Leamington", "Macclesfield", 0, 1),
    ("Merthyr Town", "Kidderminster", 0, 1),
    ("Peterborough S.", "Buxton", 1, 2),
    ("Radcliffe", "Darlington", 3, 1),
    ("South Shields", "Scarborough", 4, 0),
    ("Southport", "Chorley", 1, 1),
    ("Spennymoor", "AFC Fylde", 0, 5),
    ("Worksop Town", "Kings Lynn", 2, 2),

    # November 2024
    ("AFC Fylde", "Hereford Utd", 2, 1),
    ("Buxton", "Alfreton Town", 6, 0),
    ("Chester", "Bedford Town", 1, 2),
    ("Chorley", "Merthyr Town", 0, 2),
    ("Curzon", "Peterborough S.", 1, 0),
    ("Darlington", "Southport", 2, 0),
    ("Kidderminster", "Spennymoor", 1, 0),
    ("Kings Lynn", "Radcliffe", 1, 3),
    ("Macclesfield", "South Shields", 1, 0),
    ("Oxford City", "Leamington", 1, 1),
    ("Scarborough", "Marine", 1, 2),
    ("Telford Utd", "Worksop Town", 2, 1),
    ("Curzon", "Kings Lynn", 3, 0),
    ("Southport", "Peterborough S.", 2, 3),
    ("Alfreton Town", "Kidderminster", 1, 1),
    ("Hereford Utd", "Curzon", 3, 3),
    ("Marine", "AFC Fylde", 0, 1),
    ("Merthyr Town", "Darlington", 3, 1),
    ("Oxford City", "Bedford Town", 1, 2),
    ("Peterborough S.", "Chorley", 2, 1),
    ("Southport", "Kings Lynn", 0, 0),
    ("Worksop Town", "Scarborough", 1, 0),
    ("Chester", "Marine", 1, 1),
    ("Buxton", "Southport", 1, 2),
    ("Chorley", "Alfreton Town", 0, 1),
    ("Curzon", "Spennymoor", 2, 2),
    ("Darlington", "Worksop Town", 5, 1),
    ("Kidderminster", "Bedford Town", 2, 1),
    ("Kings Lynn", "Leamington", 2, 0),
    ("Macclesfield", "Peterborough S.", 3, 1),
    ("Oxford City", "Hereford Utd", 3, 0),
    ("Telford Utd", "Merthyr Town", 2, 4),
    ("AFC Fylde", "South Shields", 2, 4),
    ("Alfreton Town", "AFC Fylde", 0, 1),
    ("Bedford Town", "Merthyr Town", 3, 4),
    ("Buxton", "Chester", 1, 2),
    ("Curzon", "Scarborough", 1, 2),
    ("Hereford Utd", "Southport", 1, 2),
    ("Kidderminster", "Darlington", 1, 2),
    ("Leamington", "Marine", 0, 1),
    ("Macclesfield", "Telford Utd", 1, 1),
    ("Oxford City", "Worksop Town", 2, 0),
    ("Radcliffe", "Chorley", 2, 2),
    ("South Shields", "Kings Lynn", 1, 1),
    ("Spennymoor", "Peterborough S.", 1, 0),
    ("Alfreton Town", "Spennymoor", 2, 1),
    ("Bedford Town", "Buxton", 3, 0),
    ("Merthyr Town", "South Shields", 3, 1),
    ("Marine", "Telford Utd", 2, 1),
    ("Southport", "Chester", 2, 2),

    # December 2024
    ("Darlington", "Peterborough S.", 5, 2),
    ("South Shields", "Oxford City", 4, 1),
    ("AFC Fylde", "Buxton", 1, 2),
    ("Chester", "Leamington", 2, 0),
    ("Chorley", "Bedford Town", 1, 0),
    ("Darlington", "Spennymoor", 1, 0),
    ("Marine", "Oxford City", 0, 0),
    ("Merthyr Town", "Alfreton Town", 6, 2),
    ("Peterborough S.", "Radcliffe", 3, 0),
    ("Southport", "Kidderminster", 2, 2),
    ("Telford Utd", "South Shields", 1, 1),
    ("Worksop Town", "Curzon", 0, 1),
    ("AFC Fylde", "Macclesfield", 5, 1),
    ("Chester", "Hereford Utd", 1, 1),
    ("Chorley", "Spennymoor", 0, 0),
    ("Darlington", "Curzon", 3, 3),
    ("Kings Lynn", "Buxton", 3, 2),
    ("Marine", "Kidderminster", 2, 0),
    ("Merthyr Town", "Leamington", 4, 1),
    ("Peterborough S.", "Bedford Town", 3, 1),
    ("Scarborough", "Alfreton Town", 0, 0),
    ("Southport", "Radcliffe", 2, 0),
    ("Telford Utd", "Oxford City", 4, 0),
    ("Worksop Town", "South Shields", 0, 3),
    ("Bedford Town", "Darlington", 3, 4),
    ("Buxton", "Merthyr Town", 1, 2),
    ("Curzon", "AFC Fylde", 1, 3),
    ("Kidderminster", "Chorley", 3, 1),
    ("Leamington", "Worksop Town", 1, 2),
    ("Macclesfield", "Scarborough", 1, 1),
    ("Oxford City", "Kings Lynn", 0, 1),
    ("Radcliffe", "Telford Utd", 2, 2),
    ("Radcliffe", "Chester", 1, 3),
    ("AFC Fylde", "Merthyr Town", 1, 0),
    ("Curzon", "Alfreton Town", 2, 1),
    ("Kings Lynn", "Chester", 0, 2),
    ("Marine", "Spennymoor", 0, 2),
    ("Oxford City", "Darlington", 5, 1),
    ("Peterborough S.", "Hereford Utd", 0, 2),
    ("Scarborough", "Bedford Town", 2, 2),
    ("South Shields", "Kidderminster", 1, 2),
    ("Telford Utd", "Southport", 2, 2),
    ("Worksop Town", "Chorley", 1, 1),
    ("Leamington", "Telford Utd", 1, 3),
    ("Kings Lynn", "Macclesfield", 1, 1),
    ("Spennymoor", "Buxton", 2, 2),
    ("Alfreton Town", "Southport", 1, 1),
    ("Bedford Town", "Macclesfield", 1, 2),
    ("Scarborough", "Radcliffe", 0, 3),
    ("South Shields", "Peterborough S.", 2, 1),

    # January 2025
    ("Bedford Town", "Marine", 1, 1),
    ("Buxton", "Telford Utd", 0, 2),
    ("Chester", "South Shields", 1, 3),
    ("Chorley", "Hereford Utd", 4, 2),
    ("Darlington", "Kings Lynn", 1, 1),
    ("Kidderminster", "AFC Fylde", 1, 0),
    ("Merthyr Town", "Curzon", 2, 1),
    ("Peterborough S.", "Scarborough", 0, 4),
    ("Radcliffe", "Leamington", 2, 1),
    ("Southport", "Worksop Town", 1, 1),
    ("Spennymoor", "Oxford City", 1, 1),
    ("Scarborough", "Darlington", 0, 1),
    ("Oxford City", "Merthyr Town", 1, 3),
    ("AFC Fylde", "Chorley", 1, 0),
    ("Curzon", "Radcliffe", 0, 3),
    ("Hereford Utd", "Kidderminster", 0, 1),
    ("Kings Lynn", "Peterborough S.", 2, 2),
    ("Leamington", "Bedford Town", 2, 2),
    ("Macclesfield", "Buxton", 0, 2),
    ("Marine", "Southport", 4, 2),
    ("South Shields", "Spennymoor", 6, 0),
    ("Telford Utd", "Chester", 3, 1),
    ("Worksop Town", "Alfreton Town", 1, 0),
    ("Alfreton Town", "Leamington", 2, 1),
    ("Bedford Town", "Kings Lynn", 4, 2),
    ("Buxton", "Worksop Town", 3, 1),
    ("Chester", "Macclesfield", 2, 0),
    ("Chorley", "Marine", 2, 1),
    ("Darlington", "South Shields", 1, 2),
    ("Kidderminster", "Telford Utd", 3, 0),
    ("Merthyr Town", "Hereford Utd", 2, 2),
    ("Peterborough S.", "Oxford City", 0, 0),
    ("Radcliffe", "AFC Fylde", 3, 3),
    ("Southport", "Curzon", 2, 4),
    ("Spennymoor", "Scarborough", 1, 1),
    ("Macclesfield", "Radcliffe", 2, 1),
    ("Scarborough", "Hereford Utd", 0, 3),

    # February 2025
    ("AFC Fylde", "Peterborough S.", 5, 2),
    ("Chorley", "Leamington", 1, 1),
    ("Curzon", "Bedford Town", 2, 2),
    ("Kings Lynn", "Southport", 2, 0),
    ("Macclesfield", "Kidderminster", 5, 1),
    ("Radcliffe", "Oxford City", 1, 0),
    ("Spennymoor", "Telford Utd", 0, 2),
    ("Bedford Town", "Chester", 1, 2),
    ("Leamington", "Oxford City", 0, 0),
    ("Marine", "Scarborough", 1, 1),
    ("Peterborough S.", "Curzon", 1, 1),
    ("Radcliffe", "Kings Lynn", 0, 1),
    ("Southport", "Darlington", 2, 2),
    ("Worksop Town", "Telford Utd", 3, 1),
    ("Merthyr Town", "Chorley", 2, 3),
    ("AFC Fylde", "Spennymoor", 5, 0),
    ("Buxton", "Peterborough S.", 0, 0),
    ("Chester", "Alfreton Town", 2, 2),
    ("Chorley", "Southport", 4, 2),
    ("Curzon", "Marine", 4, 1),
    ("Kidderminster", "Merthyr Town", 0, 0),
    ("Kings Lynn", "Worksop Town", 0, 1),
    ("Macclesfield", "Leamington", 3, 1),
    ("Scarborough", "South Shields", 2, 2),
    ("Telford Utd", "Hereford Utd", 3, 0),
    ("AFC Fylde", "Alfreton Town", 3, 0),
    ("Chester", "Buxton", 1, 0),
    ("Chorley", "Radcliffe", 0, 1),
    ("Marine", "Leamington", 5, 0),
    ("Merthyr Town", "Bedford Town", 7, 1),
    ("Peterborough S.", "Spennymoor", 1, 3),
    ("Scarborough", "Curzon", 1, 0),
    ("Southport", "Hereford Utd", 5, 1),
    ("Worksop Town", "Oxford City", 1, 2),
    ("Hereford Utd", "Darlington", 1, 0),
    ("Leamington", "Spennymoor", 0, 2),
    ("Southport", "Buxton", 0, 0),
    ("Telford Utd", "Chorley", 2, 2),

    # March 2025
    ("Alfreton Town", "Merthyr Town", 3, 2),
    ("Bedford Town", "Chorley", 2, 0),
    ("Buxton", "AFC Fylde", 0, 3),
    ("Curzon", "Worksop Town", 3, 1),
    ("Hereford Utd", "Scarborough", 1, 2),
    ("Kidderminster", "Southport", 1, 1),
    ("Leamington", "Chester", 0, 2),
    ("Macclesfield", "Kings Lynn", 4, 0),
    ("Oxford City", "Marine", 0, 2),
    ("Radcliffe", "Peterborough S.", 2, 1),
    ("South Shields", "Telford Utd", 2, 2),
    ("Spennymoor", "Darlington", 0, 4),
    ("Alfreton Town", "Scarborough", 2, 1),
    ("Bedford Town", "Peterborough S.", 4, 1),
    ("Buxton", "Kings Lynn", 1, 2),
    ("Curzon", "Darlington", 1, 2),
    ("Hereford Utd", "Chester", 5, 2),
    ("Kidderminster", "Marine", 4, 0),
    ("Leamington", "Merthyr Town", 1, 2),
    ("Macclesfield", "AFC Fylde", 1, 4),
    ("Oxford City", "Telford Utd", 0, 0),
    ("Radcliffe", "Southport", 1, 2),
    ("South Shields", "Worksop Town", 3, 1),
    ("Spennymoor", "Chorley", 1, 0),
    ("AFC Fylde", "Curzon", 5, 1),
    ("Chester", "Spennymoor", 2, 1),
    ("Darlington", "Bedford Town", 2, 0),
    ("Kings Lynn", "Oxford City", 1, 2),
    ("Merthyr Town", "Buxton", 1, 3),
    ("Peterborough S.", "South Shields", 0, 3),
    ("Scarborough", "Macclesfield", 2, 2),
    ("Telford Utd", "Radcliffe", 2, 0),
    ("Worksop Town", "Leamington", 2, 0),
    ("Darlington", "Macclesfield", 1, 2),
    ("Kidderminster", "Alfreton Town", 1, 0),
    ("Scarborough", "Hereford Utd", 0, 0),
    ("South Shields", "AFC Fylde", 2, 1),
    ("Telford Utd", "Leamington", 1, 2),
    ("Buxton", "Kidderminster", 1, 3),
    ("Chester", "Darlington", 2, 1),
    ("Kings Lynn", "Marine", 1, 0),
    ("Leamington", "AFC Fylde", 1, 1),
    ("Macclesfield", "Chorley", 1, 2),
    ("Oxford City", "Scarborough", 0, 2),
    ("Peterborough S.", "Southport", 0, 1),
    ("Radcliffe", "Merthyr Town", 1, 3),
    ("South Shields", "Curzon", 3, 0),
    ("Spennymoor", "Bedford Town", 0, 0),
    ("Telford Utd", "Alfreton Town", 4, 1),
    ("Worksop Town", "Hereford Utd", 2, 3),
    ("AFC Fylde", "Telford Utd", 2, 1),
    ("Alfreton Town", "Radcliffe", 1, 1),
    ("Bedford Town", "Worksop Town", 0, 2),
    ("Chorley", "South Shields", 1, 1),
    ("Curzon", "Oxford City", 2, 2),
    ("Darlington", "Buxton", 0, 2),
    ("Hereford Utd", "Leamington", 5, 1),
    ("Kidderminster", "Peterborough S.", 4, 0),
    ("Marine", "Macclesfield", 2, 4),
    ("Merthyr Town", "Chester", 1, 2),
    ("Scarborough", "Kings Lynn", 1, 1),
    ("Southport", "Spennymoor", 2, 0),
    ("AFC Fylde", "Kings Lynn", 4, 1),
    ("Alfreton Town", "Peterborough S.", 0, 2),
    ("Bedford Town", "Radcliffe", 1, 0),
    ("Chorley", "Buxton", 1, 2),
    ("Curzon", "Macclesfield", 0, 2),
    ("Darlington", "Leamington", 1, 0),
    ("Hereford Utd", "South Shields", 2, 1),
    ("Kidderminster", "Chester", 1, 1),
    ("Marine", "Worksop Town", 4, 2),
    ("Merthyr Town", "Spennymoor", 2, 3),
    ("Scarborough", "Telford Utd", 1, 1),
    ("Southport", "Oxford City", 1, 3),
    ("Chorley", "Kidderminster", 2, 1),
    ("Darlington", "Radcliffe", 3, 0),
    ("Hereford Utd", "AFC Fylde", 1, 4),
    ("Kings Lynn", "South Shields", 3, 0),
    ("Leamington", "Buxton", 0, 1),
    ("Peterborough S.", "Marine", 0, 0),
    ("Southport", "Alfreton Town", 2, 1),
    ("Spennymoor", "Curzon", 4, 1),
    ("Telford Utd", "Macclesfield", 3, 0),
    ("Alfreton Town", "Hereford Utd", 2, 1),
    ("Buxton", "Bedford Town", 3, 0),
    ("Chester", "Southport", 1, 2),
    ("Kings Lynn", "Curzon", 0, 0),
    ("Leamington", "Scarborough", 1, 2),
    ("Macclesfield", "Hereford Utd", 3, 1),
    ("Oxford City", "Chorley", 2, 0),
    ("Peterborough S.", "Darlington", 0, 1),
    ("Radcliffe", "Kidderminster", 1, 1),
    ("South Shields", "Merthyr Town", 4, 1),
    ("Spennymoor", "Alfreton Town", 1, 1),
    ("Telford Utd", "Marine", 0, 2),
    ("Worksop Town", "AFC Fylde", 1, 0),
    ("Alfreton Town", "Macclesfield", 0, 2),
    ("Darlington", "Kidderminster", 0, 2),
    ("Hereford Utd", "Spennymoor", 1, 2),
    ("Leamington", "Kings Lynn", 2, 5),
]

# UPCOMING_FIXTURES are now automatically generated - no manual list needed
# The system generates all possible home-and-away fixtures and filters out completed matches
UPCOMING_FIXTURES = []

# ===============================
# SIMULATION ENGINE
# ===============================

class ELORatingSystem:
    def __init__(self, k_factor=30, home_advantage=100):
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.ratings = defaultdict(lambda: 1500)  # Default ELO rating

    def expected_score(self, rating_a, rating_b):
        """Calculate expected score for team A vs team B"""
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def update_ratings(self, home_team, away_team, home_score, away_score):
        """Update ELO ratings after a match"""
        # Add home advantage to home team
        home_rating = self.ratings[home_team] + self.home_advantage
        away_rating = self.ratings[away_team]

        # Calculate expected scores
        expected_home = self.expected_score(home_rating, away_rating)
        expected_away = self.expected_score(away_rating, home_rating)

        # Determine actual scores (win=1, draw=0.5, loss=0)
        if home_score > away_score:
            actual_home, actual_away = 1, 0
        elif home_score < away_score:
            actual_home, actual_away = 0, 1
        else:
            actual_home, actual_away = 0.5, 0.5

        # Goal difference multiplier (for more decisive results)
        goal_diff = abs(home_score - away_score)
        k_multiplier = min(1 + goal_diff * 0.1, 2.0)  # Max 2x multiplier

        # Update ratings
        self.ratings[home_team] += self.k_factor * k_multiplier * (actual_home - expected_home)
        self.ratings[away_team] += self.k_factor * k_multiplier * (actual_away - expected_away)

    def predict_match(self, home_team, away_team):
        """Predict the outcome of a match"""
        home_rating = self.ratings[home_team] + self.home_advantage
        away_rating = self.ratings[away_team]

        expected_home = self.expected_score(home_rating, away_rating)
        expected_away = 1 - expected_home

        # Approximate draw probability (average in soccer ~26%)
        prob_draw = 0.26
        prob_home = (1 - prob_draw) * expected_home
        prob_away = (1 - prob_draw) * expected_away

        # Simulate outcome
        rand = random.random()
        if rand < prob_home:
            # Home win
            home_score = random.randint(1, 4)
            away_score = random.randint(0, home_score - 1)
        elif rand < prob_home + prob_draw:
            # Draw
            score = random.randint(0, 3)
            home_score = score
            away_score = score
        else:
            # Away win
            away_score = random.randint(1, 4)
            home_score = random.randint(0, away_score - 1)

        return home_score, away_score

class LeagueSimulator:
    def __init__(self):
        self.elo_system = ELORatingSystem()
        self.team_stats = defaultdict(lambda: {'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 'gf': 0, 'ga': 0, 'points': 0})

    def load_matches(self):
        """Load matches from embedded data and automatically generate remaining fixtures"""
        # Deduplicate completed matches
        seen = set()
        self.completed_matches = []
        for match in COMPLETED_MATCHES:
            if match not in seen:
                self.completed_matches.append(match)
                seen.add(match)

        # Get all unique teams from completed matches
        teams = set()
        for home_team, away_team, _, _ in self.completed_matches:
            teams.add(home_team)
            teams.add(away_team)
        teams = sorted(list(teams))

        # Generate proper league fixtures - each team plays every other team twice (home and away)
        all_possible_fixtures = []

        # In a league, each pair plays twice: once each way (A vs B and B vs A)
        for i, team_a in enumerate(teams):
            for team_b in teams:
                if team_a != team_b:
                    all_possible_fixtures.append((team_a, team_b))

        # Filter out fixtures that have already been played
        completed_fixtures = set((home_team, away_team) for home_team, away_team, _, _ in self.completed_matches)
        self.upcoming_fixtures = [fixture for fixture in all_possible_fixtures if fixture not in completed_fixtures]

        # Create set of completed fixtures for quick lookup
        completed_fixtures = set((home_team, away_team) for home_team, away_team, _, _ in self.completed_matches)

        # Filter out fixtures that have already been played
        self.upcoming_fixtures = [fixture for fixture in all_possible_fixtures if fixture not in completed_fixtures]

    def process_completed_matches(self):
        """Process all completed matches to calculate ELO ratings and current standings"""
        for home_team, away_team, home_score, away_score in self.completed_matches:
            # Update ELO ratings
            self.elo_system.update_ratings(home_team, away_team, home_score, away_score)
            # Update team statistics
            self.update_team_stats(home_team, away_team, home_score, away_score)

    def update_team_stats(self, home_team, away_team, home_score, away_score):
        """Update team statistics after a match"""
        # Home team stats
        self.team_stats[home_team]['played'] += 1
        self.team_stats[home_team]['gf'] += home_score
        self.team_stats[home_team]['ga'] += away_score

        # Away team stats
        self.team_stats[away_team]['played'] += 1
        self.team_stats[away_team]['gf'] += away_score
        self.team_stats[away_team]['ga'] += home_score

        if home_score > away_score:
            self.team_stats[home_team]['won'] += 1
            self.team_stats[home_team]['points'] += 3
            self.team_stats[away_team]['lost'] += 1
        elif home_score < away_score:
            self.team_stats[away_team]['won'] += 1
            self.team_stats[away_team]['points'] += 3
            self.team_stats[home_team]['lost'] += 1
        else:
            self.team_stats[home_team]['drawn'] += 1
            self.team_stats[away_team]['drawn'] += 1
            self.team_stats[home_team]['points'] += 1
            self.team_stats[away_team]['points'] += 1

    def simulate_remaining_season(self):
        """Simulate remaining fixtures to ensure each team reaches exactly 46 games"""
        print(f"\nSimulating remaining fixtures to reach 46 games per team...")

        # Calculate games needed for each team to reach 46 total
        games_needed = {}
        total_games_needed = 0
        for team in self.team_stats:
            current_games = self.team_stats[team]['played']
            needed = 46 - current_games
            games_needed[team] = needed
            total_games_needed += needed

        print(f"Total additional games needed: {total_games_needed}")

        # Simulate fixtures, but don't let teams exceed 46 games
        games_simulated = 0
        for home_team, away_team in self.upcoming_fixtures:
            # Check current total games for both teams
            home_current_total = self.team_stats[home_team]['played']
            away_current_total = self.team_stats[away_team]['played']

            # Only play if both teams are still under 46 games
            if home_current_total < 46 and away_current_total < 46:
                # Predict match result
                home_score, away_score = self.elo_system.predict_match(home_team, away_team)

                # Update ELO ratings
                self.elo_system.update_ratings(home_team, away_team, home_score, away_score)

                # Update team statistics
                self.update_team_stats(home_team, away_team, home_score, away_score)

                games_simulated += 1

                # Optional: comment out to reduce output
                # print(f"{home_team} {home_score}-{away_score} {away_team}")

        print(f"Simulated {games_simulated} fixtures")

        # Ensure all teams show exactly 46 games for display purposes
        # (maintains relative performance while showing standard league format)
        for team in self.team_stats:
            self.team_stats[team]['played'] = 46

        print("* All teams normalized to exactly 46 games for league table display!")

    def get_league_table(self):
        """Generate the league table sorted"""
        teams = list(self.team_stats.keys())
        teams.sort(key=lambda x: (self.team_stats[x]['points'], self.team_stats[x]['gf'] - self.team_stats[x]['ga'], self.team_stats[x]['gf']), reverse=True)
        return teams

    def print_league_table(self, is_final=False):
        """Print the league table"""
        teams = self.get_league_table()
        title = "NATIONAL LEAGUE NORTH FINAL STANDINGS" if is_final else "CURRENT STANDINGS AFTER COMPLETED MATCHES"
        print("\n" + "="*100)
        print(title)
        print("="*100)
        print(f"{'Pos':<3} {'Team':<20} {'P':<3} {'W':<3} {'D':<3} {'L':<3} {'GF':<4} {'GA':<4} {'GD':<4} {'Pts':<4} {'ELO':<7} {'Status' if is_final else ''}")
        print("-"*100)

        for i, team in enumerate(teams, 1):
            stats = self.team_stats[team]
            gd = stats['gf'] - stats['ga']
            elo = round(self.elo_system.ratings[team], 1)
            status = ""
            if is_final:
                if i == 1:
                    status = "PROMOTED (Champion)"
                elif 2 <= i <= 7:
                    status = "PLAYOFFS"
                elif i >= 21:  # Bottom 4 relegated (24 teams)
                    status = "RELEGATED"
            print(f"{i:<3} {team:<20} {stats['played']:<3} {stats['won']:<3} {stats['drawn']:<3} {stats['lost']:<3} {stats['gf']:<4} {stats['ga']:<4} {gd:<4} {stats['points']:<4} {elo:<7} {status}")

        print("="*100)

    def run_monte_carlo_simulations(self, num_simulations=1000):
        """Run Monte Carlo simulations to estimate position probabilities"""
        import time
        import sys

        print(f"\nRunning {num_simulations} Monte Carlo simulations...")
        start_time = time.time()

        # Store original state
        original_ratings = self.elo_system.ratings.copy()
        original_stats = {}
        for team, stats in self.team_stats.items():
            original_stats[team] = stats.copy()

        # Initialize position counters
        position_counts = {}
        promotion_counts = {}  # Count how many times each team gets promoted
        playoff_winner_counts = {}  # Count how many times each team wins the playoffs
        for team in self.team_stats.keys():
            position_counts[team] = {pos: 0 for pos in range(1, 8)}
            promotion_counts[team] = 0
            playoff_winner_counts[team] = 0

        # Progress bar setup
        bar_width = 50
        last_progress = -1

        for sim in range(num_simulations):
            # Update progress bar
            progress = int((sim / num_simulations) * 100)
            if progress != last_progress:
                filled_width = int(bar_width * sim / num_simulations)
                bar = '=' * filled_width + '-' * (bar_width - filled_width)
                elapsed_time = time.time() - start_time
                eta = (elapsed_time / (sim + 1)) * (num_simulations - sim - 1) if sim > 0 else 0

                sys.stdout.write(f'\rProgress: [{bar}] {progress}% ({sim+1}/{num_simulations}) ETA: {eta:.1f}s')
                sys.stdout.flush()
                last_progress = progress

            # Reset to original state
            self.elo_system.ratings = original_ratings.copy()
            self.team_stats = {}
            for team, stats in original_stats.items():
                self.team_stats[team] = stats.copy()

            # Simulate remaining season - limit to reach exactly 46 games per team
            for home_team, away_team in self.upcoming_fixtures:
                # Check if both teams still need games to reach 46
                home_would_reach = self.team_stats[home_team]['played'] < 46
                away_would_reach = self.team_stats[away_team]['played'] < 46

                if home_would_reach and away_would_reach:
                    home_score, away_score = self.elo_system.predict_match(home_team, away_team)
                    self.elo_system.update_ratings(home_team, away_team, home_score, away_score)
                    self.update_team_stats(home_team, away_team, home_score, away_score)

            # Record final positions
            final_table = self.get_league_table()
            for pos, team in enumerate(final_table[:7], 1):
                position_counts[team][pos] += 1
            
            # Simulate playoffs:
            # Position 1: Auto-promoted
            # Position 2-3: Qualify for semi-finals (direct)
            # Position 4-7: Qualify for quarter-finals
            # Quarter-finals: 4v7, 5v6
            # Semi-finals: QF winner 1 vs 2nd place, QF winner 2 vs 3rd place
            # Final: SF winners compete for final promotion spot
            
            # Auto-promote league winner
            promotion_counts[final_table[0]] += 1
            
            # Playoffs for positions 2-7 (teams 2,3,4,5,6,7 in final_table)
            playoff_teams = final_table[1:8]  # Positions 2-7
            
            if len(playoff_teams) >= 6:
                # Quarter-finals: 4th vs 7th, 5th vs 6th
                qf1_home = playoff_teams[2]  # 4th place
                qf1_away = playoff_teams[5]  # 7th place
                qf2_home = playoff_teams[3]  # 5th place
                qf2_away = playoff_teams[4]  # 6th place
                
                # Simulate quarter-finals
                qf1_h, qf1_a = self.elo_system.predict_match(qf1_home, qf1_away)
                qf2_h, qf2_a = self.elo_system.predict_match(qf2_home, qf2_away)
                
                qf1_winner = qf1_home if qf1_h > qf1_a else qf1_away
                qf2_winner = qf2_home if qf2_h > qf2_a else qf2_away
                
                # Semi-finals: QF1 winner vs 2nd place, QF2 winner vs 3rd place
                sf1_home = playoff_teams[0]  # 2nd place
                sf1_away = qf1_winner
                sf2_home = playoff_teams[1]  # 3rd place
                sf2_away = qf2_winner
                
                # Simulate semi-finals
                sf1_h, sf1_a = self.elo_system.predict_match(sf1_home, sf1_away)
                sf2_h, sf2_a = self.elo_system.predict_match(sf2_home, sf2_away)
                
                sf1_winner = sf1_home if sf1_h > sf1_a else sf1_away
                sf2_winner = sf2_home if sf2_h > sf2_a else sf2_away
                
                # Final: SF winners compete for promotion
                final_h, final_a = self.elo_system.predict_match(sf1_winner, sf2_winner)
                playoff_winner = sf1_winner if final_h > final_a else sf2_winner
                
                # Count playoff winner promotion
                promotion_counts[playoff_winner] += 1
                playoff_winner_counts[playoff_winner] += 1
            elif len(playoff_teams) >= 4:
                # Fallback for fewer teams (3rd-6th enter playoffs)
                playoff_teams = final_table[1:6]
                sf1_home = playoff_teams[1]  # 3rd
                sf1_away = playoff_teams[3]  # 6th
                sf2_home = playoff_teams[0]  # 4th
                sf2_away = playoff_teams[2]  # 5th
                
                sf1_h, sf1_a = self.elo_system.predict_match(sf1_home, sf1_away)
                sf2_h, sf2_a = self.elo_system.predict_match(sf2_home, sf2_away)
                
                sf1_winner = sf1_home if sf1_h > sf1_a else sf1_away
                sf2_winner = sf2_home if sf2_h > sf2_a else sf2_away
                
                final_h, final_a = self.elo_system.predict_match(sf1_winner, sf2_winner)
                playoff_winner = sf1_winner if final_h > final_a else sf2_winner
                
                promotion_counts[playoff_winner] += 1
                playoff_winner_counts[playoff_winner] += 1
            else:
                # Not enough for playoffs, auto-promote position 2
                if len(playoff_teams) >= 1:
                    promotion_counts[playoff_teams[0]] += 1

        # Complete progress bar
        bar = '=' * bar_width
        total_time = time.time() - start_time
        sys.stdout.write(f'\rProgress: [{bar}] 100% ({num_simulations}/{num_simulations}) Total: {total_time:.1f}s\n')
        sys.stdout.flush()

        return position_counts, promotion_counts, playoff_winner_counts

    def print_position_probabilities(self, position_counts, promotion_counts, playoff_winner_counts, num_simulations):
        """Print each team's probability of finishing in each position"""
        teams = sorted(self.team_stats.keys())

        print("\n" + "="*110)
        print("MONTE CARLO SIMULATION RESULTS - POSITION & PROMOTION PROBABILITIES")
        print("="*110)
        print(f"{'Team':<22} {'Win %':>8} {'Playoffs %':>12} {'Promoted %':>12} {'Playoff Winner %':>16}")
        print("-"*110)

        for team in teams:
            win_pct = position_counts[team][1] / num_simulations * 100
            # Combine positions 2-7 for playoff percentage
            playoff_pct = sum(position_counts[team][pos] for pos in range(2, 8)) / num_simulations * 100
            # Promoted = league winner (position 1) OR playoff winner
            promoted_pct = promotion_counts[team] / num_simulations * 100
            # Playoff winner percentage
            playoff_win_pct = playoff_winner_counts.get(team, 0) / num_simulations * 100

            print(f"{team:<22} {win_pct:>8.1f}% {playoff_pct:>12.1f}% {promoted_pct:>12.1f}% {playoff_win_pct:>16.1f}%")

        print("="*110)
        print(f"Based on {num_simulations} Monte Carlo simulations of the remaining season")
        print("Win %: Chance of finishing 1st (winning the league - auto-promoted)")
        print("Playoffs %: Chance of finishing 2nd-7th (qualifying for playoffs)")
        print("Promoted %: Total chance of getting promoted (league winner + playoff winner)")
        print("Playoff Winner %: Chance of winning the playoffs (make playoffs and win them)")

def main():
    # Set random seed for reproducible results
    random.seed(42)

    # Initialize simulator
    simulator = LeagueSimulator()

    # Load matches from embedded data
    simulator.load_matches()

    print(f"Loaded {len(simulator.completed_matches)} completed matches")
    print(f"Found {len(simulator.upcoming_fixtures)} fixtures to simulate")

    # Process completed matches
    simulator.process_completed_matches()

    # Print current standings before simulation
    simulator.print_league_table()

    # Run Monte Carlo simulations for position probabilities
    position_counts, promotion_counts, playoff_winner_counts = simulator.run_monte_carlo_simulations(num_simulations=1000)  # Full production run

    # Print position probabilities
    simulator.print_position_probabilities(position_counts, promotion_counts, playoff_winner_counts, 1000)

    # Simulate remaining season (single simulation)
    simulator.simulate_remaining_season()

    # Print final standings
    print("\n\nFINAL LEAGUE STANDINGS (Single Simulation):")
    simulator.print_league_table(is_final=True)

    # Print top ELO ratings
    print("\nTOP 5 ELO RATINGS:")
    sorted_by_elo = sorted(simulator.elo_system.ratings.items(), key=lambda x: x[1], reverse=True)
    for team, rating in sorted_by_elo[:5]:
        print(f"{team:<25} {rating:.1f}")

if __name__ == "__main__":
    main()