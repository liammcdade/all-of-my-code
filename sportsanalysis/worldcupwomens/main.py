import random
import numpy as np
from collections import defaultdict
from tqdm import tqdm


########################################
# ELO RATINGS (from your main.py)
########################################
ELO_RATINGS = {
    'Spain': 2083.09, 'USA': 2054.65, 'England': 2038.72, 'Germany': 2021.78,
    'Japan': 2011.27, 'Brazil': 1980.00, 'France': 1975.60, 'Sweden': 1961.22,
    'Canada': 1934.88, 'Netherlands': 1929.32, 'Korea DPR': 1910.63, 'Denmark': 1885.52,
    'Norway': 1881.42, 'Italy': 1877.26, 'Australia': 1838.17, 'China PR': 1817.53,
    'Iceland': 1795.94, 'Belgium': 1784.21, 'Korea Republic': 1779.81, 'Colombia': 1774.76,
    'Portugal': 1765.46, 'Austria': 1751.05, 'Republic of Ireland': 1749.37,
    'Scotland': 1734.94, 'Switzerland': 1727.22, 'Finland': 1718.30, 'Mexico': 1707.61,
    'Poland': 1705.22, 'Russia': 1699.74, 'Argentina': 1696.45, 'Wales': 1673.57,
    'Czechia': 1671.82, 'New Zealand': 1659.16, 'Serbia': 1648.95, 'Ukraine': 1641.26,
    'Nigeria': 1602.04, 'Vietnam': 1593.71, 'Slovenia': 1582.13, 'Philippines': 1566.44,
    'Chinese Taipei': 1566.09, 'Jamaica': 1544.80, 'Costa Rica': 1528.39,
    'Venezuela': 1527.62, 'Chile': 1514.78, 'Paraguay': 1507.34,
    'Northern Ireland': 1498.80, 'Hungary': 1496.99, 'Romania': 1488.99,
    'Haiti': 1480.75, 'Thailand': 1478.09, 'Türkiye': 1475.83,
    'Slovakia': 1475.12, 'Uzbekistan': 1472.13, 'Belarus': 1470.18,
    'Myanmar': 1469.68, 'Panama': 1463.72, 'Papua New Guinea': 1450.33,
    'South Africa': 1438.71, 'Ghana': 1429.23, 'Greece': 1428.26,
    'Uruguay': 1414.25, 'Morocco': 1402.88, 'Ecuador': 1397.58,
    'Zambia': 1393.73, 'Israel': 1391.18, 'Croatia': 1386.54,
    'Bosnia and Herzegovina': 1382.21, 'IR Iran': 1370.37, 'India': 1367.24,
    'Cameroon': 1358.15, 'Albania': 1349.57, "Côte d'Ivoire": 1338.92,
    'Algeria': 1318.95, 'Azerbaijan': 1317.17, 'Peru': 1304.61,
    'Jordan': 1297.82, 'Puerto Rico': 1294.95, 'El Salvador': 1291.59,
    'Fiji': 1289.65, 'Senegal': 1285.85, 'Kosovo': 1274.57,
    'Hong Kong': 1273.08, 'Trinidad and Tobago': 1269.08,
    'Guatemala': 1267.25, 'Mali': 1260.36, 'Samoa': 1246.84,
    'Nepal': 1244.92, 'Montenegro': 1241.29, 'Solomon Islands': 1234.03,
    'Equatorial Guinea': 1231.03, 'Malta': 1227.65, 'Malaysia': 1218.02,
    'Guyana': 1217.37, 'Dominican Republic': 1211.22, 'Nicaragua': 1205.13,
    'Cuba': 1204.21, 'Kazakhstan': 1203.95, 'Guam': 1201.91,
    'Egypt': 1199.25, 'Tunisia': 1197.50, 'Lithuania': 1196.73,
    'Estonia': 1189.92, 'Latvia': 1184.56, 'New Caledonia': 1184.36,
    'Congo DR': 1179.60, 'Indonesia': 1175.97, 'Bulgaria': 1172.98,
    'Bahrain': 1169.30, 'Bolivia': 1169.02, 'Faroe Islands': 1168.96,
    'Vanuatu': 1168.10, 'Bangladesh': 1165.57, 'Laos': 1164.92,
    'Congo': 1161.03, 'Luxembourg': 1154.67, 'Tonga': 1152.53,
    'Cambodia': 1146.28, 'Burkina Faso': 1139.92, 'Cabo Verde': 1131.67,
    'American Samoa': 1130.42, 'Tanzania': 1129.13, 'Tahiti': 1127.92,
    'United Arab Emirates': 1126.67, 'Namibia': 1124.29, 'Georgia': 1118.63,
    'Honduras': 1115.28, 'Zimbabwe': 1114.48, 'Kenya': 1104.82,
    'Palestine': 1102.89, 'Lebanon': 1100.95, 'Cyprus': 1100.67,
    'Cook Islands': 1099.76, 'Moldova': 1099.18, 'Togo': 1092.99,
    'The Gambia': 1082.47, 'North Macedonia': 1079.98, 'Ethiopia': 1068.12,
    'Benin': 1066.23, 'Suriname': 1065.77, 'Turkmenistan': 1063.88,
    'Bermuda': 1050.02, 'Guinea': 1048.64, 'Kyrgyz Republic': 1048.29,
    'Central African Republic': 1045.87, 'Uganda': 1036.27,
    'Mongolia': 1035.67, 'Botswana': 1029.20, 'Gabon': 1028.74,
    'Armenia': 1028.10, 'St Kitts and Nevis': 1026.93, 'Sierra Leone': 1021.39,
    'Singapore': 1019.15, 'Malawi': 1018.89, 'Pakistan': 1008.65,
    'Angola': 989.68, 'Chad': 985.55, 'Timor-Leste': 965.35,
    'Tajikistan': 954.78, 'St Vincent and the Grenadines': 947.14,
    'Saudi Arabia': 942.58, 'Syria': 931.42, 'Sri Lanka': 930.20,
    'Barbados': 924.87, 'Bhutan': 924.11, 'St Lucia': 923.18,
    'Iraq': 910.49, 'Maldives': 908.71, 'Belize': 906.20,
    'Rwanda': 892.39, 'Dominica': 884.73, 'Liberia': 882.37,
    'Grenada': 878.19, 'Mozambique': 874.79, 'Niger': 863.94,
    'Seychelles': 849.52, 'Macau': 846.95, 'Lesotho': 840.12,
    'Guinea-Bissau': 838.58, 'Andorra': 822.29, 'Burundi': 822.10,
    'Curaçao': 821.91, 'Antigua and Barbuda': 807.20, 'Aruba': 801.27,
    'Eswatini': 797.06, 'US Virgin Islands': 790.28, 'Cayman Islands': 777.07,
    'Libya': 739.94, 'Gibraltar': 735.29, 'Comoros': 728.71,
    'Liechtenstein': 727.29, 'Madagascar': 703.03, 'Anguilla': 681.60,
    'Bahamas': 665.71, 'South Sudan': 650.08,
    'Turks and Caicos Islands': 627.14, 'Djibouti': 598.38,
    'Mauritius': 391.92, 'Türkiye': 1800, "Côte d'Ivoire": 1700
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
    "UEFA_B2": ["Switzerland", "Türkiye", "Northern Ireland", "Malta"],
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
    "CAF_B": ["South Africa", "Côte d'Ivoire", "Burkina Faso", "Tanzania"],
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

# Current standings (as of April 2026)
UEFA_A_STANDINGS = {
    "UEFA_A1": {
        "Denmark": {"P": 4, "W": 2, "D": 2, "L": 0, "GF": 6, "GA": 3, "GD": 3, "PTS": 8},
        "Sweden": {"P": 4, "W": 2, "D": 1, "L": 1, "GF": 3, "GA": 2, "GD": 1, "PTS": 7},
        "Italy": {"P": 4, "W": 1, "D": 2, "L": 1, "GF": 7, "GA": 2, "GD": 5, "PTS": 5},
        "Serbia": {"P": 4, "W": 0, "D": 1, "L": 3, "GF": 1, "GA": 10, "GD": -9, "PTS": 1}
    },
    "UEFA_A2": {
        "Netherlands": {"P": 4, "W": 2, "D": 2, "L": 0, "GF": 7, "GA": 5, "GD": 2, "PTS": 8},
        "France": {"P": 4, "W": 2, "D": 1, "L": 1, "GF": 8, "GA": 5, "GD": 3, "PTS": 7},
        "Republic of Ireland": {"P": 4, "W": 2, "D": 0, "L": 2, "GF": 6, "GA": 6, "GD": 0, "PTS": 6},
        "Poland": {"P": 4, "W": 0, "D": 1, "L": 3, "GF": 5, "GA": 10, "GD": -5, "PTS": 1}
    },
    "UEFA_A3": {
        "England": {"P": 4, "W": 4, "D": 0, "L": 0, "GF": 10, "GA": 1, "GD": 9, "PTS": 12},
        "Spain": {"P": 4, "W": 3, "D": 0, "L": 1, "GF": 11, "GA": 2, "GD": 9, "PTS": 9},
        "Iceland": {"P": 4, "W": 1, "D": 0, "L": 3, "GF": 1, "GA": 6, "GD": -5, "PTS": 3},
        "Ukraine": {"P": 4, "W": 0, "D": 0, "L": 4, "GF": 2, "GA": 15, "GD": -13, "PTS": 0}
    },
    "UEFA_A4": {
        "Germany": {"P": 4, "W": 3, "D": 1, "L": 0, "GF": 14, "GA": 1, "GD": 13, "PTS": 10},
        "Norway": {"P": 4, "W": 3, "D": 0, "L": 1, "GF": 9, "GA": 6, "GD": 3, "PTS": 9},
        "Slovenia": {"P": 4, "W": 1, "D": 0, "L": 3, "GF": 3, "GA": 13, "GD": -10, "PTS": 3},
        "Austria": {"P": 4, "W": 0, "D": 1, "L": 3, "GF": 1, "GA": 7, "GD": -6, "PTS": 1}
    }
}
UEFA_B_STANDINGS = {
    "UEFA_B1": {
        "Czech Republic": {"P": 4, "W": 3, "D": 1, "L": 0, "GF": 16, "GA": 4, "GD": 12, "PTS": 10},
        "Wales": {"P": 4, "W": 3, "D": 1, "L": 0, "GF": 13, "GA": 3, "GD": 10, "PTS": 10},
        "Albania": {"P": 4, "W": 1, "D": 0, "L": 3, "GF": 3, "GA": 11, "GD": -8, "PTS": 3},
        "Montenegro": {"P": 4, "W": 0, "D": 0, "L": 4, "GF": 3, "GA": 17, "GD": -14, "PTS": 0}
    },
    "UEFA_B2": {
        "Switzerland": {"P": 4, "W": 3, "D": 1, "L": 0, "GF": 10, "GA": 3, "GD": 7, "PTS": 10},
        "Türkiye": {"P": 4, "W": 2, "D": 1, "L": 1, "GF": 6, "GA": 4, "GD": 2, "PTS": 7},
        "Northern Ireland": {"P": 4, "W": 2, "D": 0, "L": 2, "GF": 8, "GA": 5, "GD": 3, "PTS": 6},
        "Malta": {"P": 4, "W": 0, "D": 0, "L": 4, "GF": 3, "GA": 15, "GD": -12, "PTS": 0}
    },
    "UEFA_B3": {
        "Portugal": {"P": 4, "W": 4, "D": 0, "L": 0, "GF": 11, "GA": 1, "GD": 10, "PTS": 12},
        "Finland": {"P": 4, "W": 3, "D": 0, "L": 1, "GF": 8, "GA": 5, "GD": 3, "PTS": 9},
        "Slovakia": {"P": 4, "W": 1, "D": 0, "L": 3, "GF": 6, "GA": 12, "GD": -6, "PTS": 3},
        "Latvia": {"P": 4, "W": 0, "D": 0, "L": 4, "GF": 3, "GA": 10, "GD": -7, "PTS": 0}
    },
    "UEFA_B4": {
        "Scotland": {"P": 4, "W": 2, "D": 2, "L": 0, "GF": 13, "GA": 1, "GD": 12, "PTS": 8},
        "Belgium": {"P": 4, "W": 2, "D": 2, "L": 0, "GF": 9, "GA": 1, "GD": 8, "PTS": 8},
        "Israel": {"P": 4, "W": 2, "D": 0, "L": 2, "GF": 9, "GA": 9, "GD": 0, "PTS": 6},
        "Luxembourg": {"P": 4, "W": 0, "D": 0, "L": 4, "GF": 1, "GA": 21, "GD": -20, "PTS": 0}
    }
}
UEFA_C_STANDINGS = {
    "UEFA_C1": {
        "Bosnia and Herzegovina": {"P": 4, "W": 3, "D": 0, "L": 1, "GF": 22, "GA": 4, "GD": 18, "PTS": 9},
        "Estonia": {"P": 4, "W": 2, "D": 1, "L": 1, "GF": 5, "GA": 5, "GD": 0, "PTS": 7},
        "Lithuania": {"P": 4, "W": 2, "D": 1, "L": 1, "GF": 9, "GA": 3, "GD": 6, "PTS": 7},
        "Liechtenstein": {"P": 4, "W": 0, "D": 0, "L": 4, "GF": 3, "GA": 27, "GD": -24, "PTS": 0}
    },
    "UEFA_C2": {
        "Kosovo": {"P": 4, "W": 4, "D": 0, "L": 0, "GF": 12, "GA": 2, "GD": 10, "PTS": 12},
        "Croatia": {"P": 4, "W": 3, "D": 0, "L": 1, "GF": 11, "GA": 1, "GD": 10, "PTS": 9},
        "Bulgaria": {"P": 4, "W": 1, "D": 0, "L": 3, "GF": 7, "GA": 6, "GD": 1, "PTS": 3},
        "Gibraltar": {"P": 4, "W": 0, "D": 0, "L": 4, "GF": 0, "GA": 21, "GD": -21, "PTS": 0}
    },
    "UEFA_C3": {
        "Hungary": {"P": 4, "W": 3, "D": 1, "L": 0, "GF": 13, "GA": 0, "GD": 13, "PTS": 10},
        "Azerbaijan": {"P": 4, "W": 3, "D": 0, "L": 1, "GF": 7, "GA": 2, "GD": 5, "PTS": 9},
        "North Macedonia": {"P": 4, "W": 1, "D": 0, "L": 3, "GF": 3, "GA": 14, "GD": -11, "PTS": 3},
        "Andorra": {"P": 4, "W": 0, "D": 1, "L": 3, "GF": 1, "GA": 8, "GD": -7, "PTS": 1}
    },
    "UEFA_C4": {
        "Greece": {"P": 3, "W": 3, "D": 0, "L": 0, "GF": 8, "GA": 2, "GD": 6, "PTS": 9},
        "Faroe Islands": {"P": 3, "W": 1, "D": 0, "L": 2, "GF": 3, "GA": 5, "GD": -2, "PTS": 3},
        "Georgia": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 4, "GD": -4, "PTS": 0}
    },
    "UEFA_C5": {
        "Romania": {"P": 3, "W": 3, "D": 0, "L": 0, "GF": 8, "GA": 0, "GD": 8, "PTS": 9},
        "Moldova": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 0, "GA": 1, "GD": -1, "PTS": 1},
        "Cyprus": {"P": 3, "W": 0, "D": 1, "L": 2, "GF": 0, "GA": 7, "GD": -7, "PTS": 1}
    },
    "UEFA_C6": {
        "Belarus": {"P": 3, "W": 2, "D": 0, "L": 1, "GF": 4, "GA": 1, "GD": 3, "PTS": 6},
        "Kazakhstan": {"P": 3, "W": 2, "D": 0, "L": 1, "GF": 4, "GA": 1, "GD": 3, "PTS": 6},
        "Armenia": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 6, "GD": -6, "PTS": 0}
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
        "Côte d'Ivoire": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0},
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
CONMEBOL_GROUP = ["Argentina", "Colombia", "Venezuela", "Chile", "Ecuador", "Paraguay", "Peru", "Uruguay", "Bolivia"]
CONMEBOL_STANDINGS = {
    "Argentina": {"P": 6, "W": 4, "D": 2, "L": 0, "GF": 16, "GA": 4, "GD": 12, "PTS": 14},
    "Colombia": {"P": 6, "W": 4, "D": 2, "L": 0, "GF": 11, "GA": 4, "GD": 7, "PTS": 14},
    "Venezuela": {"P": 7, "W": 3, "D": 2, "L": 2, "GF": 18, "GA": 5, "GD": 13, "PTS": 11},
    "Chile": {"P": 7, "W": 3, "D": 1, "L": 3, "GF": 10, "GA": 7, "GD": 3, "PTS": 10},
    "Ecuador": {"P": 6, "W": 2, "D": 2, "L": 2, "GF": 6, "GA": 4, "GD": 2, "PTS": 8},
    "Paraguay": {"P": 6, "W": 2, "D": 1, "L": 3, "GF": 6, "GA": 7, "GD": -1, "PTS": 7},
    "Peru": {"P": 6, "W": 2, "D": 1, "L": 3, "GF": 7, "GA": 14, "GD": -7, "PTS": 7},
    "Uruguay": {"P": 6, "W": 1, "D": 2, "L": 3, "GF": 6, "GA": 9, "GD": -3, "PTS": 5},
    "Bolivia": {"P": 6, "W": 0, "D": 1, "L": 5, "GF": 2, "GA": 28, "GD": -26, "PTS": 1}
}
REMAINING_MATCHES_CONMEBOL = [
    ("Bolivia", "Paraguay"),
    ("Argentina", "Peru"),
    ("Colombia", "Uruguay"),
    ("Chile", "Ecuador"),
    ("Peru", "Bolivia"),
    ("Paraguay", "Colombia"),
    ("Uruguay", "Venezuela"),
    ("Ecuador", "Argentina")
]
CURRENT_STANDINGS = {**UEFA_A_STANDINGS, **UEFA_B_STANDINGS, **UEFA_C_STANDINGS}

# Remaining matches for each group (based on fixture list)
REMAINING_MATCHES = {
    "UEFA_A1": [
        ("Denmark", "Sweden"),
        ("Italy", "Serbia"),
        ("Sweden", "Italy"),
        ("Serbia", "Denmark")
    ],
    "UEFA_A2": [
        ("Poland", "France"),
        ("Republic of Ireland", "Netherlands"),
        ("France", "Republic of Ireland"),
        ("Netherlands", "Poland")
    ],
    "UEFA_A3": [
        ("Spain", "England"),
        ("Ukraine", "Iceland"),
        ("England", "Ukraine"),
        ("Iceland", "Spain")
    ],
    "UEFA_A4": [
        ("Austria", "Slovenia"),
        ("Germany", "Norway"),
        ("Slovenia", "Germany"),
        ("Norway", "Austria")
    ],

    "UEFA_B1": [
        ("Montenegro", "Wales"),
        ("Czech Republic", "Albania"),
        ("Wales", "Czech Republic"),
        ("Albania", "Montenegro")
    ],
    "UEFA_B2": [
        ("Switzerland", "Malta"),
        ("Türkiye", "Northern Ireland"),
        ("Northern Ireland", "Switzerland"),
        ("Malta", "Türkiye")
    ],
    "UEFA_B3": [
        ("Portugal", "Latvia"),
        ("Slovakia", "Finland"),
        ("Finland", "Portugal"),
        ("Latvia", "Slovakia")
    ],
    "UEFA_B4": [
        ("Belgium", "Luxembourg"),
        ("Scotland", "Israel"),
        ("Israel", "Scotland"),
        ("Luxembourg", "Belgium")
    ],
    "UEFA_C1": [
        ("Bosnia and Herzegovina", "Lithuania"),
        ("Liechtenstein", "Estonia"),
        ("Estonia", "Bosnia and Herzegovina"),
        ("Lithuania", "Liechtenstein")
    ],
    "UEFA_C2": [
        ("Kosovo", "Croatia"),
        ("Bulgaria", "Gibraltar"),
        ("Croatia", "Bulgaria"),
        ("Gibraltar", "Kosovo")
    ],
    "UEFA_C3": [
        ("Azerbaijan", "Hungary"),
        ("Andorra", "North Macedonia"),
        ("Hungary", "Andorra"),
        ("North Macedonia", "Azerbaijan")
    ],
    "UEFA_C4": [
        ("Georgia", "Faroe Islands"),
        ("Georgia", "Greece")
    ],
    "UEFA_C5": [
        ("Moldova", "Romania"),
        ("Cyprus", "Moldova")
    ],
    "UEFA_C6": [
        ("Armenia", "Kazakhstan"),
        ("Belarus", "Armenia")
    ]

}

########################################
# SIMULATION FUNCTIONS (adapted from fullsim.py + your match sim)
########################################
NUM_SIMULATIONS = 10000

def simulate_match(team1, team2):
    elo1 = ELO_RATINGS.get(team1, 1500)
    elo2 = ELO_RATINGS.get(team2, 1500)
    rating_diff = abs(elo1 - elo2)
    base_lambda = 2.5 + 0.001 * rating_diff
    base_lambda = max(1.8, min(3.8, base_lambda))
    exp1 = 10 ** (elo1 / 400)
    exp2 = 10 ** (elo2 / 400)
    share1 = exp1 / (exp1 + exp2)
    lambda1 = base_lambda * share1
    lambda2 = base_lambda * (1 - share1)
    g1, g2 = sample_bivariate_poisson_goals(lambda1, lambda2, correlation=0.15)
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

    # Sample goals (bivariate Poisson)
    goals_a, goals_b = sample_bivariate_poisson_goals(lambda_a, lambda_b, correlation=0.12)

    # Determine winner
    if goals_a > goals_b:
        return team_a
    elif goals_b > goals_a:
        return team_b
    else:
        # Penalties: 55-45 based on ELO
        if rating_a > rating_b:
            return team_a if random.random() < 0.55 else team_b
        else:
            return team_b if random.random() < 0.55 else team_a

def simulate_playoffs(playoff_teams):
    """
    Simulate UEFA play-offs: 32 teams, two rounds of knockout.
    Returns the 8 winners (7 direct qualifiers + 1 inter-confederation).
    """
    teams = playoff_teams[:]
    random.shuffle(teams)

    # Round 1: 32 to 16
    round1_winners = []
    for i in range(0, 32, 2):
        winner = simulate_knockout_match(teams[i], teams[i+1])
        round1_winners.append(winner)

    # Round 2: 16 to 8
    round2_winners = []
    for i in range(0, 16, 2):
        winner = simulate_knockout_match(round1_winners[i], round1_winners[i+1])
        round2_winners.append(winner)

    return round2_winners

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

def simulate_group_full(group_name, teams, current_standings, remaining_matches=None):
    """Simulate one full realization of the group (current + remaining matches)."""
    table = {team: {"P":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"PTS":0} for team in teams}
    # Merge current standings
    if group_name in current_standings:
        for team, stats in current_standings[group_name].items():
            if team in table:
                table[team].update(stats)

    # Simulate remaining matches
    if remaining_matches and group_name in remaining_matches:
        for t1, t2 in remaining_matches[group_name]:
            g1, g2 = simulate_match(t1, t2)
            update_table(table, t1, t2, g1, g2)
    else:
        # Fallback: simulate all possible matches if no remaining specified (for groups starting from 0)
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                t1, t2 = teams[i], teams[j]
                g1, g2 = simulate_match(t1, t2)
                update_table(table, t1, t2, g1, g2)

    # Sort standings: PTS > GD > GF
    ranking = sorted(table.items(), key=lambda x: (x[1]["PTS"], x[1]["GD"], x[1]["GF"]), reverse=True)
    return ranking, table

def simulate_home_away(team1, team2, home1_first=True):
    # Simulate two legs: if home1_first, team1 home first, team2 home second
    if home1_first:
        g1_1, g2_1 = simulate_match(team1, team2)  # team1 home
        g1_2, g2_2 = simulate_match(team2, team1)  # team2 home second
    else:
        g1_1, g2_1 = simulate_match(team2, team1)  # team2 home first
        g1_2, g2_2 = simulate_match(team1, team2)  # team1 home second
    agg1 = g1_1 + g1_2
    agg2 = g2_1 + g2_2
    if agg1 > agg2:
        return team1
    elif agg2 > agg1:
        return team2
    else:
        # Penalties: 55-45 based on ELO
        elo1 = ELO_RATINGS.get(team1, 1500)
        elo2 = ELO_RATINGS.get(team2, 1500)
        if elo1 > elo2:
            return team1 if random.random() < 0.55 else team2
        else:
            return team2 if random.random() < 0.55 else team1

def run_monte_carlo(pbar):
    uefa_qual_counts = defaultdict(int)

    for _ in range(NUM_SIMULATIONS):
        # Simulate all groups
        group_rankings = {}
        for group_name, teams in GROUPS.items():
            ranking, _ = simulate_group_full(group_name, teams, CURRENT_STANDINGS, REMAINING_MATCHES)
            group_rankings[group_name] = ranking

        # Direct qualifiers: top 1 from each League A
        direct_qualifiers = [group_rankings[f"UEFA_A{i}"][0][0] for i in range(1, 5)]

        # Collect Path 1 participants
        path1_seeded = []
        path1_unseeded = []
        # League A runners-up and 3rd (seeded)
        for g in ["UEFA_A1","UEFA_A2","UEFA_A3","UEFA_A4"]:
            path1_seeded.append(group_rankings[g][1][0])  # runner-up
            path1_seeded.append(group_rankings[g][2][0])  # 3rd
        # League C winners (unseeded)
        for g in ["UEFA_C1","UEFA_C2","UEFA_C3","UEFA_C4","UEFA_C5","UEFA_C6"]:
            path1_unseeded.append(group_rankings[g][0][0])
        # Best 2 runners-up from C (unseeded)
        c_runners_up = [(group_rankings[g][1][0], group_rankings[g][1][1]["PTS"], group_rankings[g][1][1]["GD"], group_rankings[g][1][1]["GF"]) for g in ["UEFA_C1","UEFA_C2","UEFA_C3","UEFA_C4","UEFA_C5","UEFA_C6"]]
        c_runners_up.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
        path1_unseeded.extend([team for team, _, _, _ in c_runners_up[:2]])

        # Collect Path 2 participants
        path2_seeded = []
        path2_unseeded = []
        # League A 4th (seeded)
        for g in ["UEFA_A1","UEFA_A2","UEFA_A3","UEFA_A4"]:
            path2_seeded.append(group_rankings[g][3][0])
        # League B winners (seeded)
        for g in ["UEFA_B1","UEFA_B2","UEFA_B3","UEFA_B4"]:
            path2_seeded.append(group_rankings[g][0][0])
        # League B runners-up and 3rd (unseeded)
        for g in ["UEFA_B1","UEFA_B2","UEFA_B3","UEFA_B4"]:
            path2_unseeded.append(group_rankings[g][1][0])  # runner-up
            path2_unseeded.append(group_rankings[g][2][0])  # 3rd

        # Round 1: simulate ties in each path
        def simulate_round1(seeded, unseeded):
            random.shuffle(unseeded)
            winners = []
            for i in range(len(seeded)):
                team_s = seeded[i]
                team_u = unseeded[i]
                winner = simulate_home_away(team_s, team_u, home1_first=False)  # seeded hosts second leg
                winners.append(winner)
            return winners

        path1_winners = simulate_round1(path1_seeded, path1_unseeded)
        path2_winners = simulate_round1(path2_seeded, path2_unseeded)

        # Round 2: pair Path 1 winners (seeded) vs Path 2 winners (unseeded)
        random.shuffle(path2_winners)
        round2_winners = []
        for i in range(8):
            team_s = path1_winners[i]
            team_u = path2_winners[i]
            winner = simulate_home_away(team_s, team_u, home1_first=False)  # seeded hosts second
            round2_winners.append(winner)

        # Sort winners by league ranking (position in group, lower better)
        def get_league_rank(team):
            for group, ranking in group_rankings.items():
                for pos, (t, _) in enumerate(ranking, 1):
                    if t == team:
                        return pos, group  # position, group
            return 99, ""  # fallback

        round2_winners.sort(key=lambda t: get_league_rank(t))

        # Top 7 qualify, 8th inter
        qualifiers = round2_winners[:7] + direct_qualifiers
        inter_team = round2_winners[7]

        # Count
        for team in qualifiers:
            uefa_qual_counts[team] += 1
        uefa_qual_counts[inter_team] += 1  # inter

        pbar.update(1)

    uefa_qual_probs = {team: round(count / NUM_SIMULATIONS * 100, 1) for team, count in uefa_qual_counts.items()}

    return uefa_qual_probs

def run_concacaf_simulation(pbar):
    # CONCACAF Championship QF matches as per fixture
    qf_matches = [
        ("USA", "El Salvador"),
        ("Jamaica", "Costa Rica"),
        ("Canada", "Panama"),
        ("Mexico", "Haiti")
    ]

    qual_counts = {team: 0 for team in ["USA", "El Salvador", "Jamaica", "Costa Rica", "Canada", "Panama", "Mexico", "Haiti"]}

    for _ in range(NUM_SIMULATIONS):
        # Simulate QF
        qf_winners = []
        qf_losers = []
        for t1, t2 in qf_matches:
            g1, g2 = simulate_match(t1, t2)
            if g1 > g2:
                winner = t1
            elif g2 > g1:
                winner = t2
            else:
                winner = t1 if ELO_RATINGS.get(t1, 1500) > ELO_RATINGS.get(t2, 1500) else t2
            qf_winners.append(winner)
            loser = t2 if winner == t1 else t1
            qf_losers.append(loser)

        # Direct qualifiers: QF winners
        direct_qualifiers = qf_winners

        # Losers play play-in matches randomly paired
        random.shuffle(qf_losers)
        g1, g2 = simulate_match(qf_losers[0], qf_losers[1])
        playin1_winner = qf_losers[0] if g1 > g2 else qf_losers[1] if g2 > g1 else (qf_losers[0] if ELO_RATINGS.get(qf_losers[0], 1500) > ELO_RATINGS.get(qf_losers[1], 1500) else qf_losers[1])
        g3, g4 = simulate_match(qf_losers[2], qf_losers[3])
        playin2_winner = qf_losers[2] if g3 > g4 else qf_losers[3] if g4 > g3 else (qf_losers[2] if ELO_RATINGS.get(qf_losers[2], 1500) > ELO_RATINGS.get(qf_losers[3], 1500) else qf_losers[3])
        inter_qualifiers = [playin1_winner, playin2_winner]

        # Record qualification
        for team in direct_qualifiers + inter_qualifiers:
            qual_counts[team] += 1

        pbar.update(1)

    concacaf_qual_probs = {team: round(qual_counts[team] / NUM_SIMULATIONS * 100, 1) for team in qual_counts}



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
    qual_counts = {team: 0 for team in ["Morocco", "Algeria", "Senegal", "Kenya", "South Africa", "Côte d'Ivoire", "Burkina Faso", "Tanzania", "Nigeria", "Zambia", "Egypt", "Malawi", "Ghana", "Cameroon", "Mali", "Cape Verde"]}

    for _ in range(NUM_SIMULATIONS):
        # Simulate group stage to get top 2 from each group
        group_top2 = {}
        for group_name, teams in CAF_GROUPS.items():
            ranking, _ = simulate_group_full(group_name, teams, CAF_STANDINGS)
            group_top2[group_name] = [ranking[0][0], ranking[1][0]]  # Top 2

        # Simulate quarter-finals: A1 vs B1, C1 vs D1, A2 vs B2, C2 vs D2
        qf1_winner = simulate_knockout_match(group_top2["CAF_A"][0], group_top2["CAF_B"][0])
        qf2_winner = simulate_knockout_match(group_top2["CAF_C"][0], group_top2["CAF_D"][0])
        qf3_winner = simulate_knockout_match(group_top2["CAF_A"][1], group_top2["CAF_B"][1])
        qf4_winner = simulate_knockout_match(group_top2["CAF_C"][1], group_top2["CAF_D"][1])

        # Direct qualifiers: all QF winners
        direct_qualifiers = [qf1_winner, qf2_winner, qf3_winner, qf4_winner]

        # Losers play play-in matches randomly
        all_top2 = [team for sublist in group_top2.values() for team in sublist]
        losers = [team for team in all_top2 if team not in direct_qualifiers]
        random.shuffle(losers)
        playin1_winner = simulate_knockout_match(losers[0], losers[1])
        playin2_winner = simulate_knockout_match(losers[2], losers[3])
        inter_conf_qualifiers = [playin1_winner, playin2_winner]

        # Record qualification (direct + inter-confederation)
        for team in direct_qualifiers + inter_conf_qualifiers:
            qual_counts[team] += 1

        pbar.update(1)

    # Collect qual probs
    caf_qual_probs = {team: round(qual_counts[team] / NUM_SIMULATIONS * 100, 1) for team in qual_counts}

    return caf_qual_probs

def run_conmebol_simulation(pbar):
    qual_counts = {team: 0 for team in CONMEBOL_GROUP}

    for _ in range(NUM_SIMULATIONS):
        ranking, _ = simulate_group_full("CONMEBOL", CONMEBOL_GROUP, {"CONMEBOL": CONMEBOL_STANDINGS}, {"CONMEBOL": REMAINING_MATCHES_CONMEBOL})

        # Top 2 direct qualifiers
        direct_qualifiers = [ranking[0][0], ranking[1][0]]

        # 3rd and 4th to inter-confederation
        inter_qualifiers = [ranking[2][0], ranking[3][0]]

        for team in direct_qualifiers + inter_qualifiers:
            qual_counts[team] += 1

        pbar.update(1)

    conmebol_qual_probs = {team: round(qual_counts[team] / NUM_SIMULATIONS * 100, 1) for team in CONMEBOL_GROUP}

    return conmebol_qual_probs

if __name__ == "__main__":
    print("=== 2027 WOMEN'S WORLD CUP QUALIFICATION SIMULATOR ===")
    print("Running simulations for all confederations...\n")

    total_sims = 10000 * 5  # UEFA, CONCACAF, CAF, CONMEBOL, OFC
    with tqdm(total=total_sims, desc="Overall qualification simulations") as pbar:
        uefa_probs = run_monte_carlo(pbar)
        concacaf_probs = run_concacaf_simulation(pbar)
        caf_probs = run_caf_simulation(pbar)
        conmebol_probs = run_conmebol_simulation(pbar)
        ofc_probs = run_ofc_simulation(pbar)

        # Combine all qualification probabilities
        all_qual_probs = {**uefa_probs, **concacaf_probs, **caf_probs, **conmebol_probs, **ofc_probs}

        # Add definitely qualified teams (already qualified)
        definitely_qualified = {
            'Australia': 100.0,
            'China': 100.0,
            'Japan': 100.0,
            'North Korea': 100.0,
            'South Korea': 100.0,
            'Brazil': 100.0,
            'New Zealand': 100.0
        }

        # Inter-confederation playoff participants (approx 50% chance for 6-team final knockout)
        inter_confederation = {
            'Philippines': 50.0,
            'Chinese Taipei': 50.0,
            'Uzbekistan': 50.0,
            'Papua New Guinea': 50.0
        }
        all_qual_probs.update(definitely_qualified)
        all_qual_probs.update(inter_confederation)

        # Sort by probability descending
        sorted_teams = sorted(all_qual_probs.items(), key=lambda x: x[1], reverse=True)

        print("\n### All Teams Qualification Probabilities (Descending Order)")
        for team, prob in sorted_teams:
            if prob > 0:  # Only include teams with chance
                print(f"{team}: {prob}%")

        print("\nSimulation complete. Probabilities reflect remaining matches via Monte Carlo.")