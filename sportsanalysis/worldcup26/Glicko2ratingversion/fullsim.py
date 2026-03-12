import pandas as pd
import numpy as np
import random
from tqdm import tqdm
from itertools import product
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import json
import os


number_of_qualfied_teams = 48
# Choose mode
mode = input("Choose mode: 1 for 'most_likely' (picks most likely qualifiers), 2 for 'all' (simulates all group possibilities): ")
if mode == '1':
    mode = 'most_likely'
elif mode == '2':
    mode = 'all'
else:
    mode = 'all'  # default

# -------------------------
# CONFIG / GROUPS (no 'points' entries)
# -------------------------
GROUPS = {
    'A': {
        'teams': ['Mexico', 'South Africa', 'South Korea', 'UEFA_Path_D_Winner'],
        'matches': [
            ('Mexico', 'South Africa'),
            ('South Korea', 'UEFA_Path_D_Winner'),
            ('UEFA_Path_D_Winner', 'South Africa'),
            ('Mexico', 'South Korea'),
            ('UEFA_Path_D_Winner', 'Mexico'),
            ('South Africa', 'South Korea')
        ],
        'possible_winners': {
            'UEFA_Path_D_Winner': ['Denmark', 'North Macedonia', 'Czech Republic', 'Republic of Ireland']
        }
    },
    'B': {
        'teams': ['Canada', 'Qatar', 'Switzerland', 'UEFA_Path_A_Winner'],
        'matches': [
            ('Canada', 'UEFA_Path_A_Winner'),
            ('Qatar', 'Switzerland'),
            ('Switzerland', 'UEFA_Path_A_Winner'),
            ('Canada', 'Qatar'),
            ('Switzerland', 'Canada'),
            ('UEFA_Path_A_Winner', 'Qatar')
        ],
        'possible_winners': {
            'UEFA_Path_A_Winner': ['Italy', 'Northern Ireland', 'Wales', 'Bosnia and Herzegovina']
        }
    },
    'C': {
        'teams': ['Brazil', 'Morocco', 'Haiti', 'Scotland'],
        'matches': [
            ('Brazil', 'Morocco'),
            ('Haiti', 'Scotland'),
            ('Brazil', 'Haiti'),
            ('Scotland', 'Morocco'),
            ('Scotland', 'Brazil'),
            ('Morocco', 'Haiti')
        ]
    },
    'D': {
        'teams': ['United States', 'Paraguay', 'Australia', 'UEFA_Path_C_Winner'],
        'matches': [
            ('United States', 'Paraguay'),
            ('Australia', 'UEFA_Path_C_Winner'),
            ('UEFA_Path_C_Winner', 'Paraguay'),
            ('United States', 'Australia'),
            ('UEFA_Path_C_Winner', 'United States'),
            ('Paraguay', 'Australia')
        ],
        'possible_winners': {
            'UEFA_Path_C_Winner': [('Turkey'), ('Romania'), ('Slovakia'), ('Kosovo')]
        }
    },
    'E': {
        'teams': ['Germany', 'Curaçao', 'Ivory Coast', 'Ecuador'],
        'matches': [
            ('Germany', 'Curaçao'),
            ('Ivory Coast', 'Ecuador'),
            ('Germany', 'Ivory Coast'),
            ('Ecuador', 'Curaçao'),
            ('Ecuador', 'Germany'),
            ('Curaçao', 'Ivory Coast')
        ]
    },
    'F': {
        'teams': ['Netherlands', 'Japan', 'UEFA_Path_B_Winner', 'Tunisia'],
        'matches': [
            ('Netherlands', 'Japan'),
            ('UEFA_Path_B_Winner', 'Tunisia'),
            ('Netherlands', 'UEFA_Path_B_Winner'),
            ('Tunisia', 'Japan'),
            ('Tunisia', 'Netherlands'),
            ('Japan', 'UEFA_Path_B_Winner')
        ],
        'possible_winners': {
            'UEFA_Path_B_Winner': [('Ukraine'), ('Sweden'), ('Poland'), ('Albania')]
        }
    },
    'G': {
        'teams': ['Belgium', 'Egypt', 'Iran', 'New Zealand'],
        'matches': [
            ('Belgium', 'Egypt'),
            ('Iran', 'New Zealand'),
            ('Belgium', 'Iran'),
            ('New Zealand', 'Egypt'),
            ('New Zealand', 'Belgium'),
            ('Egypt', 'Iran')
        ]
    },
    'H': {
        'teams': ['Spain', 'Cape Verde', 'Saudi Arabia', 'Uruguay'],
        'matches': [
            ('Spain', 'Cape Verde'),
            ('Saudi Arabia', 'Uruguay'),
            ('Spain', 'Saudi Arabia'),
            ('Uruguay', 'Cape Verde'),
            ('Uruguay', 'Spain'),
            ('Cape Verde', 'Saudi Arabia')
        ]
    },
    'I': {
        'teams': ['France', 'Senegal', 'IC_Path_2_Winner', 'Norway'],
        'matches': [
            ('France', 'Senegal'),
            ('IC_Path_2_Winner', 'Norway'),
            ('France', 'IC_Path_2_Winner'),
            ('Norway', 'Senegal'),
            ('Norway', 'France'),
            ('Senegal', 'IC_Path_2_Winner')
        ],
        'possible_winners': {
            'IC_Path_2_Winner': [('Iraq'), ('Bolivia'), ('Suriname')]
        }
    },
    'J': {
        'teams': ['Argentina', 'Algeria', 'Austria', 'Jordan'],
        'matches': [
            ('Argentina', 'Algeria'),
            ('Austria', 'Jordan'),
            ('Argentina', 'Austria'),
            ('Jordan', 'Algeria'),
            ('Jordan', 'Argentina'),
            ('Algeria', 'Austria')
        ]
    },
    'K': {
        'teams': ['Portugal', 'IC_Path_1_Winner', 'Uzbekistan', 'Colombia'],
        'matches': [
            ('Portugal', 'IC_Path_1_Winner'),
            ('Uzbekistan', 'Colombia'),
            ('Portugal', 'Uzbekistan'),
            ('Colombia', 'IC_Path_1_Winner'),
            ('Colombia', 'Portugal'),
            ('IC_Path_1_Winner', 'Uzbekistan')
        ],
        'possible_winners': {
            'IC_Path_1_Winner': [('DR Congo'), ('Jamaica'), ('New Caledonia')]
        }
    },
    'L': {
        'teams': ['England', 'Croatia', 'Panama', 'Ghana'],
        'matches': [
            ('England', 'Croatia'),
            ('England', 'Panama'),
            ('England', 'Ghana'),
            ('Croatia', 'Panama'),
            ('Croatia', 'Ghana'),
            ('Panama', 'Ghana')
        ]
    }
}

# -------------------------
# HOME ADVANTAGE BONUSES
# -------------------------
home_bonuses = {
    'Mexico': 55.2,
    'United States': 55.2,
    'Canada': 55.2
}

# -------------------------
# TEAM RATINGS (Elo-like)
# -------------------------
teams_ratings = {
    'Spain': 2010.31,
    'Argentina': 2005.13,
    'Colombia': 1941.47,
    'France': 1935.09,
    'Brazil': 1929.06,
    'England': 1919.37,
    'Portugal': 1896.48,
    'Netherlands': 1881.9,
    'Ecuador': 1869.22,
    'Croatia': 1862.02,
    'Germany': 1853.14,
    'Switzerland': 1845.99,
    'Uruguay': 1842.77,
    'Japan': 1839.04,
    'Norway': 1834.66,
    'Denmark': 1822.66,
    'Morocco': 1818.6,
    'Belgium': 1818.32,
    'Italy': 1817.76,
    'Turkey': 1803.71,
    'Canada': 1803.26,
    'Senegal': 1797.5,
    'Austria': 1791.3,
    'South Korea': 1790.73,
    'Paraguay': 1784.82,
    'Mexico': 1784.5,
    'Iran': 1781.23,
    'Australia': 1777.02,
    'Ukraine': 1766.95,
    'United States': 1763.4,
    'Serbia': 1762.86,
    'Algeria': 1762.12,
    'Basque Country': 1762.07,
    'Chile': 1756.48,
    'Russia': 1754.01,
    'Uzbekistan': 1746.25,
    'Poland': 1738.7,
    'Greece': 1737.62,
    'Czechoslovakia': 1732.78,
    'Jersey': 1726.81,
    'Yugoslavia': 1726.12,
    'Panama': 1725.25,
    'Scotland': 1724.78,
    'Czech Republic': 1721.53,
    'Venezuela': 1716.84,
    'Tunisia': 1709.0,
    'Peru': 1708.32,
    'German DR': 1708.01,
    'Costa Rica': 1702.45,
    'Slovenia': 1699.94,
    'Sweden': 1699.42,
    'Wales': 1694.45,
    'Jordan': 1690.49,
    'Hungary': 1687.01,
    'Guernsey': 1685.56,
    'Kosovo': 1685.16,
    'Congo DR': 1682.99,
    'Nigeria': 1681.78,
    'Ivory Coast': 1681.6,
    'Slovakia': 1677.08,
    'New Zealand': 1675.23,
    'Ireland': 1674.94,
    'Occitania': 1667.17,
    'Egypt': 1665.88,
    'Mali': 1665.41,
    'Isle of Man': 1663.0,
    'Albania': 1660.52,
    'Burkina Faso': 1660.45,
    'Georgia': 1659.34,
    'Catalonia': 1659.23,
    'Bolivia': 1658.75,
    'Padania': 1652.52,
    'Saudi Arabia': 1651.32,
    'Iraq': 1646.65,
    'Cape Verde': 1643.65,
    'Romania': 1643.37,
    'Israel': 1640.05,
    'Northern Cyprus': 1639.95,
    'Haiti': 1636.48,
    'Cameroon': 1629.98,
    'Northern Ireland': 1627.64,
    'South Africa': 1626.84,
    'Honduras': 1625.49,
    'Iraqi Kurdistan': 1618.56,
    'United Arab Emirates': 1617.67,
    'Isle of Wight': 1617.55,
    'Jamaica': 1614.12,
    'Iceland': 1613.39,
    'Guatemala': 1610.86,
    'Ghana': 1609.98,
    'Kernow': 1606.33,
    'Bosnia and Herzegovina': 1605.79,
    'Ynys Môn': 1598.7,
    'Abkhazia': 1596.98,
    'North Macedonia': 1593.01,
    'Andalusia': 1591.94,
    'Angola': 1586.2,
    'Kárpátalja': 1582.11,
    'Panjab': 1581.37,
    'Guinea': 1580.55,
    'New Caledonia': 1579.65,
    'Reunion': 1574.13,
    'Finland': 1572.86,
    'County of Nice': 1572.43,
    'Oman': 1570.96,
    'Rhodes': 1569.11,
    'Syria': 1568.94,
    'Ellan Vannin': 1563.61,
    'Yorkshire': 1560.13,
    'Belarus': 1558.65,
    'Palestine': 1557.77,
    'Menorca': 1555.56,
    'Gabon': 1553.83,
    'Artsakh': 1550.63,
    'Corsica': 1550.49,
    'Chameria': 1547.42,
    'Cascadia': 1545.85,
    'Arameans Suryoye': 1536.1,
    'Libya': 1535.88,
    'Trinidad and Tobago': 1535.64,
    'Suriname': 1532.12,
    'Zanzibar': 1530.98,
    'Thailand': 1528.06,
    'Gambia': 1527.79,
    'Bahrain': 1525.88,
    'Qatar': 1525.68,
    'Asturias': 1524.4,
    'Western Armenia': 1524.31,
    'Maule Sur': 1520.56,
    'Benin': 1520.55,
    'China': 1520.09,
    'Uganda': 1519.83,
    'Bulgaria': 1519.8,
    'Galicia': 1519.08,
    'Canary Islands': 1518.43,
    'Zambia': 1516.92,
    'Surrey': 1516.33,
    'United Koreans in Japan': 1514.86,
    'Parishes of Jersey': 1514.85,
    'Montenegro': 1514.7,
    'Madagascar': 1513.93,
    'Donetsk PR': 1513.61,
    'Silesia': 1513.46,
    'Guadeloupe': 1512.2,
    'Shetland': 1510.39,
    'North Korea': 1510.21,
    'Biafra': 1510.19,
    'Elba Island': 1507.54,
    'El Salvador': 1507.35,
    'Mapuche': 1507.05,
    'Equatorial Guinea': 1506.51,
    'Felvidék': 1505.88,
    'Sudan': 1504.32,
    'Sealand': 1503.16,
    'North Vietnam': 1501.78,
    'Tahiti': 1501.49,
    'Tamil Eelam': 1500.9,
    'Curaçao': 1500.61,
    'Délvidék': 1499.75,
    'Martinique': 1499.58,
    'Malaysia': 1497.38,
    'Sápmi': 1496.32,
    'Mozambique': 1496.3,
    'Crimea': 1496.06,
    'Brittany': 1495.0,
    'Székely Land': 1494.35,
    'Central Spain': 1493.04,
    'Western Sahara': 1492.81,
    'West Papua': 1492.7,
    'Saugeais': 1491.68,
    'Kazakhstan': 1491.36,
    'Nicaragua': 1491.36,
    'Cilento': 1490.56,
    'Republic of St. Pauli': 1490.5,
    'Madrid': 1490.33,
    'Dominican Republic': 1489.32,
    'Luhansk PR': 1487.56,
    'Yoruba Nation': 1487.53,
    'Greenland': 1487.04,
    'Seborga': 1485.47,
    'Sierra Leone': 1484.54,
    'South Ossetia': 1481.98,
    'Vietnam': 1481.36,
    'Kuwait': 1480.34,
    'Gozo': 1479.67,
    'Matabeleland': 1479.63,
    'Franconia': 1478.33,
    'Luxembourg': 1478.2,
    'Kenya': 1478.08,
    'Somaliland': 1477.54,
    'Comoros': 1477.11,
    'South Yemen': 1476.41,
    'Åland Islands': 1476.01,
    'Kyrgyzstan': 1473.87,
    'Zimbabwe': 1473.34,
    'Togo': 1473.05,
    'Guyana': 1472.64,
    'Aymara': 1472.39,
    'Armenia': 1471.63,
    'Lebanon': 1469.73,
    'Estonia': 1469.15,
    'Indonesia': 1468.87,
    'Mayotte': 1468.56,
    'Provence': 1468.33,
    'Romani people': 1465.51,
    'Gotland': 1464.94,
    'Niger': 1463.95,
    'Kabylia': 1463.89,
    'Ryūkyū': 1462.71,
    'Hmong': 1462.5,
    'Mauritania': 1461.73,
    'French Guiana': 1460.8,
    'Botswana': 1457.71,
    'Faroe Islands': 1452.36,
    'Malawi': 1451.36,
    'Monaco': 1449.33,
    'Papua New Guinea': 1448.25,
    'Niue': 1445.61,
    'Saarland': 1445.05,
    'Azerbaijan': 1444.96,
    'Tajikistan': 1443.84,
    'Western Isles': 1440.34,
    'Găgăuzia': 1440.3,
    'Burundi': 1440.14,
    'Rwanda': 1438.9,
    'Chechnya': 1437.12,
    'Namibia': 1436.09,
    'Central African Republic': 1435.53,
    'Two Sicilies': 1433.91,
    'Cuba': 1433.41,
    'Marshall Islands': 1433.07,
    'Solomon Islands': 1432.88,
    'Vanuatu': 1432.79,
    'Tanzania': 1431.46,
    'St. Vincent / Grenadines': 1428.09,
    'Fiji': 1427.02,
    'Western Australia': 1426.83,
    'Ticino': 1422.99,
    'Ethiopia': 1419.17,
    'Manchukuo': 1418.78,
    'Orkney': 1415.34,
    'Liberia': 1415.13,
    'Guinea-Bissau': 1414.63,
    'Raetia': 1413.06,
    'Saint Barthélemy': 1411.81,
    'Ambazonia': 1409.36,
    'Latvia': 1403.44,
    'Cyprus': 1401.81,
    'Lithuania': 1401.72,
    'Vatican City': 1400.57,
    'Palau': 1399.02,
    'Moldova': 1398.2,
    'Turkmenistan': 1397.59,
    'Vietnam Republic': 1396.92,
    'Congo': 1394.43,
    'Malta': 1393.28,
    'Lesotho': 1392.31,
    'Yemen DPR': 1391.01,
    'Belize': 1389.8,
    'Eswatini': 1389.73,
    'Hong Kong': 1382.71,
    'Saare County': 1381.61,
    'Puerto Rico': 1378.77,
    'Barawa': 1375.35,
    'Bermuda': 1373.5,
    'Saint Helena': 1371.27,
    'Hitra': 1371.01,
    'Chagos Islands': 1367.03,
    'Sark': 1364.75,
    'Philippines': 1360.37,
    'Yemen': 1354.89,
    'Micronesia': 1351.63,
    'Grenada': 1343.86,
    'Sint Maarten': 1334.41,
    'Singapore': 1332.32,
    'South Sudan': 1329.98,
    'India': 1329.71,
    'Wallis Islands and Futuna': 1329.61,
    'Chad': 1327.9,
    'St. Kitts and Nevis': 1322.93,
    'Darfur': 1322.62,
    'Saint Martin': 1320.59,
    'Tibet': 1319.74,
    'Saint Pierre and Miquelon': 1316.1,
    'Samoa': 1294.43,
    'St. Lucia': 1293.9,
    'Afghanistan': 1292.1,
    'Mauritius': 1292.08,
    'Kiribati': 1290.65,
    'Montserrat': 1287.99,
    'Aruba': 1287.69,
    'Eritrea': 1277.38,
    'Falkland Islands': 1275.09,
    'Tuvalu': 1270.04,
    'Andorra': 1267.04,
    'Sao Tome e Principe': 1263.88,
    'Dominica': 1258.43,
    'Barbados': 1258.42,
    'Frøya': 1249.89,
    'Gibraltar': 1246.92,
    'Cook Islands': 1237.16,
    'Antigua and Barbuda': 1230.72,
    'Nepal': 1229.2,
    'Bonaire': 1228.49,
    'Bangladesh': 1226.46,
    'Myanmar': 1218.4,
    'Taiwan': 1210.84,
    'Djibouti': 1187.35,
    'Cayman Islands': 1184.93,
    'Tonga': 1177.32,
    'Maldives': 1176.77,
    'Somalia': 1172.06,
    'Cambodia': 1163.95,
    'Alderney': 1161.98,
    'Seychelles': 1152.74,
    'British Virgin Islands': 1152.58,
    'Liechtenstein': 1149.7,
    'Bahamas': 1136.74,
    'Pakistan': 1135.59,
    'Turks and Caicos Islands': 1135.25,
    'Mongolia': 1131.97,
    'Sri Lanka': 1130.85,
    'Guam': 1125.66,
    'United States Virgin Islands': 1115.61,
    'American Samoa': 1088.67,
    'Northern Mariana Islands': 1087.4,
    'Laos': 1077.06,
    'San Marino': 1076.62,
    'Anguilla': 1062.54,
    'Timor-Leste': 1049.8,
    'Brunei': 1048.39,
    'Macau': 1027.09,
    'Bhutan': 1012.91,
}

# -------------------------
# LOAD GLICKO-2 RATINGS
# -------------------------
glicko_path = os.path.join(os.path.dirname(__file__), "glicko_ratings.json")
if os.path.exists(glicko_path):
    print(f"Loading Glicko-2 ratings from {glicko_path}...")
    with open(glicko_path, "r") as f:
        glicko_ratings = json.load(f)
        # Update existing ratings and add new ones
        for team, rating in glicko_ratings.items():
            teams_ratings[team] = rating
    print("Glicko-2 ratings loaded successfully.")
else:
    print(f"No Glicko-2 ratings file found at {glicko_path}. Using default Elo-like ratings.")


# Collect all possible teams (direct teams and qualifying candidates)
all_possible_teams = set()
for group in GROUPS.values():
    for team in group['teams']:
        if team in teams_ratings:
            all_possible_teams.add(team)
        elif 'possible_winners' in group:
            for ph, opts in group['possible_winners'].items():
                if team == ph:
                    for o in opts:
                        team_name = o[0] if isinstance(o, tuple) else o
                        all_possible_teams.add(team_name)
all_possible_teams = list(all_possible_teams)

# Limit teams_ratings to only include teams that are in the tournament or can still qualify
teams_ratings = {
    'Spain': 2010.31,
    'Argentina': 2005.13,
    'Colombia': 1941.47,
    'France': 1935.09,
    'Brazil': 1929.06,
    'England': 1919.37,
    'Portugal': 1896.48,
    'Netherlands': 1881.9,
    'Ecuador': 1869.22,
    'Croatia': 1862.02,
    'Germany': 1853.14,
    'Switzerland': 1845.99,
    'Uruguay': 1842.77,
    'Japan': 1839.04,
    'Norway': 1834.66,
    'Denmark': 1822.66,
    'Morocco': 1818.6,
    'Belgium': 1818.32,
    'Italy': 1817.76,
    'Turkey': 1803.71,
    'Canada': 1803.26,
    'Senegal': 1797.5,
    'Austria': 1791.3,
    'South Korea': 1790.73,
    'Paraguay': 1784.82,
    'Mexico': 1784.5,
    'Iran': 1781.23,
    'Australia': 1777.02,
    'Ukraine': 1766.95,
    'USA': 1763.4,
    'Serbia': 1762.86,
    'Algeria': 1762.12,
    'Basque Country': 1762.07,
    'Chile': 1756.48,
    'Russia': 1754.01,
    'Uzbekistan': 1746.25,
    'Poland': 1738.7,
    'Greece': 1737.62,
    'Czechoslovakia': 1732.78,
    'Jersey': 1726.81,
    'Yugoslavia': 1726.12,
    'Panama': 1725.25,
    'Scotland': 1724.78,
    'Czech Republic': 1721.53,
    'Venezuela': 1716.84,
    'Tunisia': 1709.0,
    'Peru': 1708.32,
    'German DR': 1708.01,
    'Costa Rica': 1702.45,
    'Slovenia': 1699.94,
    'Sweden': 1699.42,
    'Wales': 1694.45,
    'Jordan': 1690.49,
    'Hungary': 1687.01,
    'Guernsey': 1685.56,
    'Kosovo': 1685.16,
    'Congo DR': 1682.99,
    'Nigeria': 1681.78,
    'Ivory Coast': 1681.6,
    'Slovakia': 1677.08,
    'New Zealand': 1675.23,
    'Ireland': 1674.94,
    'Occitania': 1667.17,
    'Egypt': 1665.88,
    'Mali': 1665.41,
    'Isle of Man': 1663.0,
    'Albania': 1660.52,
    'Burkina Faso': 1660.45,
    'Georgia': 1659.34,
    'Catalonia': 1659.23,
    'Bolivia': 1658.75,
    'Padania': 1652.52,
    'Saudi Arabia': 1651.32,
    'Iraq': 1646.65,
    'Cape Verde': 1643.65,
    'Romania': 1643.37,
    'Israel': 1640.05,
    'Northern Cyprus': 1639.95,
    'Haiti': 1636.48,
    'Cameroon': 1629.98,
    'Northern Ireland': 1627.64,
    'South Africa': 1626.84,
    'Honduras': 1625.49,
    'Iraqi Kurdistan': 1618.56,
    'United Arab Emirates': 1617.67,
    'Isle of Wight': 1617.55,
    'Jamaica': 1614.12,
    'Iceland': 1613.39,
    'Guatemala': 1610.86,
    'Ghana': 1609.98,
    'Kernow': 1606.33,
    'Bosnia and Herzegovina': 1605.79,
    'Ynys Môn': 1598.7,
    'Abkhazia': 1596.98,
    'North Macedonia': 1593.01,
    'Andalusia': 1591.94,
    'Angola': 1586.2,
    'Kárpátalja': 1582.11,
    'Panjab': 1581.37,
    'Guinea': 1580.55,
    'New Caledonia': 1579.65,
    'Reunion': 1574.13,
    'Finland': 1572.86,
    'County of Nice': 1572.43,
    'Oman': 1570.96,
    'Rhodes': 1569.11,
    'Syria': 1568.94,
    'Ellan Vannin': 1563.61,
    'Yorkshire': 1560.13,
    'Belarus': 1558.65,
    'Palestine': 1557.77,
    'Menorca': 1555.56,
    'Gabon': 1553.83,
    'Artsakh': 1550.63,
    'Corsica': 1550.49,
    'Chameria': 1547.42,
    'Cascadia': 1545.85,
    'Arameans Suryoye': 1536.1,
    'Libya': 1535.88,
    'Trinidad and Tobago': 1535.64,
    'Suriname': 1532.12,
    'Zanzibar': 1530.98,
    'Thailand': 1528.06,
    'Gambia': 1527.79,
    'Bahrain': 1525.88,
    'Qatar': 1525.68,
    'Asturias': 1524.4,
    'Western Armenia': 1524.31,
    'Maule Sur': 1520.56,
    'Benin': 1520.55,
    'China': 1520.09,
    'Uganda': 1519.83,
    'Bulgaria': 1519.8,
    'Galicia': 1519.08,
    'Canary Islands': 1518.43,
    'Zambia': 1516.92,
    'Surrey': 1516.33,
    'United Koreans in Japan': 1514.86,
    'Parishes of Jersey': 1514.85,
    'Montenegro': 1514.7,
    'Madagascar': 1513.93,
    'Donetsk PR': 1513.61,
    'Silesia': 1513.46,
    'Guadeloupe': 1512.2,
    'Shetland': 1510.39,
    'North Korea': 1510.21,
    'Biafra': 1510.19,
    'Elba Island': 1507.54,
    'El Salvador': 1507.35,
    'Mapuche': 1507.05,
    'Equatorial Guinea': 1506.51,
    'Felvidék': 1505.88,
    'Sudan': 1504.32,
    'Sealand': 1503.16,
    'North Vietnam': 1501.78,
    'Tahiti': 1501.49,
    'Tamil Eelam': 1500.9,
    'Curaçao': 1500.61,
    'Délvidék': 1499.75,
    'Martinique': 1499.58,
    'Malaysia': 1497.38,
    'Sápmi': 1496.32,
    'Mozambique': 1496.3,
    'Crimea': 1496.06,
    'Brittany': 1495.0,
    'Székely Land': 1494.35,
    'Central Spain': 1493.04,
    'Western Sahara': 1492.81,
    'West Papua': 1492.7,
    'Saugeais': 1491.68,
    'Kazakhstan': 1491.36,
    'Nicaragua': 1491.36,
    'Cilento': 1490.56,
    'Republic of St. Pauli': 1490.5,
    'Madrid': 1490.33,
    'Dominican Republic': 1489.32,
    'Luhansk PR': 1487.56,
    'Yoruba Nation': 1487.53,
    'Greenland': 1487.04,
    'Seborga': 1485.47,
    'Sierra Leone': 1484.54,
    'South Ossetia': 1481.98,
    'Vietnam': 1481.36,
    'Kuwait': 1480.34,
    'Gozo': 1479.67,
    'Matabeleland': 1479.63,
    'Franconia': 1478.33,
    'Luxembourg': 1478.2,
    'Kenya': 1478.08,
    'Somaliland': 1477.54,
    'Comoros': 1477.11,
    'South Yemen': 1476.41,
    'Åland Islands': 1476.01,
    'Kyrgyzstan': 1473.87,
    'Zimbabwe': 1473.34,
    'Togo': 1473.05,
    'Guyana': 1472.64,
    'Aymara': 1472.39,
    'Armenia': 1471.63,
    'Lebanon': 1469.73,
    'Estonia': 1469.15,
    'Indonesia': 1468.87,
    'Mayotte': 1468.56,
    'Provence': 1468.33,
    'Romani people': 1465.51,
    'Gotland': 1464.94,
    'Niger': 1463.95,
    'Kabylia': 1463.89,
    'Ryūkyū': 1462.71,
    'Hmong': 1462.5,
    'Mauritania': 1461.73,
    'French Guiana': 1460.8,
    'Botswana': 1457.71,
    'Faroe Islands': 1452.36,
    'Malawi': 1451.36,
    'Monaco': 1449.33,
    'Papua New Guinea': 1448.25,
    'Niue': 1445.61,
    'Saarland': 1445.05,
    'Azerbaijan': 1444.96,
    'Tajikistan': 1443.84,
    'Western Isles': 1440.34,
    'Găgăuzia': 1440.3,
    'Burundi': 1440.14,
    'Rwanda': 1438.9,
    'Chechnya': 1437.12,
    'Namibia': 1436.09,
    'Central African Republic': 1435.53,
    'Two Sicilies': 1433.91,
    'Cuba': 1433.41,
    'Marshall Islands': 1433.07,
    'Solomon Islands': 1432.88,
    'Vanuatu': 1432.79,
    'Tanzania': 1431.46,
    'St. Vincent / Grenadines': 1428.09,
    'Fiji': 1427.02,
    'Western Australia': 1426.83,
    'Ticino': 1422.99,
    'Ethiopia': 1419.17,
    'Manchukuo': 1418.78,
    'Orkney': 1415.34,
    'Liberia': 1415.13,
    'Guinea-Bissau': 1414.63,
    'Raetia': 1413.06,
    'Saint Barthélemy': 1411.81,
    'Ambazonia': 1409.36,
    'Latvia': 1403.44,
    'Cyprus': 1401.81,
    'Lithuania': 1401.72,
    'Vatican City': 1400.57,
    'Palau': 1399.02,
    'Moldova': 1398.2,
    'Turkmenistan': 1397.59,
    'Vietnam Republic': 1396.92,
    'Congo': 1394.43,
    'Malta': 1393.28,
    'Lesotho': 1392.31,
    'Yemen DPR': 1391.01,
    'Belize': 1389.8,
    'Eswatini': 1389.73,
    'Hong Kong': 1382.71,
    'Saare County': 1381.61,
    'Puerto Rico': 1378.77,
    'Barawa': 1375.35,
    'Bermuda': 1373.5,
    'Saint Helena': 1371.27,
    'Hitra': 1371.01,
    'Chagos Islands': 1367.03,
    'Sark': 1364.75,
    'Philippines': 1360.37,
    'Yemen': 1354.89,
    'Micronesia': 1351.63,
    'Grenada': 1343.86,
    'Sint Maarten': 1334.41,
    'Singapore': 1332.32,
    'South Sudan': 1329.98,
    'India': 1329.71,
    'Wallis Islands and Futuna': 1329.61,
    'Chad': 1327.9,
    'St. Kitts and Nevis': 1322.93,
    'Darfur': 1322.62,
    'Saint Martin': 1320.59,
    'Tibet': 1319.74,
    'Saint Pierre and Miquelon': 1316.1,
    'Samoa': 1294.43,
    'St. Lucia': 1293.9,
    'Afghanistan': 1292.1,
    'Mauritius': 1292.08,
    'Kiribati': 1290.65,
    'Montserrat': 1287.99,
    'Aruba': 1287.69,
    'Eritrea': 1277.38,
    'Falkland Islands': 1275.09,
    'Tuvalu': 1270.04,
    'Andorra': 1267.04,
    'Sao Tome e Principe': 1263.88,
    'Dominica': 1258.43,
    'Barbados': 1258.42,
    'Frøya': 1249.89,
    'Gibraltar': 1246.92,
    'Cook Islands': 1237.16,
    'Antigua and Barbuda': 1230.72,
    'Nepal': 1229.2,
    'Bonaire': 1228.49,
    'Bangladesh': 1226.46,
    'Myanmar': 1218.4,
    'Taiwan': 1210.84,
    'Djibouti': 1187.35,
    'Cayman Islands': 1184.93,
    'Tonga': 1177.32,
    'Maldives': 1176.77,
    'Somalia': 1172.06,
    'Cambodia': 1163.95,
    'Alderney': 1161.98,
    'Seychelles': 1152.74,
    'British Virgin Islands': 1152.58,
    'Liechtenstein': 1149.7,
    'Bahamas': 1136.74,
    'Pakistan': 1135.59,
    'Turks and Caicos Islands': 1135.25,
    'Mongolia': 1131.97,
    'Sri Lanka': 1130.85,
    'Guam': 1125.66,
    'United States Virgin Islands': 1115.61,
    'American Samoa': 1088.67,
    'Northern Mariana Islands': 1087.4,
    'Laos': 1077.06,
    'San Marino': 1076.62,
    'Anguilla': 1062.54,
    'Timor-Leste': 1049.8,
    'Brunei': 1048.39,
    'Macau': 1027.09,
    'Bhutan': 1012.91,
}

# -------------------------
# Helper: resolve rating for any team / placeholder
# -------------------------
def get_rating(team):
    """
    Return a numeric rating for 'team'.
    - Direct teams: lookup teams_ratings (fallback 1500)
    - Placeholder teams (e.g. UEFA_Path_A_Winner): if GROUPS has 'possible_winners'
      then we return the average rating of the listed candidates (whether they are given
      as names or (name, rating) tuples). This gives a neutral estimate for placeholders.
    """
    # direct lookup
    if team in teams_ratings:
        return float(teams_ratings[team])

    # If the name appears as one of the candidate lists under possible_winners, it may be a placeholder
    for g in GROUPS.values():
        if 'possible_winners' in g:
            for placeholder, opts in g['possible_winners'].items():
                if team == placeholder:
                    # opts can be list of strings or list of tuples (name, rating)
                    ratings = []
                    for o in opts:
                        if isinstance(o, tuple):
                            ratings.append(float(o[1]))
                        else:
                            ratings.append(float(teams_ratings.get(o, 1500)))
                    return float(np.mean(ratings) if len(ratings) > 0 else 1500.0)

    # final fallback
    return 1500.0

# -------------------------
# Win probability and match simulation (all use ratings from get_rating)
# -------------------------
def get_win_probability(rating_a, rating_b, divisor=552):
    """
    Expected win probability for team A (higher is better).
    .
    """
    dr = rating_a - rating_b
    return 1 / (1 + 10 ** (-dr / divisor))

def simulate_match(team_a, team_b, group_key=None, draw_base=0.243, allow_draw=True):
    """
    Simulate one 90-minute match with goal scoring.
    Returns (points_a, points_b, goals_a, goals_b): points and goals scored.
    """
    rating_a = get_rating(team_a)
    rating_b = get_rating(team_b)

    # Apply home advantage for host nations in their groups
    if group_key in ['A', 'B', 'D']:
        host_teams = {'A': 'Mexico', 'B': 'Canada', 'D': 'United States'}
        host = host_teams[group_key]
        if team_a == host:
            rating_a += home_bonuses[host]
        if team_b == host:
            rating_b += home_bonuses[host]

    rating_diff = abs(rating_a - rating_b)

    if not allow_draw:
        draw_base = 0.0
    else:
        # For group stage matches, use dynamic draw probability based on rating difference
        if group_key is not None:
            draw_base = 0.26 * np.exp(-rating_diff / 380)

    p_a_win = get_win_probability(rating_a, rating_b, divisor=552)
    p_b_win = 1 - p_a_win

    # Split the draw probability evenly from both win buckets
    p_win_a = p_a_win - draw_base / 2
    p_win_b = p_b_win - draw_base / 2
    p_draw = draw_base

    # Critical fix: clamp to zero to avoid negative probabilities at extreme ratings
    p_win_a = max(0.0, p_win_a)
    p_win_b = max(0.0, p_win_b)
    p_draw = max(0.0, p_draw)

    # Renormalize (this is the mathematically correct way)
    total = p_win_a + p_win_b + p_draw
    if total == 0:
        # Fallback: should never happen with reasonable ratings
        probs = np.array([0.5, 0.5, 0.0]) if not allow_draw else np.array([1/3, 1/3, 1/3])
    else:
        probs = np.array([p_win_a, p_win_b, p_draw]) / total

    # For group stage matches, use goal-based simulation with expected total goals
    if group_key is not None:
        # Calculate expected total goals for group stage (clamped between 2.1 and 3.9)
        lambda_total = 2.55 + 0.0014 * rating_diff
        lambda_total = max(2.1, min(3.9, lambda_total))

        # Calculate goal share using Elo ratings directly
        # s_A = 10^(E_A/400) / (10^(E_A/400) + 10^(E_B/400))
        exp_rating_a = 10 ** (rating_a / 400)
        exp_rating_b = 10 ** (rating_b / 400)
        s_a = exp_rating_a / (exp_rating_a + exp_rating_b)

        # Expected goals for each team
        lambda_a = lambda_total * s_a
        lambda_b = lambda_total * (1 - s_a)

        # Sample actual goals from Poisson distribution, capped at 7
        goals_a = min(np.random.poisson(lambda_a), 7)
        goals_b = min(np.random.poisson(lambda_b), 7)

        # Determine match result based on goals
        if goals_a > goals_b:
            return 3, 0, goals_a, goals_b  # A wins
        elif goals_b > goals_a:
            return 0, 3, goals_a, goals_b  # B wins
        else:
            return 1, 1, goals_a, goals_b  # Draw
    else:
        # For knockout matches, use the original probability-based approach
        outcome = np.random.choice(['A_win', 'B_win', 'Draw'], p=probs)

        if outcome == 'A_win':
            return 3, 0, 1, 0  # Assume 1-0 for knockout draws that get resolved
        elif outcome == 'B_win':
            return 0, 3, 0, 1
        else:
            return 1, 1, 1, 1

def simulate_knockout_match(team_a, team_b):
    """
    Knockout simulation with regulation time, extra time, and penalties if needed.
    Returns the winner team name.
    """
    rating_a = get_rating(team_a)
    rating_b = get_rating(team_b)
    rating_diff = abs(rating_a - rating_b)

    # Regulation time (90 minutes) - no draws allowed, but we simulate goals
    # Use the same expected goals calculation as group stage but without draw probability
    lambda_total = 2.55 + 0.0014 * rating_diff
    lambda_total = max(2.1, min(3.9, lambda_total))

    # Calculate goal share using Elo ratings directly
    exp_rating_a = 10 ** (rating_a / 400)
    exp_rating_b = 10 ** (rating_b / 400)
    s_a = exp_rating_a / (exp_rating_a + exp_rating_b)

    # Expected goals for each team
    lambda_a = lambda_total * s_a
    lambda_b = lambda_total * (1 - s_a)

    # Sample actual goals from Poisson distribution, capped at 7
    goals_a_reg = min(np.random.poisson(lambda_a), 7)
    goals_b_reg = min(np.random.poisson(lambda_b), 7)

    # If not tied after regulation, return winner
    if goals_a_reg != goals_b_reg:
        return team_a if goals_a_reg > goals_b_reg else team_b

    # Extra time: 30% of regulation expected goals
    lambda_et = 0.30 * lambda_total
    lambda_a_et = lambda_et * s_a
    lambda_b_et = lambda_et * (1 - s_a)

    goals_a_et = min(np.random.poisson(lambda_a_et), 7)
    goals_b_et = min(np.random.poisson(lambda_b_et), 7)

    total_goals_a = goals_a_reg + goals_a_et
    total_goals_b = goals_b_reg + goals_b_et

    # If not tied after extra time, return winner
    if total_goals_a != total_goals_b:
        return team_a if total_goals_a > total_goals_b else team_b

    # Penalties: P(A wins shootout) = 1 / (1 + 10^(-Δ/300))
    rating_diff_penalty = rating_a - rating_b
    prob_a_penalty = 1 / (1 + 10 ** (-rating_diff_penalty / 300))

    return team_a if random.random() < prob_a_penalty else team_b

# small helper for bracket simulation where ratings are given as pairs or names
def rating_for_candidate(candidate):
    if isinstance(candidate, tuple):
        # (name, rating)
        return candidate[1]
    return teams_ratings.get(candidate, 1500.0)

def simulate_group(group, num_sims, group_key=None):
    results = {team: {'1st': 0, '2nd': 0, '3rd': 0, '4th': 0} for team in group['teams']}
    for _ in range(num_sims):
        group_table = {team: 0 for team in group['teams']}
        for team_a, team_b in group['matches']:
            sa, sb, ga, gb = simulate_match(team_a, team_b, group_key=group_key, allow_draw=True)
            group_table[team_a] += sa
            group_table[team_b] += sb
        standings_list = list(group_table.items())
        random.shuffle(standings_list)
        standings = sorted(standings_list, key=lambda item: item[1], reverse=True)
        results[standings[0][0]]['1st'] += 1
        results[standings[1][0]]['2nd'] += 1
        results[standings[2][0]]['3rd'] += 1
        results[standings[3][0]]['4th'] += 1
    return results

if mode == 'most_likely':
    # -------------------------
    # Pre-determine qualifiers for placeholders using teams_ratings always
    # -------------------------
    QUALIFIER_SIMS = 10000
    qualifiers = {}

    # Generic helper to simulate 4-team bracket using team names or (name,rating) tuples
    def simulate_bracket_by_candidates(candidates, sims=QUALIFIER_SIMS):
        """
        candidates: list like ['Italy','Wales','Bosnia and Herzegovina','Northern Ireland']
        or list of tuples [('Turkey',1880.0),...]
        Returns the most frequently occurring winner after sims simulations.
        """
        wins = {}
        # prepare names and ratings for simulate_knockout_match that expects team names,
        # but simulate_knockout_match will call get_rating which handles (name) lookup only.
        # For candidates passed as tuples, temporarily map to synthetic names and patch teams_ratings
        patched = {}
        temp_names = []
        try:
            for i, c in enumerate(candidates):
                if isinstance(c, tuple):
                    name = f"__temp_candidate_{i}__"
                    teams_ratings[name] = float(c[1])
                    patched[name] = c[0]
                    temp_names.append(name)
                    wins[name] = 0
                else:
                    name = c
                    wins[name] = 0
                    temp_names.append(name)
            for _ in range(sims):
                # semi 1: 0 vs 1, semi 2: 2 vs 3
                semi1 = simulate_knockout_match(temp_names[0], temp_names[1])
                semi2 = simulate_knockout_match(temp_names[2], temp_names[3])
                final_winner = simulate_knockout_match(semi1, semi2)
                wins[final_winner] = wins.get(final_winner, 0) + 1
            # map back patched names to real candidate names for selection
            mapped_wins = {}
            for k, v in wins.items():
                real_name = patched[k] if k in patched else k
                mapped_wins[real_name] = mapped_wins.get(real_name, 0) + v
            # choose max
            return max(mapped_wins, key=mapped_wins.get)
        finally:
            # cleanup temp ratings
            for name in patched.keys():
                teams_ratings.pop(name, None)

    # simulate 3-team round robin with candidates as names or tuples
    def simulate_round_robin_candidates(candidates, sims=QUALIFIER_SIMS):
        wins = {}
        patched = {}
        temp_names = []
        try:
            for i, c in enumerate(candidates):
                if isinstance(c, tuple):
                    name = f"__temp_rr_{i}__"
                    teams_ratings[name] = float(c[1])
                    patched[name] = c[0]
                    temp_names.append(name)
                    wins[name] = 0
                else:
                    name = c
                    wins[name] = 0
                    temp_names.append(name)
            for _ in range(sims):
                # three matches
                group_points = {n: 0 for n in temp_names}
                matches = [(temp_names[0], temp_names[1]), (temp_names[0], temp_names[2]), (temp_names[1], temp_names[2])]
                for a, b in matches:
                    sa, sb = simulate_match(a, b, allow_draw=True)
                    group_points[a] += sa
                    group_points[b] += sb
                max_points = max(group_points.values())
                candidates_with_max = [n for n, pts in group_points.items() if pts == max_points]
                winner = random.choice(candidates_with_max)
                wins[winner] += 1
            mapped_wins = {}
            for k, v in wins.items():
                real_name = patched[k] if k in patched else k
                mapped_wins[real_name] = mapped_wins.get(real_name, 0) + v
            return max(mapped_wins, key=mapped_wins.get)
        finally:
            for name in patched.keys():
                teams_ratings.pop(name, None)

    # Store original possible_winners
    original_possible = {g: group.get('possible_winners', {}).copy() for g, group in GROUPS.items()}

    # Run qualifiers where placeholders exist
    for group_key, group in GROUPS.items():
        if 'possible_winners' in group:
            for placeholder, opts in list(group['possible_winners'].items()):
                # opts may be list of names or list of (name,rating) tuples
                if len(opts) == 3 and all(isinstance(o, tuple) for o in opts):
                    # 3-team round robin candidates
                    winner = simulate_round_robin_candidates(opts)
                elif len(opts) == 4:
                    winner = simulate_bracket_by_candidates(opts)
                else:
                    # fallback: average rating approach and pick highest rating
                    # transform tuples to names if needed
                    candidate_names = [o[0] if isinstance(o, tuple) else o for o in opts]
                    winner = max(candidate_names, key=lambda x: teams_ratings.get(x, 1500.0))
                qualifiers[placeholder] = winner

    # Replace placeholders in GROUPS with decided qualifiers and remove possible_winners
    for group in GROUPS.values():
        if 'possible_winners' in group:
            for placeholder, _ in list(group['possible_winners'].items()):
                chosen = qualifiers.get(placeholder)
                if chosen:
                    idx = group['teams'].index(placeholder)
                    group['teams'][idx] = chosen
                    group['matches'] = [(a if a != placeholder else chosen, b if b != placeholder else chosen) for a, b in group['matches']]
            del group['possible_winners']

    # -------------------------
    # Build all_teams_points using get_rating exclusively
    # -------------------------
    all_teams_points = {}
    for group in GROUPS.values():
        for team in group['teams']:
            all_teams_points[team] = get_rating(team)

# -------------------------
# MAIN SIMULATION
# -------------------------
unique_finals = set()
knockout_results = {team: {'Round_of_32': 0, 'Round_of_16': 0, 'Quarterfinals': 0, 'Semifinals': 0, 'Final': 0, 'Winner': 0, 'Third': 0, 'Runner_up': 0, 'Fourth': 0} for team in all_possible_teams}

if mode == 'all':
    NUM_SIMULATIONS = 10
    # Get qualifier options
    qualifier_options = {}
    for g, group in GROUPS.items():
        if 'possible_winners' in group:
            for ph, opts in group['possible_winners'].items():
                qualifier_options[ph] = [o[0] if isinstance(o, tuple) else o for o in opts]

    # All combinations
    all_combos = list(product(*[qualifier_options[ph] for ph in sorted(qualifier_options.keys())]))
    total_combos = len(all_combos)
    total_sims = total_combos * NUM_SIMULATIONS
    print(f"Total group combinations: {total_combos}, Total simulations: {total_sims}")

    for combo in tqdm(all_combos):
        qualifier_dict = dict(zip(sorted(qualifier_options.keys()), combo))
        # Create current GROUPS
        current_GROUPS = {}
        for g, group in GROUPS.items():
            current_GROUPS[g] = {
                'teams': [qualifier_dict.get(t, t) for t in group['teams']],
                'matches': [(qualifier_dict.get(a, a), qualifier_dict.get(b, b)) for a, b in group['matches']]
            }

        for _ in range(NUM_SIMULATIONS):
            group_standings = {}
            for group_key, group in current_GROUPS.items():
                teams = group['teams']
                group_stats = {team: {'points': 0, 'gf': 0, 'ga': 0} for team in teams}
                for team_a, team_b in group['matches']:
                    sa, sb, ga, gb = simulate_match(team_a, team_b, group_key=group_key, allow_draw=True)
                    group_stats[team_a]['points'] += sa
                    group_stats[team_b]['points'] += sb
                    group_stats[team_a]['gf'] += ga
                    group_stats[team_a]['ga'] += gb
                    group_stats[team_b]['gf'] += gb
                    group_stats[team_b]['ga'] += ga

                # Calculate goal difference and create standings with tiebreakers
                standings_list = []
                for team, stats in group_stats.items():
                    gd = stats['gf'] - stats['ga']
                    elo = get_rating(team)
                    standings_list.append((team, stats['points'], gd, stats['gf'], elo))

                # Sort by: points (desc), goal diff (desc), goals scored (desc), Elo rating (desc)
                standings_list.sort(key=lambda x: (x[1], x[2], x[3], x[4]), reverse=True)
                group_standings[group_key] = standings_list

            # Determine advancing teams: top 2 from each group + best 8 thirds
            winners = {group: group_standings[group][0][0] for group in 'ABCDEFGHIJKL'}
            runners_up = {group: group_standings[group][1][0] for group in 'ABCDEFGHIJKL'}
            third_places_with_group = [(group, group_standings[group][2][0], group_standings[group][2][1], group_standings[group][2][2], group_standings[group][2][3], group_standings[group][2][4]) for group in 'ABCDEFGHIJKL']
            # Sort by: points (desc), goal diff (desc), goals scored (desc), Elo rating (desc)
            third_places_with_group.sort(key=lambda x: (x[2], x[3], x[4], x[5]), reverse=True)
            selected_thirds = third_places_with_group[:8]
            advancing_thirds = [t[1] for t in selected_thirds]

            # Assign thirds to R32 matches (shuffle for randomness)
            third_teams = advancing_thirds.copy()
            random.shuffle(third_teams)
            third_assign = {
                74: third_teams[0],
                77: third_teams[1],
                79: third_teams[2],
                80: third_teams[3],
                81: third_teams[4],
                82: third_teams[5],
                85: third_teams[6],
                87: third_teams[7]
            }

            # Mark Round of 32 appearance
            advancing = list(winners.values()) + list(runners_up.values()) + advancing_thirds
            for team in advancing:
                knockout_results[team]['Round_of_32'] += 1

            # Simulate Round of 32
            r32_matches = {
                73: (runners_up['A'], runners_up['B']),
                74: (winners['E'], third_assign[74]),
                75: (winners['F'], runners_up['C']),
                76: (winners['C'], runners_up['F']),
                77: (winners['I'], third_assign[77]),
                78: (runners_up['E'], runners_up['I']),
                79: (winners['A'], third_assign[79]),
                80: (winners['L'], third_assign[80]),
                81: (winners['D'], third_assign[81]),
                82: (winners['G'], third_assign[82]),
                83: (runners_up['K'], runners_up['L']),
                84: (winners['H'], runners_up['J']),
                85: (winners['B'], third_assign[85]),
                86: (winners['J'], runners_up['H']),
                87: (winners['K'], third_assign[87]),
                88: (runners_up['D'], runners_up['G'])
            }
            r32_winners = {}
            for match, (t1, t2) in r32_matches.items():
                winner = simulate_knockout_match(t1, t2)
                r32_winners[match] = winner
                knockout_results[winner]['Round_of_16'] += 1

            # Round of 16
            r16_matches = {
                89: (r32_winners[74], r32_winners[77]),
                90: (r32_winners[73], r32_winners[75]),
                91: (r32_winners[76], r32_winners[78]),
                92: (r32_winners[79], r32_winners[80]),
                93: (r32_winners[83], r32_winners[84]),
                94: (r32_winners[81], r32_winners[82]),
                95: (r32_winners[86], r32_winners[88]),
                96: (r32_winners[85], r32_winners[87])
            }
            r16_winners = {}
            for match, (t1, t2) in r16_matches.items():
                winner = simulate_knockout_match(t1, t2)
                r16_winners[match] = winner
                knockout_results[winner]['Quarterfinals'] += 1

            # Quarterfinals
            qf_matches = {
                97: (r16_winners[89], r16_winners[90]),
                98: (r16_winners[93], r16_winners[94]),
                99: (r16_winners[91], r16_winners[92]),
                100: (r16_winners[95], r16_winners[96])
            }
            qf_winners = {}
            for match, (t1, t2) in qf_matches.items():
                winner = simulate_knockout_match(t1, t2)
                qf_winners[match] = winner
                knockout_results[winner]['Semifinals'] += 1

            # Semifinals
            sf_matches = {
                101: (qf_winners[97], qf_winners[98]),
                102: (qf_winners[99], qf_winners[100])
            }
            sf_winners = {}
            for match, (t1, t2) in sf_matches.items():
                winner = simulate_knockout_match(t1, t2)
                sf_winners[match] = winner
                knockout_results[winner]['Final'] += 1

            # Third place
            loser101 = qf_winners[97] if sf_winners[101] == qf_winners[98] else qf_winners[98]
            loser102 = qf_winners[99] if sf_winners[102] == qf_winners[100] else qf_winners[100]
            third = simulate_knockout_match(loser101, loser102)
            knockout_results[third]['Third'] += 1
            fourth_team = loser101 if third == loser102 else loser102
            knockout_results[fourth_team]['Fourth'] += 1

            # Final
            final_winner = simulate_knockout_match(sf_winners[101], sf_winners[102])
            knockout_results[final_winner]['Winner'] += 1
            runner_up = sf_winners[101] if final_winner == sf_winners[102] else sf_winners[102]
            knockout_results[runner_up]['Runner_up'] += 1
            unique_finals.add(frozenset([sf_winners[101], sf_winners[102]]))

elif mode == 'most_likely':
    NUM_SIMULATIONS = 1000
    results = {}
    for group_key, group in GROUPS.items():
        results[group_key] = {team: {'1st_Place': 0, '2nd_Place': 0, '3rd_Place': 0, '4th_Place': 0, 'Advance_3rd': 0} for team in group['teams']}

    for _ in tqdm(range(NUM_SIMULATIONS)):
        group_standings = {}
        for group_key, group in GROUPS.items():
            teams = group['teams']
            group_stats = {team: {'points': 0, 'gf': 0, 'ga': 0} for team in teams}
            for team_a, team_b in group['matches']:
                sa, sb, ga, gb = simulate_match(team_a, team_b, group_key=group_key, allow_draw=True)
                group_stats[team_a]['points'] += sa
                group_stats[team_b]['points'] += sb
                group_stats[team_a]['gf'] += ga
                group_stats[team_a]['ga'] += gb
                group_stats[team_b]['gf'] += gb
                group_stats[team_b]['ga'] += ga

            # Calculate goal difference and create standings with tiebreakers
            standings_list = []
            for team, stats in group_stats.items():
                gd = stats['gf'] - stats['ga']
                elo = get_rating(team)
                standings_list.append((team, stats['points'], gd, stats['gf'], elo))

            # Sort by: points (desc), goal diff (desc), goals scored (desc), Elo rating (desc)
            standings_list.sort(key=lambda x: (x[1], x[2], x[3], x[4]), reverse=True)
            group_standings[group_key] = standings_list

            results[group_key][standings_list[0][0]]['1st_Place'] += 1
            results[group_key][standings_list[1][0]]['2nd_Place'] += 1
            results[group_key][standings_list[2][0]]['3rd_Place'] += 1
            results[group_key][standings_list[3][0]]['4th_Place'] += 1

        # Determine advancing teams: top 2 from each group + best 8 thirds
        winners = {group: group_standings[group][0][0] for group in 'ABCDEFGHIJKL'}
        runners_up = {group: group_standings[group][1][0] for group in 'ABCDEFGHIJKL'}
        third_places_with_group = [(group, group_standings[group][2][0], group_standings[group][2][1], group_standings[group][2][2], group_standings[group][2][3], group_standings[group][2][4]) for group in 'ABCDEFGHIJKL']
        # Sort by: points (desc), goal diff (desc), goals scored (desc), Elo rating (desc)
        third_places_with_group.sort(key=lambda x: (x[2], x[3], x[4], x[5]), reverse=True)
        selected_thirds = third_places_with_group[:8]
        advancing_thirds = [t[1] for t in selected_thirds]

        # Assign thirds to R32 matches (shuffle for randomness)
        third_teams = advancing_thirds.copy()
        random.shuffle(third_teams)
        third_assign = {
            74: third_teams[0],
            77: third_teams[1],
            79: third_teams[2],
            80: third_teams[3],
            81: third_teams[4],
            82: third_teams[5],
            85: third_teams[6],
            87: third_teams[7]
        }

        # Count Advance_3rd for the selected thirds
        for third_place_tuple in selected_thirds:
            group, third_team = third_place_tuple[0], third_place_tuple[1]
            results[group][third_team]['Advance_3rd'] += 1

        # Mark Round of 32 appearance
        advancing = list(winners.values()) + list(runners_up.values()) + advancing_thirds
        for team in advancing:
            knockout_results[team]['Round_of_32'] += 1

        # Simulate Round of 32
        r32_matches = {
            73: (runners_up['A'], runners_up['B']),
            74: (winners['E'], third_assign[74]),
            75: (winners['F'], runners_up['C']),
            76: (winners['C'], runners_up['F']),
            77: (winners['I'], third_assign[77]),
            78: (runners_up['E'], runners_up['I']),
            79: (winners['A'], third_assign[79]),
            80: (winners['L'], third_assign[80]),
            81: (winners['D'], third_assign[81]),
            82: (winners['G'], third_assign[82]),
            83: (runners_up['K'], runners_up['L']),
            84: (winners['H'], runners_up['J']),
            85: (winners['B'], third_assign[85]),
            86: (winners['J'], runners_up['H']),
            87: (winners['K'], third_assign[87]),
            88: (runners_up['D'], runners_up['G'])
        }
        r32_winners = {}
        for match, (t1, t2) in r32_matches.items():
            winner = simulate_knockout_match(t1, t2)
            r32_winners[match] = winner
            knockout_results[winner]['Round_of_16'] += 1

        # Round of 16
        r16_matches = {
            89: (r32_winners[74], r32_winners[77]),
            90: (r32_winners[73], r32_winners[75]),
            91: (r32_winners[76], r32_winners[78]),
            92: (r32_winners[79], r32_winners[80]),
            93: (r32_winners[83], r32_winners[84]),
            94: (r32_winners[81], r32_winners[82]),
            95: (r32_winners[86], r32_winners[88]),
            96: (r32_winners[85], r32_winners[87])
        }
        r16_winners = {}
        for match, (t1, t2) in r16_matches.items():
            winner = simulate_knockout_match(t1, t2)
            r16_winners[match] = winner
            knockout_results[winner]['Quarterfinals'] += 1

        # Quarterfinals
        qf_matches = {
            97: (r16_winners[89], r16_winners[90]),
            98: (r16_winners[93], r16_winners[94]),
            99: (r16_winners[91], r16_winners[92]),
            100: (r16_winners[95], r16_winners[96])
        }
        qf_winners = {}
        for match, (t1, t2) in qf_matches.items():
            winner = simulate_knockout_match(t1, t2)
            qf_winners[match] = winner
            knockout_results[winner]['Semifinals'] += 1

        # Semifinals
        sf_matches = {
            101: (qf_winners[97], qf_winners[98]),
            102: (qf_winners[99], qf_winners[100])
        }
        sf_winners = {}
        for match, (t1, t2) in sf_matches.items():
            winner = simulate_knockout_match(t1, t2)
            sf_winners[match] = winner
            knockout_results[winner]['Final'] += 1

        # Third place
        loser101 = qf_winners[97] if sf_winners[101] == qf_winners[98] else qf_winners[98]
        loser102 = qf_winners[99] if sf_winners[102] == qf_winners[100] else qf_winners[100]
        third = simulate_knockout_match(loser101, loser102)
        knockout_results[third]['Third'] += 1
        fourth_team = loser101 if third == loser102 else loser102
        knockout_results[fourth_team]['Fourth'] += 1

        # Final
        final_winner = simulate_knockout_match(sf_winners[101], sf_winners[102])
        knockout_results[final_winner]['Winner'] += 1
        runner_up = sf_winners[101] if final_winner == sf_winners[102] else sf_winners[102]
        knockout_results[runner_up]['Runner_up'] += 1
        unique_finals.add(frozenset([sf_winners[101], sf_winners[102]]))

# -------------------------
# OUTPUT
# -------------------------
if mode == 'most_likely':
    for group_key in GROUPS:
        print(f"\n## World Cup Group {group_key} Probabilistic Prediction ({NUM_SIMULATIONS} Simulations)")
        print("\n---")
        final_percentages = {}
        for team, data in results[group_key].items():
            final_percentages[team] = {
                '% Chance of Finishing 1st': (data['1st_Place'] / NUM_SIMULATIONS) * 100,
                '% Chance of Finishing 2nd': (data['2nd_Place'] / NUM_SIMULATIONS) * 100,
                '% Chance of Advancing as 3rd': (data['Advance_3rd'] / NUM_SIMULATIONS) * 100,
                '% Chance of Finishing 4th': (data['4th_Place'] / NUM_SIMULATIONS) * 100,
                '% Chance of Not Going Through': ((data['3rd_Place'] - data['Advance_3rd'] + data['4th_Place']) / NUM_SIMULATIONS) * 100
            }
        df_final = pd.DataFrame.from_dict(final_percentages, orient='index')
        df_final = df_final.sort_values(by='% Chance of Finishing 1st', ascending=False)
        df_final['% Chance of Finishing 1st'] = df_final['% Chance of Finishing 1st'].round(2).astype(str) + '%'
        df_final['% Chance of Finishing 2nd'] = df_final['% Chance of Finishing 2nd'].round(2).astype(str) + '%'
        df_final['% Chance of Advancing as 3rd'] = df_final['% Chance of Advancing as 3rd'].round(2).astype(str) + '%'
        df_final['% Chance of Finishing 4th'] = df_final['% Chance of Finishing 4th'].round(2).astype(str) + '%'
        df_final['% Chance of Not Going Through'] = df_final['% Chance of Not Going Through'].round(2).astype(str) + '%'
        print(f"**Teams:** {', '.join(GROUPS[group_key]['teams'])}")
        print(f"**Model Basis:** Simulations use `teams_ratings` exclusively (placeholders resolved by averaging candidate ratings).")
        print(f"### Predicted Group {group_key} Finishing Positions:")
        print(df_final.to_markdown())

    print("\nDo you want to print group scenarios with different qualifiers? (y/n)")
    try:
        response = input().lower()
    except EOFError:
        response = 'n'
    if response == 'y':
        print("\n## Group Scenarios with Different Qualifiers")
        for group_key, group in GROUPS.items():
            if group_key in original_possible and original_possible[group_key]:
                for placeholder, opts in original_possible[group_key].items():
                    possible_teams = [o[0] if isinstance(o, tuple) else o for o in opts]
                    chosen = qualifiers[placeholder]
                    for qual_team in possible_teams:
                        # create temp group
                        temp_teams = [qual_team if t == chosen else t for t in GROUPS[group_key]['teams']]
                        temp_matches = [(qual_team if a == chosen else a, qual_team if b == chosen else b) for a, b in GROUPS[group_key]['matches']]
                        temp_group = {
                            'teams': temp_teams,
                            'matches': temp_matches
                        }
                        group_results = simulate_group(temp_group, NUM_SIMULATIONS, group_key=group_key)
                        print(f"\n### Group {group_key} with {qual_team} qualifying")
                        final_percentages = {}
                        for team, data in group_results.items():
                            final_percentages[team] = {
                                '% Chance of Finishing 1st': (data['1st'] / NUM_SIMULATIONS) * 100,
                                '% Chance of Finishing 2nd': (data['2nd'] / NUM_SIMULATIONS) * 100,
                                '% Chance of Finishing 3rd': (data['3rd'] / NUM_SIMULATIONS) * 100,
                                '% Chance of Finishing 4th': (data['4th'] / NUM_SIMULATIONS) * 100,
                            }
                        df_final = pd.DataFrame.from_dict(final_percentages, orient='index')
                        df_final = df_final.sort_values(by='% Chance of Finishing 1st', ascending=False)
                        df_final = df_final.round(2).astype(str) + '%'
                        print(f"**Teams:** {', '.join(temp_group['teams'])}")
                        print(df_final.to_markdown())

print("\n## Final Positions Matrix")
print("\n---")
positions = ['Round_of_32', 'Round_of_16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Runner_up', 'Third', 'Fourth']
teams_reached = [team for team, data in knockout_results.items() if any(data[pos] > 0 for pos in positions)]
teams_reached.sort(key=lambda t: knockout_results[t]['Winner'], reverse=True)
data = {pos: [knockout_results[team][pos] for team in teams_reached] for pos in positions}
df = pd.DataFrame(data, index=teams_reached)
if mode == 'all':
    df = df / total_sims * 100
else:
    df = df / NUM_SIMULATIONS * 100
df = df.round(1).astype(str) + '%'
df.columns = ['Round of 32', 'Round of 16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Runner-up', 'Third', 'Fourth']
print(df.to_markdown())

# Cool facts: teams that reached each round at least once
print("\n## Cool Facts")
print("---")
total_teams = len(all_possible_teams)
round_names = {
    'Round_of_32': 'Round of 32',
    'Round_of_16': 'Round of 16',
    'Quarterfinals': 'Quarterfinals',
    'Semifinals': 'Semifinals',
    'Final': 'Final',
    'Winner': 'Winner',
    'Runner_up': 'Runner-up',
    'Third': 'Third Place',
    'Fourth': 'Fourth Place'
}

for pos in positions:
    teams_count = sum(1 for team_data in knockout_results.values() if team_data[pos] > 0)
    percentage = (teams_count / number_of_qualfied_teams) * 100
    print(f"Teams that reached {round_names[pos]} at least once: {teams_count} ({percentage:.1f}%)")

if mode == 'all'or mode == 'most_likely':
    print(f"\nNumber of different final matchups: {len(unique_finals)}")


# Generate HTML output
def create_html():
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>World Cup 2026 Simulation Results</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #000000;
            color: #39ff14;
        }
        h1, h2 {
            color: #39ff14;
            text-shadow: 0 0 15px #39ff14, 0 0 30px #39ff14;
        }
        p, li {
            color: #39ff14;
            text-shadow: 0 0 5px #39ff14;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
            border: 2px solid #39ff14;
            box-shadow: 0 0 20px #39ff14;
        }
        th, td {
            border: 1px solid #39ff14;
            padding: 8px;
            text-align: left;
            color: #39ff14;
            text-shadow: 0 0 3px #39ff14;
        }
        th {
            background-color: #111111;
            color: #39ff14;
            text-shadow: 0 0 8px #39ff14, 0 0 15px #39ff14;
        }
        tbody tr:nth-child(even) {
            background-color: #111111;
        }
        tbody tr:nth-child(odd) {
            background-color: #000000;
        }
        .group { margin-bottom: 40px; }
    </style>
</head>
<body>
    <h1>World Cup 2026 Simulation Results</h1>
"""

    if mode == 'most_likely':
        for group_key in GROUPS:
            html_content += f"<div class='group'><h2>World Cup Group {group_key} Probabilistic Prediction ({NUM_SIMULATIONS} Simulations)</h2>"
            html_content += f"<p><strong>Teams:</strong> {', '.join(GROUPS[group_key]['teams'])}</p>"
            html_content += "<p><strong>Model Basis:</strong> Simulations use `teams_ratings` exclusively (placeholders resolved by averaging candidate ratings).</p>"
            html_content += f"<h3>Predicted Group {group_key} Finishing Positions:</h3>"
            final_percentages = {}
            for team, data in results[group_key].items():
                final_percentages[team] = {
                    '% Chance of Finishing 1st': (data['1st_Place'] / NUM_SIMULATIONS) * 100,
                    '% Chance of Finishing 2nd': (data['2nd_Place'] / NUM_SIMULATIONS) * 100,
                    '% Chance of Advancing as 3rd': (data['Advance_3rd'] / NUM_SIMULATIONS) * 100,
                    '% Chance of Finishing 4th': (data['4th_Place'] / NUM_SIMULATIONS) * 100,
                    '% Chance of Not Going Through': ((data['3rd_Place'] - data['Advance_3rd'] + data['4th_Place']) / NUM_SIMULATIONS) * 100
                }
            df_final = pd.DataFrame.from_dict(final_percentages, orient='index')
            df_final = df_final.sort_values(by='% Chance of Finishing 1st', ascending=False)
            df_final = df_final.round(2)
            html_content += df_final.to_html()
            html_content += "</div>"

    html_content += "<h2>Final Positions Matrix</h2>"
    positions = ['Round_of_32', 'Round_of_16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Runner_up', 'Third', 'Fourth']
    teams_reached = [team for team, data in knockout_results.items() if any(data[pos] > 0 for pos in positions)]
    teams_reached.sort(key=lambda t: knockout_results[t]['Winner'], reverse=True)
    data = {pos: [knockout_results[team][pos] for team in teams_reached] for pos in positions}
    df = pd.DataFrame(data, index=teams_reached)
    if mode == 'all':
        df = df / total_sims * 100
    else:
        df = df / NUM_SIMULATIONS * 100
    df = df.round(1)
    df.columns = ['Round of 32', 'Round of 16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Runner-up', 'Third', 'Fourth']
    html_content += df.to_html()

    html_content += "<h2>Cool Facts</h2>"
    html_content += "<ul>"
    total_teams = len(all_possible_teams)
    round_names = {
        'Round_of_32': 'Round of 32',
        'Round_of_16': 'Round of 16',
        'Quarterfinals': 'Quarterfinals',
        'Semifinals': 'Semifinals',
        'Final': 'Final',
        'Winner': 'Winner',
        'Runner_up': 'Runner-up',
        'Third': 'Third Place',
        'Fourth': 'Fourth Place'
    }

    for pos in positions:
        teams_count = sum(1 for team_data in knockout_results.values() if team_data[pos] > 0)
        percentage = (teams_count / number_of_qualfied_teams) * 100
        html_content += f"<li>Teams that reached {round_names[pos]} at least once: {teams_count} ({percentage:.1f}%)</li>"

    html_content += "</ul>"

    html_content += """
</body>
</html>
"""

    try:
        with open('worldcup_simulation_results.html', 'w') as f:
            f.write(html_content)
    except Exception as e:
        print(f"Error generating HTML file: {e}")
        return False
    return True

# Generate PDF output
def create_pdf():
    doc = SimpleDocTemplate('worldcup_simulation_results.pdf', pagesize=letter)
    styles = getSampleStyleSheet()

    # Create custom styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=30)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14, spaceAfter=20)
    normal_style = styles['Normal']

    story = []

    # Title
    story.append(Paragraph("World Cup 2026 Simulation Results", title_style))
    story.append(Spacer(1, 12))

    if mode == 'most_likely':
        for group_key in GROUPS:
            # Group header
            story.append(Paragraph(f"World Cup Group {group_key} Probabilistic Prediction ({NUM_SIMULATIONS} Simulations)", heading_style))

            # Teams
            teams_text = f"<b>Teams:</b> {', '.join(GROUPS[group_key]['teams'])}"
            story.append(Paragraph(teams_text, normal_style))

            # Model basis
            story.append(Paragraph("<b>Model Basis:</b> Simulations use `teams_ratings` exclusively (placeholders resolved by averaging candidate ratings).", normal_style))

            # Group table
            story.append(Paragraph("Predicted Group {group_key} Finishing Positions:", styles['Heading3']))

            final_percentages = {}
            for team, data in results[group_key].items():
                final_percentages[team] = {
                    '% Chance of Finishing 1st': f"{(data['1st_Place'] / NUM_SIMULATIONS) * 100:.1f}%",
                    '% Chance of Finishing 2nd': f"{(data['2nd_Place'] / NUM_SIMULATIONS) * 100:.1f}%",
                    '% Chance of Advancing as 3rd': f"{(data['Advance_3rd'] / NUM_SIMULATIONS) * 100:.1f}%",
                    '% Chance of Finishing 4th': f"{(data['4th_Place'] / NUM_SIMULATIONS) * 100:.1f}%",
                    '% Chance of Not Going Through': f"{((data['3rd_Place'] - data['Advance_3rd'] + data['4th_Place']) / NUM_SIMULATIONS) * 100:.1f}%"
                }

            df_final = pd.DataFrame.from_dict(final_percentages, orient='index')
            df_final = df_final.sort_values(by='% Chance of Finishing 1st', ascending=False, key=lambda x: x.str.rstrip('%').astype(float))

            # Convert to table data
            table_data = [list(df_final.columns)]
            for team in df_final.index:
                table_data.append([team] + list(df_final.loc[team]))

            # Set column widths (in points: 72 points = 1 inch)
            # Total width should be around 450-500 points for letter page
            col_widths = [80] + [50] * 5  # Team name wider, percentages narrower
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),  # Smaller font for headers
                ('FONTSIZE', (0, 1), (-1, -1), 7),  # Even smaller for content
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ]))
            story.append(table)
            story.append(Spacer(1, 20))

    # Final Positions Matrix
    story.append(Paragraph("Final Positions Matrix", heading_style))

    positions = ['Round_of_32', 'Round_of_16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Runner_up', 'Third', 'Fourth']
    teams_reached = [team for team, data in knockout_results.items() if any(data[pos] > 0 for pos in positions)]
    teams_reached.sort(key=lambda t: knockout_results[t]['Winner'], reverse=True)
    data = {pos: [knockout_results[team][pos] for team in teams_reached] for pos in positions}
    df = pd.DataFrame(data, index=teams_reached)
    if mode == 'all':
        df = df / total_sims * 100
    else:
        df = df / NUM_SIMULATIONS * 100
    df = df.round(1)

    # Convert to formatted strings with %
    for col in df.columns:
        df[col] = df[col].astype(str) + '%'

    df.columns = ['Round of 32', 'Round of 16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Runner-up', 'Third', 'Fourth']

    # Convert to table data
    table_data = [list(df.columns)]
    for team in df.index:
        table_data.append([team] + list(df.loc[team]))

    # Set column widths for final positions matrix
    # Team names need more space, percentages can be narrower
    col_widths = [90] + [35] * 9  # Team name wider, percentages much narrower
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 6),  # Very small font for headers
        ('FONTSIZE', (0, 1), (-1, -1), 5),  # Very small for content
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

    # Cool Facts
    story.append(Paragraph("Cool Facts", heading_style))

    round_names = {
        'Round_of_32': 'Round of 32',
        'Round_of_16': 'Round of 16',
        'Quarterfinals': 'Quarterfinals',
        'Semifinals': 'Semifinals',
        'Final': 'Final',
        'Winner': 'Winner',
        'Runner_up': 'Runner-up',
        'Third': 'Third Place',
        'Fourth': 'Fourth Place'
    }

    for pos in positions:
        teams_count = sum(1 for team_data in knockout_results.values() if team_data[pos] > 0)
        percentage = (teams_count / number_of_qualfied_teams) * 100
        fact_text = f"Teams that reached {round_names[pos]} at least once: {teams_count} ({percentage:.1f}%)"
        story.append(Paragraph(f"• {fact_text}", normal_style))
        story.append(Spacer(1, 6))

    doc.build(story)

html_success = create_html()
if html_success:
    print("\nHTML file 'worldcup_simulation_results.html' generated.")
else:
    print("\nFailed to generate HTML file.")

try:
    create_pdf()
    print("PDF file 'worldcup_simulation_results.pdf' generated.")
except PermissionError as e:
    print(f"Error generating PDF: {e}")
    print("The PDF file may be open in another program. Please close it and try again.")
except Exception as e:
    print(f"Error generating PDF: {e}")

print("\nSimulation complete.")
