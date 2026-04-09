import random
import pandas as pd
import numpy as np
from collections import defaultdict
from tqdm import tqdm

########################################
# ELO RATINGS (from your main.py)
########################################
ELO_RATINGS = {
    'Spain': 2284.01, 'England': 2169.74, 'France': 2171.51, 'Germany': 2155.64,
    'Sweden': 2131.95, 'Netherlands': 2038.35, 'Norway': 1998.07, 'Denmark': 1975.94,
    'Italy': 1968.79, 'Iceland': 1883.96, 'Belgium': 1833.09, 'Austria': 1806.45,
    'Poland': 1810.72, 'Republic of Ireland': 1779.41, 'Serbia': 1717.59, 'Ukraine': 1679.38,
    'Slovenia': 1632.61,
    # CONCACAF teams
    'USA': 2252.84, 'Canada': 2053.77, 'Mexico': 1922.50, 'Haiti': 1717.51,
    'Jamaica': 1624.41, 'Costa Rica': 1611.55, 'Panama': 1636.01, 'Trinidad and Tobago': 1531.64,
    'Guatemala': 1474.47, 'Puerto Rico': 1654.17, 'El Salvador': 1580.76, 'Cuba': 1583.30,
    # Other CONCACAF teams (approximate/default 1500 if not known)
    'Guyana': 1500, 'Dominican Republic': 1500, 'Nicaragua': 1500, 'Honduras': 1500,
    'Suriname': 1500, 'Bermuda': 1500, 'Saint Kitts and Nevis': 1500, 'Barbados': 1500,
    'Saint Lucia': 1500, 'Saint Vincent and the Grenadines': 1500, 'Grenada': 1500,
    'Dominica': 1500, 'Belize': 1500, 'Curaçao': 1500, 'Antigua and Barbuda': 1500,
    'Aruba': 1500, 'Anguilla': 1500, 'Cayman Islands': 1500, 'U.S. Virgin Islands': 1500,
    # UEFA League C teams
    'Bosnia and Herzegovina': 1500, 'Lithuania': 1500, 'Estonia': 1500, 'Liechtenstein': 1500,
    'Kosovo': 1500, 'Croatia': 1500, 'Bulgaria': 1500, 'Gibraltar': 1500,
    'Hungary': 1500, 'Azerbaijan': 1500, 'North Macedonia': 1500, 'Andorra': 1500,
    'Greece': 1500, 'Faroe Islands': 1500, 'Georgia': 1500,
    'Romania': 1500, 'Moldova': 1500, 'Cyprus': 1500,
    'Belarus': 1500, 'Kazakhstan': 1500, 'Armenia': 1500,
    # OFC
    'New Zealand': 1688.34, 'Papua New Guinea': 1667.68, 'Fiji': 1548.73, 'American Samoa': 1280.00,
    # CAF teams
    'Morocco': 1500, 'Algeria': 1500, 'Senegal': 1500, 'Kenya': 1500,
    'South Africa': 1500, 'Ivory Coast': 1500, 'Burkina Faso': 1500, 'Tanzania': 1500,
    'Nigeria': 1500, 'Zambia': 1500, 'Egypt': 1500, 'Malawi': 1500,
    'Ghana': 1500, 'Cameroon': 1500, 'Mali': 1500, 'Cape Verde': 1500,
}

########################################
# UEFA LEAGUE A, B and C GROUPS (Updated for 2027 WWC Qual)
########################################
UEFA_A_GROUPS = {
    "UEFA_A1": ["Denmark", "Sweden", "Italy", "Serbia"],
    "UEFA_A2": ["France", "Netherlands", "Poland", "Republic of Ireland"],
    "UEFA_A3": ["England", "Spain", "Iceland", "Ukraine"],
    "UEFA_A4": ["Germany", "Norway", "Slovenia", "Austria"],
}
UEFA_B_GROUPS = {
    "UEFA_B1": ["Wales", "Czech Republic", "Albania", "Montenegro"],
    "UEFA_B2": ["Switzerland", "Turkey", "Northern Ireland", "Malta"],
    "UEFA_B3": ["Portugal", "Finland", "Slovakia", "Latvia"],
    "UEFA_B4": ["Scotland", "Belgium", "Israel", "Luxembourg"],
}
UEFA_C_GROUPS = {
    "UEFA_C1": ["Bosnia and Herzegovina", "Lithuania", "Estonia", "Liechtenstein"],
    "UEFA_C2": ["Kosovo", "Croatia", "Bulgaria", "Gibraltar"],
    "UEFA_C3": ["Hungary", "Azerbaijan", "North Macedonia", "Andorra"],
    "UEFA_C4": ["Greece", "Faroe Islands", "Georgia"],
    "UEFA_C5": ["Romania", "Moldova", "Cyprus"],
    "UEFA_C6": ["Belarus", "Kazakhstan", "Armenia"],
}
CAF_GROUPS = {
    "CAF_A": ["Morocco", "Algeria", "Senegal", "Kenya"],
    "CAF_B": ["South Africa", "Ivory Coast", "Burkina Faso", "Tanzania"],
    "CAF_C": ["Nigeria", "Zambia", "Egypt", "Malawi"],
    "CAF_D": ["Ghana", "Cameroon", "Mali", "Cape Verde"],
}
GROUPS = {**UEFA_A_GROUPS, **UEFA_B_GROUPS, **UEFA_C_GROUPS}

########################################
# OFC QUALIFICATION KNOCKOUT
########################################
OFC_SEMI_FINALS = [
    ("New Zealand", "Fiji"),
    ("Papua New Guinea", "American Samoa")
]
OFC_FINAL = ("Winner_Semi1", "Winner_Semi2")

########################################
# CONCACAF QUALIFICATION GROUPS (Updated for 2027 WWC Qual)
########################################
GROUPS_CONCACAF = {
    "CONCACAF_A": ["Mexico", "Puerto Rico", "Saint Lucia", "Saint Vincent and the Grenadines", "U.S. Virgin Islands"],
    "CONCACAF_B": ["Jamaica", "Guyana", "Nicaragua", "Dominica", "Antigua and Barbuda"],
    "CONCACAF_C": ["Costa Rica", "Guatemala", "Bermuda", "Grenada", "Cayman Islands"],
    "CONCACAF_D": ["Haiti", "Dominican Republic", "Suriname", "Belize", "Anguilla"],
    "CONCACAF_E": ["Panama", "Cuba", "Saint Kitts and Nevis", "Curaçao", "Aruba"],
    "CONCACAF_F": ["Trinidad and Tobago", "El Salvador", "Honduras", "Barbados"],
}

CURRENT_STANDINGS_CONCACAF = {
    "CONCACAF_A": {
        "Puerto Rico": {"P": 3, "W": 3, "D": 0, "L": 0, "GF": 26, "GA": 0, "GD": 26, "PTS": 9},
        "Mexico": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 21, "GA": 0, "GD": 21, "PTS": 6},
        "U.S. Virgin Islands": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 10, "GD": -7, "PTS": 3},
        "Saint Lucia": {"P": 3, "W": 0, "D": 0, "L": 3, "GF": 1, "GA": 17, "GD": -16, "PTS": 0},
        "Saint Vincent and the Grenadines": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 24, "GD": -24, "PTS": 0}
    },
    "CONCACAF_B": {
        "Jamaica": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 21, "GA": 2, "GD": 19, "PTS": 6},
        "Nicaragua": {"P": 3, "W": 2, "D": 0, "L": 1, "GF": 9, "GA": 4, "GD": 5, "PTS": 6},
        "Guyana": {"P": 3, "W": 2, "D": 0, "L": 1, "GF": 8, "GA": 3, "GD": 5, "PTS": 6},
        "Antigua and Barbuda": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 8, "GD": -8, "PTS": 0},
        "Dominica": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 21, "GD": -21, "PTS": 0}
    },
    "CONCACAF_C": {
        "Guatemala": {"P": 3, "W": 3, "D": 0, "L": 0, "GF": 23, "GA": 1, "GD": 22, "PTS": 9},
        "Costa Rica": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 10, "GA": 1, "GD": 9, "PTS": 6},
        "Bermuda": {"P": 3, "W": 1, "D": 0, "L": 2, "GF": 5, "GA": 12, "GD": -7, "PTS": 3},
        "Grenada": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 1, "GA": 8, "GD": -7, "PTS": 0},
        "Cayman Islands": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 17, "GD": -17, "PTS": 0}
    },
    "CONCACAF_D": {
        "Dominican Republic": {"P": 3, "W": 2, "D": 1, "L": 0, "GF": 16, "GA": 3, "GD": 13, "PTS": 7},
        "Haiti": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 11, "GA": 0, "GD": 11, "PTS": 6},
        "Suriname": {"P": 3, "W": 1, "D": 1, "L": 1, "GF": 5, "GA": 5, "GD": 0, "PTS": 4},
        "Anguilla": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 1, "GA": 11, "GD": -10, "PTS": 0},
        "Belize": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 1, "GA": 15, "GD": -14, "PTS": 0}
    },
    "CONCACAF_E": {
        "Cuba": {"P": 3, "W": 2, "D": 1, "L": 0, "GF": 6, "GA": 2, "GD": 4, "PTS": 7},
        "Panama": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 9, "GA": 1, "GD": 8, "PTS": 6},
        "Aruba": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 2, "GA": 2, "GD": 0, "PTS": 3},
        "Saint Kitts and Nevis": {"P": 3, "W": 0, "D": 1, "L": 2, "GF": 3, "GA": 7, "GD": -4, "PTS": 1},
        "Curaçao": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 1, "GA": 9, "GD": -8, "PTS": 0}
    },
    "CONCACAF_F": {
        "El Salvador": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 16, "GA": 0, "GD": 16, "PTS": 6},
        "Trinidad and Tobago": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 7, "GA": 2, "GD": 5, "PTS": 4},
        "Honduras": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 2, "GA": 5, "GD": -3, "PTS": 1},
        "Barbados": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 18, "GD": -18, "PTS": 0}
    }
}

REMAINING_MATCHES_CONCACAF = {
    "CONCACAF_A": [
        ("Mexico", "U.S. Virgin Islands"),
        ("Saint Vincent and the Grenadines", "U.S. Virgin Islands"),
        ("Saint Lucia", "Saint Vincent and the Grenadines"),
        ("Mexico", "Puerto Rico"),
        ("Saint Lucia", "U.S. Virgin Islands"),
        ("Mexico", "Saint Vincent and the Grenadines"),
        ("Puerto Rico", "Saint Lucia"),
        ("Puerto Rico", "Saint Vincent and the Grenadines"),
        ("Mexico", "Saint Lucia"),
        ("Puerto Rico", "U.S. Virgin Islands")
    ],
    "CONCACAF_B": [
        ("Jamaica", "Antigua and Barbuda"),
        ("Dominica", "Antigua and Barbuda"),
        ("Jamaica", "Guyana"),
        ("Nicaragua", "Dominica"),
        ("Antigua and Barbuda", "Guyana"),
        ("Jamaica", "Nicaragua"),
        ("Dominica", "Guyana"),
        ("Nicaragua", "Antigua and Barbuda"),
        ("Jamaica", "Dominica"),
        ("Guyana", "Nicaragua")
    ],
    "CONCACAF_C": [
        ("Costa Rica", "Cayman Islands"),
        ("Grenada", "Cayman Islands"),
        ("Costa Rica", "Guatemala"),
        ("Bermuda", "Grenada"),
        ("Cayman Islands", "Guatemala"),
        ("Costa Rica", "Bermuda"),
        ("Grenada", "Guatemala"),
        ("Bermuda", "Cayman Islands"),
        ("Costa Rica", "Grenada"),
        ("Guatemala", "Bermuda")
    ],
    "CONCACAF_D": [
        ("Haiti", "Anguilla"),
        ("Belize", "Anguilla"),
        ("Haiti", "Dominican Republic"),
        ("Suriname", "Belize"),
        ("Anguilla", "Dominican Republic"),
        ("Haiti", "Suriname"),
        ("Belize", "Dominican Republic"),
        ("Suriname", "Anguilla"),
        ("Haiti", "Belize"),
        ("Dominican Republic", "Suriname")
    ],
    "CONCACAF_E": [
        ("Panama", "Aruba"),
        ("Curaçao", "Aruba"),
        ("Panama", "Cuba"),
        ("Saint Kitts and Nevis", "Curaçao"),
        ("Aruba", "Cuba"),
        ("Panama", "Saint Kitts and Nevis"),
        ("Curaçao", "Cuba"),
        ("Saint Kitts and Nevis", "Aruba"),
        ("Panama", "Curaçao"),
        ("Cuba", "Saint Kitts and Nevis")
    ],
    "CONCACAF_F": [
        ("Trinidad and Tobago", "El Salvador"),
        ("Honduras", "Barbados"),
        ("El Salvador", "Barbados"),
        ("Trinidad and Tobago", "Honduras"),
        ("El Salvador", "Honduras"),
        ("Barbados", "Trinidad and Tobago")
    ]
}

# Current standings (as of March 2026)
UEFA_A_STANDINGS = {
    "UEFA_A1": {
        "Denmark": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 4, "GA": 2, "GD": 2, "PTS": 4},
        "Sweden": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 1, "GA": 0, "GD": 1, "PTS": 4},
        "Italy": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 1, "GA": 2, "GD": -1, "PTS": 1},
        "Serbia": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 1, "GA": 3, "GD": -2, "PTS": 1}
    },
    "UEFA_A2": {
        "France": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 6, "GA": 2, "GD": 4, "PTS": 6},
        "Netherlands": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 4, "GA": 3, "GD": 1, "PTS": 4},
        "Poland": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 3, "GA": 6, "GD": -3, "PTS": 1},
        "Republic of Ireland": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 2, "GA": 4, "GD": -2, "PTS": 0}
    },
    "UEFA_A3": {
        "England": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 8, "GA": 1, "GD": 7, "PTS": 6},
        "Spain": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 6, "GA": 1, "GD": 5, "PTS": 6},
        "Iceland": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 5, "GD": -5, "PTS": 0},
        "Ukraine": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 2, "GA": 9, "GD": -7, "PTS": 0}
    },
    "UEFA_A4": {
        "Germany": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 9, "GA": 0, "GD": 9, "PTS": 6},
        "Norway": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 1, "GA": 4, "GD": -3, "PTS": 3},
        "Slovenia": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 1, "GA": 5, "GD": -4, "PTS": 3},
        "Austria": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 2, "GD": -2, "PTS": 0}
    }
}
UEFA_B_STANDINGS = {
    "UEFA_B1": {
        "Wales": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 8, "GA": 3, "GD": 5, "PTS": 4},
        "Czech Republic": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 7, "GA": 3, "GD": 4, "PTS": 4},
        "Albania": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 6, "GD": -3, "PTS": 3},
        "Montenegro": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 2, "GA": 8, "GD": -6, "PTS": 0}
    },
    "UEFA_B2": {
        "Switzerland": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 6, "GA": 1, "GD": 5, "PTS": 6},
        "Turkey": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 4, "GA": 0, "GD": 4, "PTS": 6},
        "Northern Ireland": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 3, "GD": -3, "PTS": 0},
        "Malta": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 1, "GA": 7, "GD": -6, "PTS": 0}
    },
    "UEFA_B3": {
        "Portugal": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 6, "GA": 0, "GD": 6, "PTS": 6},
        "Finland": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 3, "GD": 0, "PTS": 3},
        "Slovakia": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 6, "GD": -3, "PTS": 3},
        "Latvia": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 3, "GA": 6, "GD": -3, "PTS": 0}
    },
    "UEFA_B4": {
        "Scotland": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 12, "GA": 0, "GD": 12, "PTS": 6},
        "Belgium": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 8, "GA": 0, "GD": 8, "PTS": 6},
        "Israel": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 8, "GD": -8, "PTS": 0},
        "Luxembourg": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 12, "GD": -12, "PTS": 0}
    }
}
UEFA_C_STANDINGS = {
    "UEFA_C1": {
        "Bosnia and Herzegovina": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 16, "GA": 2, "GD": 14, "PTS": 6},
        "Lithuania": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 6, "GA": 1, "GD": 5, "PTS": 4},
        "Estonia": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 1, "GA": 3, "GD": -2, "PTS": 1},
        "Liechtenstein": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 2, "GA": 19, "GD": -17, "PTS": 0}
    },
    "UEFA_C2": {
        "Kosovo": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 7, "GA": 0, "GD": 7, "PTS": 6},
        "Croatia": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 1, "GA": 1, "GD": 0, "PTS": 3},
        "Bulgaria": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 5, "GA": 1, "GD": 4, "PTS": 3},
        "Gibraltar": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 11, "GD": -11, "PTS": 0}
    },
    "UEFA_C3": {
        "Hungary": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 1, "GA": 0, "GD": 1, "PTS": 4},
        "Azerbaijan": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 2, "GA": 1, "GD": 1, "PTS": 3},
        "North Macedonia": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 2, "GD": 1, "PTS": 3},
        "Andorra": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 0, "GA": 3, "GD": -3, "PTS": 1}
    },
    "UEFA_C4": {
        "Greece": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 5, "GA": 0, "GD": 5, "PTS": 6},
        "Faroe Islands": {"P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 2, "GD": -2, "PTS": 0},
        "Georgia": {"P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 3, "GD": -3, "PTS": 0}
    },
    "UEFA_C5": {
        "Romania": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 5, "GA": 0, "GD": 5, "PTS": 6},
        "Moldova": {"P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 1, "GD": -1, "PTS": 0},
        "Cyprus": {"P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 4, "GD": -4, "PTS": 0}
    },
    "UEFA_C6": {
        "Belarus": {"P": 1, "W": 1, "D": 0, "L": 0, "GF": 1, "GA": 0, "GD": 1, "PTS": 3},
        "Kazakhstan": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 1, "GD": 2, "PTS": 3},
        "Armenia": {"P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 3, "GD": -3, "PTS": 0}
    }
}
CAF_STANDINGS = {
    "CAF_A": {
        "Morocco": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Algeria": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Senegal": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Kenya": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0}
    },
    "CAF_B": {
        "South Africa": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Ivory Coast": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Burkina Faso": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Tanzania": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0}
    },
    "CAF_C": {
        "Nigeria": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Zambia": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Egypt": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Malawi": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0}
    },
    "CAF_D": {
        "Ghana": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Cameroon": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Mali": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
        "Cape Verde": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0}
    }
}
CURRENT_STANDINGS = {**UEFA_A_STANDINGS, **UEFA_B_STANDINGS, **UEFA_C_STANDINGS}

# Remaining matches for each group (based on fixture list)
REMAINING_MATCHES = {
    "UEFA_A1": [
        ("Sweden", "Denmark"),
        ("Serbia", "Italy"),
        ("Sweden", "Serbia"),
        ("Denmark", "Italy"),
        ("Denmark", "Sweden"),
        ("Italy", "Serbia"),
        ("Sweden", "Italy"),
        ("Serbia", "Denmark")
    ],
    "UEFA_A2": [
        ("Netherlands", "France"),
        ("Poland", "Republic of Ireland"),
        ("France", "Netherlands"),
        ("Republic of Ireland", "Poland"),
        ("Poland", "France"),
        ("Republic of Ireland", "Netherlands"),
        ("France", "Republic of Ireland"),
        ("Netherlands", "Poland")
    ],
    "UEFA_A3": [
        ("England", "Spain"),
        ("Iceland", "Ukraine"),
        ("Spain", "Ukraine"),
        ("Iceland", "England"),
        ("Spain", "England"),
        ("Ukraine", "Iceland"),
        ("England", "Ukraine"),
        ("Iceland", "Spain")
    ],
    "UEFA_A4": [
        ("Germany", "Austria"),
        ("Norway", "Slovenia"),
        ("Slovenia", "Norway"),
        ("Austria", "Germany"),
        ("Austria", "Slovenia"),
        ("Germany", "Norway"),
        ("Slovenia", "Germany"),
        ("Norway", "Austria")
    ],

    "UEFA_B1": [
        ("Wales", "Czech Republic"),
        ("Albania", "Montenegro"),
        ("Czech Republic", "Albania"),
        ("Montenegro", "Wales"),
        ("Czech Republic", "Wales"),
        ("Albania", "Montenegro"),
        ("Wales", "Albania"),
        ("Montenegro", "Czech Republic")
    ],
    "UEFA_B2": [
        ("Switzerland", "Turkey"),
        ("Northern Ireland", "Malta"),
        ("Turkey", "Northern Ireland"),
        ("Malta", "Switzerland"),
        ("Turkey", "Switzerland"),
        ("Malta", "Northern Ireland"),
        ("Switzerland", "Malta"),
        ("Northern Ireland", "Turkey")
    ],
    "UEFA_B3": [
        ("Portugal", "Finland"),
        ("Slovakia", "Latvia"),
        ("Finland", "Slovakia"),
        ("Latvia", "Portugal"),
        ("Finland", "Portugal"),
        ("Latvia", "Slovakia"),
        ("Portugal", "Latvia"),
        ("Slovakia", "Finland")
    ],
    "UEFA_B4": [
        ("Scotland", "Belgium"),
        ("Israel", "Luxembourg"),
        ("Belgium", "Israel"),
        ("Luxembourg", "Scotland"),
        ("Belgium", "Scotland"),
        ("Luxembourg", "Israel"),
        ("Scotland", "Luxembourg"),
        ("Israel", "Belgium")
    ],
    "UEFA_C1": [
        ("Bosnia and Herzegovina", "Lithuania"),
        ("Estonia", "Liechtenstein"),
        ("Lithuania", "Estonia"),
        ("Liechtenstein", "Bosnia and Herzegovina"),
        ("Lithuania", "Bosnia and Herzegovina"),
        ("Estonia", "Liechtenstein"),
        ("Bosnia and Herzegovina", "Estonia"),
        ("Liechtenstein", "Lithuania")
    ],
    "UEFA_C2": [
        ("Kosovo", "Croatia"),
        ("Bulgaria", "Gibraltar"),
        ("Croatia", "Bulgaria"),
        ("Gibraltar", "Kosovo"),
        ("Croatia", "Kosovo"),
        ("Gibraltar", "Bulgaria"),
        ("Kosovo", "Bulgaria"),
        ("Gibraltar", "Croatia")
    ],
    "UEFA_C3": [
        ("Hungary", "Azerbaijan"),
        ("North Macedonia", "Andorra"),
        ("Azerbaijan", "North Macedonia"),
        ("Andorra", "Hungary"),
        ("Azerbaijan", "Hungary"),
        ("Andorra", "North Macedonia"),
        ("Hungary", "North Macedonia"),
        ("Andorra", "Azerbaijan")
    ],
    "UEFA_C4": [
        ("Greece", "Faroe Islands"),
        ("Georgia", "Cyprus"),
        ("Faroe Islands", "Georgia"),
        ("Cyprus", "Greece"),
        ("Faroe Islands", "Greece"),
        ("Cyprus", "Georgia"),
        ("Greece", "Georgia"),
        ("Cyprus", "Faroe Islands")
    ],
    "UEFA_C5": [
        ("Romania", "Moldova"),
        ("Cyprus", "Kazakhstan"),
        ("Moldova", "Cyprus"),
        ("Kazakhstan", "Romania"),
        ("Moldova", "Romania"),
        ("Kazakhstan", "Cyprus"),
        ("Romania", "Cyprus"),
        ("Kazakhstan", "Moldova")
    ],
    "UEFA_C6": [
        ("Belarus", "Kazakhstan"),
        ("Armenia", "Gibraltar"),
        ("Kazakhstan", "Armenia"),
        ("Gibraltar", "Belarus"),
        ("Kazakhstan", "Belarus"),
        ("Gibraltar", "Armenia"),
        ("Belarus", "Armenia"),
        ("Gibraltar", "Kazakhstan")
    ]

}

########################################
# SIMULATION FUNCTIONS (adapted from fullsim.py + your match sim)
########################################
NUM_SIMULATIONS = 1000

def win_prob(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def simulate_match(team1, team2):
    elo1 = ELO_RATINGS.get(team1, 1500)
    elo2 = ELO_RATINGS.get(team2, 1500)
    p = win_prob(elo1, elo2)
    r = random.random()
    if r < p * 0.75:  # Team 1 favored
        g1 = random.randint(1, 4)
        g2 = random.randint(0, 2)
    elif r < p * 0.75 + (1 - p) * 0.75:  # Team 2 upset
        g1 = random.randint(0, 2)
        g2 = random.randint(1, 4)
    else:  # Draw
        g1 = g2 = random.randint(0, 2)
    return g1, g2

def sample_bivariate_poisson_goals(lambda_a, lambda_b, correlation=0.15):
    """
    Sample goals for two teams using a bivariate Poisson-like approach.

    This models goals with a shared 'excitement' component that creates
    realistic correlation between teams' scoring (e.g., high-scoring games
    tend to have both teams scoring more).

    Parameters:
    - lambda_a: Expected goals for team A
    - lambda_b: Expected goals for team B
    - correlation: Controls how much the teams' scoring is correlated (0-1)

    Returns:
    - goals_a, goals_b: Sampled goal counts
    """
    # Shared component (excitement factor) - models correlated scoring
    shared_lambda = (lambda_a + lambda_b) * correlation
    shared_goals = np.random.poisson(shared_lambda)

    # Team-specific components (attack vs defense)
    individual_a = np.random.poisson(lambda_a * (1 - correlation))
    individual_b = np.random.poisson(lambda_b * (1 - correlation))

    goals_a = shared_goals + individual_a
    goals_b = shared_goals + individual_b

    # Cap goals at reasonable maximum (World Cup rarely sees 8+ goals)
    max_goals = 10
    return min(goals_a, max_goals), min(goals_b, max_goals)

def simulate_knockout_match(team_a, team_b):
    """
    Simulate a knockout match between two teams.
    Returns the winner.
    """
    rating_a = ELO_RATINGS.get(team_a, 1500)
    rating_b = ELO_RATINGS.get(team_b, 1500)

    # Calculate expected goals
    rating_diff = abs(rating_a - rating_b)
    base_lambda = 2.5 + 0.001 * rating_diff
    base_lambda = max(1.8, min(3.8, base_lambda))

    exp_rating_a = 10 ** (rating_a / 400)
    exp_rating_b = 10 ** (rating_b / 400)
    share_a = exp_rating_a / (exp_rating_a + exp_rating_b)

    lambda_a = base_lambda * share_a
    lambda_b = base_lambda * (1 - share_a)

    # Sample goals
    goals_a, goals_b = sample_bivariate_poisson_goals(lambda_a, lambda_b, correlation=0.12)

    # Determine winner
    if goals_a > goals_b:
        return team_a
    elif goals_b > goals_a:
        return team_b
    else:
        # In knockout, if draw, simulate extra time or penalties
        # For simplicity, higher rated team wins on penalties
        return team_a if rating_a > rating_b else team_b

def update_table(table, t1, t2, g1, g2):
    for t in (t1, t2):
        if t not in table:
            table[t] = {"P":0, "W":0, "D":0, "L":0, "GF":0, "GA":0, "GD":0, "PTS":0}
    table[t1]["P"] += 1
    table[t2]["P"] += 1
    table[t1]["GF"] += g1
    table[t1]["GA"] += g2
    table[t2]["GF"] += g2
    table[t2]["GA"] += g1
    if g1 > g2:
        table[t1]["W"] += 1; table[t2]["L"] += 1; table[t1]["PTS"] += 3
    elif g2 > g1:
        table[t2]["W"] += 1; table[t1]["L"] += 1; table[t2]["PTS"] += 3
    else:
        table[t1]["D"] += 1; table[t2]["D"] += 1; table[t1]["PTS"] += 1; table[t2]["PTS"] += 1
    table[t1]["GD"] = table[t1]["GF"] - table[t1]["GA"]
    table[t2]["GD"] = table[t2]["GF"] - table[t2]["GA"]

def simulate_group_full(group_name, teams, current_standings):
    """Simulate one full realization of the group (current + remaining matches)."""
    table = {team: {"P":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"PTS":0} for team in teams}
    # Merge current standings
    if group_name in current_standings:
        for team, stats in current_standings[group_name].items():
            if team in table:
                table[team].update(stats)

    # Simulate all possible matches (round-robin) — the current standings reflect played matches
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            t1, t2 = teams[i], teams[j]
            g1, g2 = simulate_match(t1, t2)
            update_table(table, t1, t2, g1, g2)

    # Sort standings: PTS > GD > GF
    ranking = sorted(table.items(), key=lambda x: (x[1]["PTS"], x[1]["GD"], x[1]["GF"]), reverse=True)
    return ranking, table

def run_monte_carlo(pbar):
    print("=== 2027 WOMEN'S WORLD CUP QUALIFICATION SIMULATOR (UEFA League A, B and C) ===")
    print("Running 10000 full qualification simulations...\n")

    position_results = {}
    expected_points = {}
    uefa_qual_probs = {}  # To collect for final list

    for group_name, teams in GROUPS.items():
        print(f"Simulating {group_name}...")
        pos_counts = {team: {'1st': 0, '2nd': 0} for team in teams}  # Top 2 qualify for playoffs
        points_tracker = {team: {'total_pts': 0, 'total_gf': 0, 'total_ga': 0, 'apps': 0} for team in teams}

        for _ in range(NUM_SIMULATIONS):
            ranking, final_table = simulate_group_full(group_name, teams, CURRENT_STANDINGS)

            # Record positions
            for pos, (team, stats) in enumerate(ranking, 1):
                if pos == 1:
                    pos_counts[team]['1st'] += 1
                elif pos == 2:
                    pos_counts[team]['2nd'] += 1

            # Track expected points and goals
            for team, stats in final_table.items():
                points_tracker[team]['total_pts'] += stats["PTS"]
                points_tracker[team]['total_gf'] += stats["GF"]
                points_tracker[team]['total_ga'] += stats["GA"]
                points_tracker[team]['apps'] += 1

            pbar.update(1)

        position_results[group_name] = pos_counts
        expected_points[group_name] = {team: round(points_tracker[team]['total_pts'] / NUM_SIMULATIONS, 1) for team in teams}
        expected_gf = {team: round(points_tracker[team]['total_gf'] / NUM_SIMULATIONS, 1) for team in teams}
        expected_ga = {team: round(points_tracker[team]['total_ga'] / NUM_SIMULATIONS, 1) for team in teams}
        expected_gd = {team: round((points_tracker[team]['total_gf'] - points_tracker[team]['total_ga']) / NUM_SIMULATIONS, 1) for team in teams}

        # Collect qual probs for final list (top 2 qualify for playoffs)
        for team in teams:
            uefa_qual_probs[team] = round((pos_counts[team]['1st'] + pos_counts[team]['2nd']) / NUM_SIMULATIONS * 100, 1)



    return uefa_qual_probs

def run_concacaf_simulation(pbar):
    print("=== 2027 WOMEN'S WORLD CUP QUALIFICATION SIMULATOR (CONCACAF Groups) ===")
    print("Running 10000 full qualification simulations...\n")

    position_results = {}
    expected_points = {}
    concacaf_qual_probs = {}  # Top 2 from each group

    for group_name, teams in GROUPS_CONCACAF.items():
        print(f"Simulating {group_name}...")
        pos_counts = {team: {'1st': 0} for team in teams}  # Only winners qualify for championship
        points_tracker = {team: {'total_pts': 0, 'total_gf': 0, 'total_ga': 0, 'apps': 0} for team in teams}

        for _ in range(NUM_SIMULATIONS):
            ranking, final_table = simulate_group_full(group_name, teams, CURRENT_STANDINGS_CONCACAF)

            # Record positions
            for pos, (team, stats) in enumerate(ranking, 1):
                if pos == 1:
                    pos_counts[team]['1st'] += 1

            # Track expected points and goals
            for team, stats in final_table.items():
                points_tracker[team]['total_pts'] += stats["PTS"]
                points_tracker[team]['total_gf'] += stats["GF"]
                points_tracker[team]['total_ga'] += stats["GA"]
                points_tracker[team]['apps'] += 1

            pbar.update(1)

        position_results[group_name] = pos_counts
        expected_points[group_name] = {team: round(points_tracker[team]['total_pts'] / NUM_SIMULATIONS, 1) for team in teams}
        expected_gf = {team: round(points_tracker[team]['total_gf'] / NUM_SIMULATIONS, 1) for team in teams}
        expected_ga = {team: round(points_tracker[team]['total_ga'] / NUM_SIMULATIONS, 1) for team in teams}
        expected_gd = {team: round((points_tracker[team]['total_gf'] - points_tracker[team]['total_ga']) / NUM_SIMULATIONS, 1) for team in teams}

        # Collect qual probs for final list (winners)
        for team in teams:
            concacaf_qual_probs[team] = round(pos_counts[team]['1st'] / NUM_SIMULATIONS * 100, 1)



    return concacaf_qual_probs

def run_ofc_simulation(pbar):
    print("=== 2027 WOMEN'S WORLD CUP QUALIFICATION SIMULATOR (OFC Knockout) ===")
    print("Running 10000 full qualification simulations...\n")

    qual_counts = {team: 0 for team in ["New Zealand", "Fiji", "Papua New Guinea", "American Samoa"]}

    for _ in range(NUM_SIMULATIONS):
        # Simulate Semi-finals
        winner_semi1 = simulate_knockout_match(OFC_SEMI_FINALS[0][0], OFC_SEMI_FINALS[0][1])
        winner_semi2 = simulate_knockout_match(OFC_SEMI_FINALS[1][0], OFC_SEMI_FINALS[1][1])

        # Simulate Final
        ofc_winner = simulate_knockout_match(winner_semi1, winner_semi2)

        # Record qualification
        qual_counts[ofc_winner] += 1

        pbar.update(1)

    # Collect qual probs
    ofc_qual_probs = {team: round(qual_counts[team] / 10000 * 100, 1) for team in qual_counts}



    return ofc_qual_probs

def run_caf_simulation(pbar):
    print("=== 2027 WOMEN'S AFCON SIMULATOR (CAF Groups + Knockout) ===")
    print("Running 10000 full tournament simulations...\n")

    qual_counts = {team: 0 for team in ["Morocco", "Algeria", "Senegal", "Kenya", "South Africa", "Ivory Coast", "Burkina Faso", "Tanzania", "Nigeria", "Zambia", "Egypt", "Malawi", "Ghana", "Cameroon", "Mali", "Cape Verde"]}

    for _ in range(NUM_SIMULATIONS):
        # Simulate group stage to get winners
        group_winners = {}
        for group_name, teams in CAF_GROUPS.items():
            ranking, _ = simulate_group_full(group_name, teams, CAF_STANDINGS)
            group_winners[group_name] = ranking[0][0]  # Winner

        # Simulate knockout: assume QF: A1 vs B1, C1 vs D1, etc.
        qf1 = simulate_knockout_match(group_winners["CAF_A"], group_winners["CAF_B"])
        qf2 = simulate_knockout_match(group_winners["CAF_C"], group_winners["CAF_D"])

        # SF: qf1 vs qf2
        sf1 = simulate_knockout_match(qf1, qf2)

        # Final winner
        afcon_winner = sf1  # Since only one match for simplicity, winner qualifies

        # Record qualification (QF winners qualify)
        qual_counts[qf1] += 1
        qual_counts[qf2] += 1

        pbar.update(1)

    # Collect qual probs
    caf_qual_probs = {team: round(qual_counts[team] / 10000 * 100, 1) for team in qual_counts}



    return caf_qual_probs

if __name__ == "__main__":
    total_sims = 4*1000 + 6*1000 + 1*1000 + 1*1000  # 12000
    with tqdm(total=total_sims, desc="Overall qualification simulations") as pbar:
        uefa_probs = run_monte_carlo(pbar)
        print("\n" + "="*50 + "\n")
        concacaf_probs = run_concacaf_simulation(pbar)
        print("\n" + "="*50 + "\n")
        ofc_probs = run_ofc_simulation(pbar)
        print("\n" + "="*50 + "\n")
        caf_probs = run_caf_simulation(pbar)
        print("\n" + "="*50 + "\n")

        # Combine all qualification probabilities
        all_qual_probs = {**uefa_probs, **concacaf_probs, **ofc_probs, **caf_probs}

        # Sort by probability descending
        sorted_teams = sorted(all_qual_probs.items(), key=lambda x: x[1], reverse=True)

        print("### All Teams Qualification Probabilities (Descending Order)")
        for team, prob in sorted_teams:
            if prob > 0:  # Only include teams with chance
                print(f"{team}: {prob}%")

        print("\nSimulation complete. Probabilities reflect remaining matches via Monte Carlo.")