import random
import math
from collections import defaultdict

########################################
# ELO RATINGS (example placeholders)
########################################

ELO_RATINGS = {
    'Spain': 2284.01,
    'USA': 2252.84,
    'France': 2171.51,
    'England': 2169.74,
    'Germany': 2155.64,
    'Japan': 2141.13,
    'Brazil': 2138.81,
    'Sweden': 2131.95,
    'North Korea': 2059.17,
    'Canada': 2053.77,
    'Netherlands': 2038.35,
    'Norway': 1998.07,
    'Australia': 1982.34,
    'Denmark': 1975.94,
    'Italy': 1968.79,
    'Mexico': 1922.50,
    'Colombia': 1910.77,
    'Nigeria': 1896.33,
    'China': 1888.76,
    'Iceland': 1883.96,
    'South Korea': 1852.65,
    'Belgium': 1833.09,
    'Poland': 1810.72,
    'Portugal': 1808.39,
    'Austria': 1806.45,
    'Russia': 1800.69,
    'Scotland': 1785.39,
    'South Africa': 1783.22,
    'Switzerland': 1782.34,
    'Ireland': 1779.41,
    'Finland': 1779.29,
    'Vietnam': 1769.19,
    'Argentina': 1766.61,
    'Zambia': 1745.79,
    'Ghana': 1738.57,
    'Serbia': 1717.59,
    'Haiti': 1717.51,
    'Wales': 1715.81,
    'Ivory Coast': 1698.65,
    'Taiwan': 1692.19,
    'New Zealand': 1688.34,
    'Morocco': 1686.50,
    'Czech Republic': 1684.27,
    'Ukraine': 1679.38,
    'Cameroon': 1677.50,
    'Åland': 1667.79,
    'Papua New Guinea': 1667.68,
    'Algeria': 1663.76,
    'Bermuda': 1662.33,
    'Thailand': 1658.36,
    'Myanmar': 1658.15,
    'Senegal': 1658.02,
    'Tanzania': 1657.69,
    'Puerto Rico': 1654.17,
    'Isle of Man': 1652.33,
    'Kenya': 1649.88,
    'Venezuela': 1641.50,
    'Chile': 1637.85,
    'Panama': 1636.01,
    'Slovenia': 1632.61,
    'Jamaica': 1624.41,
    'Philippines': 1623.83,
    'Sápmi': 1619.86,
    'Great Britain': 1614.75,
    'Malawi': 1612.53,
    'Costa Rica': 1611.55,
    'Gotland': 1610.51,
    'Uzbekistan': 1607.41,
    'Ethiopia': 1602.67,
    'Dominican Republic': 1599.61,
    'Mali': 1597.41,
    'Western Isles': 1590.40,
    'Burkina Faso': 1586.25,
    'Cuba': 1583.30,
    'El Salvador': 1580.76,
    'FR Yugoslavia': 1576.98,
    'Paraguay': 1573.89,
    'Belarus': 1567.21,
    'Uruguay': 1563.00,
    'Zimbabwe': 1562.38,
    'Prince Edward Island': 1556.42,
    'Namibia': 1550.86,
    'Guyana': 1549.60,
    'Uganda': 1549.52,
    'Fiji': 1548.73,
    'Northern Ireland': 1540.00,
    'Czechoslovakia': 1538.11,
    'Iran': 1534.18,
    'Trinidad and Tobago': 1531.64,
    'Hungary': 1521.85,
    'Equatorial Guinea': 1517.46,
    'Botswana': 1516.59,
    'Jersey': 1515.45,
    'Reunion': 1512.80,
    'Liberia': 1512.20,
    'Tunisia': 1511.55,
    'Gozo': 1508.56,
    'Surrey': 1506.05,
    'Cape Verde': 1505.46,
    'Turkey': 1500.52,
    'Slovakia': 1500.46,
    'Catalonia': 1498.88,
    'Chad': 1497.60,
    'Mayotte': 1497.59,
    'Netherlands Antilles': 1494.65,
    'Yugoslavia': 1491.29,
    'Congo DR': 1490.03,
    'Jordan': 1488.89,
    'Isle of Wight': 1488.15,
    'Saare County': 1480.12,
    'Shetland Islands': 1479.80,
    'Ecuador': 1479.50,
    'Tamil Eelam': 1478.97,
    'Menorca': 1477.64,
    'Guatemala': 1474.47,
    'Curacao': 1473.65,
    'India': 1473.37,
    'Székely Land': 1469.68,
    'Egypt': 1469.61,
    'Congo': 1468.14,
    'Benin': 1468.05,
    'Nicaragua': 1465.25,
    'Bangladesh': 1464.32,
    'Nepal': 1463.77,
    'Gambia': 1463.19,
    'Curaçao': 1460.70,
    'Romania': 1459.18,
    'Greenland': 1458.20,
    'Togo': 1457.66,
    'St. Lucia': 1451.78,
    'Froya': 1451.75,
    'Samoa': 1450.59,
    'Greece': 1448.95,
    'Burundi': 1446.20,
    'New Caledonia': 1446.13,
    'St. Kitts and Nevis': 1442.30,
    'Solomon Islands': 1438.45,
    'Suriname': 1434.47,
    'Mozambique': 1432.74,
    'Tibet': 1431.49,
    'Central African Republic': 1430.16,
    'Madagascar': 1428.79,
    'Mauritania': 1428.68,
    'Vanuatu': 1419.59,
    'Hong Kong': 1419.33,
    'Orkney': 1418.96,
    'Bosnia and Herzegovina': 1418.18,
    'Serbia and Montenegro': 1416.23,
    'Qatar': 1410.41,
    'Ynys Môn': 1406.92,
    'Rwanda': 1404.87,
    'Martinique': 1402.89,
    'Sierra Leone': 1401.35,
    'U.S. Virgin Islands': 1400.88,
    'Bonaire': 1400.66,
    'Croatia': 1400.28,
    'Barbados': 1400.07,
    'Aruba': 1399.94,
    'Angola': 1398.61,
    'Gabon': 1393.23,
    'Israel': 1389.62,
    'Montenegro': 1384.20,
    'Sudan': 1384.20,
    'Rhodes': 1383.95,
    'Saudi Arabia': 1382.28,
    'South Sudan': 1381.07,
    'Eritrea': 1379.38,
    'Turkmenistan': 1378.38,
    'Sao Tome e Principe': 1377.63,
    'Albania': 1376.03,
    'United States Virgin Islands': 1375.91,
    'Guam': 1375.75,
    'Shetland': 1373.66,
    'Tahiti': 1370.99,
    'Guadeloupe': 1370.88,
    'Grenada': 1368.13,
    'Belize': 1363.55,
    'Guinea-Bissau': 1359.82,
    'Azerbaijan': 1359.39,
    'Kosovo': 1349.79,
    'Kuwait': 1347.17,
    'Guernsey': 1344.38,
    'Cambodia': 1343.62,
    'Lebanon': 1343.44,
    'Honduras': 1342.60,
    'Kiribati': 1341.82,
    'Bahamas': 1340.91,
    'Niger': 1338.74,
    'St. Vincent / Grenadines': 1338.53,
    'Tonga': 1335.45,
    'Hitra': 1332.39,
    'Malaysia': 1325.41,
    'Zanzibar': 1314.78,
    'Anguilla': 1313.88,
    'Pakistan': 1312.82,
    'Indonesia': 1311.53,
    'Luxembourg': 1311.50,
    'Malta': 1300.12,
    'Eswatini': 1298.52,
    'Cook Islands': 1298.26,
    'Bahrain': 1295.98,
    'Lesotho': 1294.55,
    'Djibouti': 1292.08,
    'Northern Mariana Islands': 1291.58,
    'Guinea': 1290.55,
    'Libya': 1288.03,
    'Comoros': 1287.47,
    'Mongolia': 1287.11,
    'Macau': 1281.36,
    'Cayman Islands': 1277.69,
    'Bhutan': 1274.07,
    'United Arab Emirates': 1270.41,
    'Kyrgyzstan': 1269.71,
    'British Virgin Islands': 1267.48,
    'Palestine': 1266.54,
    'Peru': 1265.35,
    'Afghanistan': 1264.99,
    'Antigua and Barbuda': 1257.63,
    'Latvia': 1254.13,
    'Liechtenstein': 1251.77,
    'Iraq': 1250.33,
    'Seychelles': 1244.93,
    'Bolivia': 1243.75,
    'Syria': 1242.11,
    'Lithuania': 1222.53,
    'Sri Lanka': 1220.65,
    'Tajikistan': 1216.19,
    'Mauritius': 1208.21,
    'Cyprus': 1201.49,
    'Kazakhstan': 1199.41,
    'Dominica': 1199.38,
    'Faroe Islands': 1199.09,
    'Singapore': 1194.97,
    'American Samoa': 1190.86,
    'Georgia': 1190.05,
    'Andorra': 1183.83,
    'Timor-Leste': 1181.60,
    'Turks and Caicos Islands': 1180.18,
    'Laos': 1179.27,
    'Estonia': 1177.37,
    'North Macedonia': 1165.89,
    'Bulgaria': 1157.62,
    'Moldova': 1146.23,
    'Macedonia': 1126.32,
    'Armenia': 1090.97,
    'Gibraltar': 1087.89,
    'Maldives': 1083.87,
}
########################################
# GROUP DEFINITIONS
########################################

GROUPS = {

"A1":["Denmark","Sweden","Italy","Serbia"],
"A2":["France","Netherlands","Poland","Ireland"],
"A3":["England","Spain","Iceland","Ukraine"],
"A4":["Germany","Norway","Austria","Slovenia"],

"B1":["Albania","Wales","Czech Republic","Montenegro"],
"B2":["Turkey","Switzerland","Northern Ireland","Malta"],
"B3":["Portugal","Slovakia","Latvia","Finland"],
"B4":["Scotland","Belgium","Israel","Luxembourg"],

"C1":["Lithuania","Bosnia and Herzegovina","Estonia","Liechtenstein"],
"C2":["Kosovo","Croatia","Bulgaria","Gibraltar"],
"C3":["Azerbaijan","Hungary","Andorra","North Macedonia"],
"C4":["Greece","Faroe Islands","Georgia"],
"C5":["Romania","Cyprus","Moldova"],
"C6":["Kazakhstan","Belarus","Armenia"]
}


STANDINGS = {

"A1":{
"Denmark":{"P":1,"W":1,"D":0,"L":0,"GF":3,"GA":1,"GD":2,"PTS":3},
"Sweden":{"P":1,"W":1,"D":0,"L":0,"GF":1,"GA":0,"GD":1,"PTS":3},
"Italy":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":1,"GD":-1,"PTS":0},
"Serbia":{"P":1,"W":0,"D":0,"L":1,"GF":1,"GA":3,"GD":-2,"PTS":0}
},

"A2":{
"France":{"P":1,"W":1,"D":0,"L":0,"GF":2,"GA":1,"GD":1,"PTS":3},
"Netherlands":{"P":1,"W":0,"D":1,"L":0,"GF":2,"GA":2,"GD":0,"PTS":1},
"Poland":{"P":1,"W":0,"D":1,"L":0,"GF":2,"GA":2,"GD":0,"PTS":1},
"Republic of Ireland":{"P":1,"W":0,"D":0,"L":1,"GF":1,"GA":2,"GD":-1,"PTS":0}
},

"A3":{
"England":{"P":1,"W":1,"D":0,"L":0,"GF":6,"GA":1,"GD":5,"PTS":3},
"Spain":{"P":1,"W":1,"D":0,"L":0,"GF":3,"GA":0,"GD":3,"PTS":3},
"Iceland":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":3,"GD":-3,"PTS":0},
"Ukraine":{"P":1,"W":0,"D":0,"L":1,"GF":1,"GA":6,"GD":-5,"PTS":0}
},

"A4":{
"Germany":{"P":1,"W":1,"D":0,"L":0,"GF":5,"GA":0,"GD":5,"PTS":3},
"Norway":{"P":1,"W":1,"D":0,"L":0,"GF":1,"GA":0,"GD":1,"PTS":3},
"Austria":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":1,"GD":-1,"PTS":0},
"Slovenia":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":5,"GD":-5,"PTS":0}
},

"B1":{
"Albania":{"P":1,"W":1,"D":0,"L":0,"GF":2,"GA":1,"GD":1,"PTS":3},
"Wales":{"P":1,"W":0,"D":1,"L":0,"GF":2,"GA":2,"GD":0,"PTS":1},
"Czech Republic":{"P":1,"W":0,"D":1,"L":0,"GF":2,"GA":2,"GD":0,"PTS":1},
"Montenegro":{"P":1,"W":0,"D":0,"L":1,"GF":1,"GA":2,"GD":-1,"PTS":0}
},

"B2":{
"Turkey":{"P":1,"W":1,"D":0,"L":0,"GF":3,"GA":0,"GD":3,"PTS":3},
"Switzerland":{"P":1,"W":1,"D":0,"L":0,"GF":2,"GA":0,"GD":2,"PTS":3},
"Northern Ireland":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":2,"GD":-2,"PTS":0},
"Malta":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":3,"GD":-3,"PTS":0}
},

"B3":{
"Portugal":{"P":1,"W":1,"D":0,"L":0,"GF":2,"GA":0,"GD":2,"PTS":3},
"Slovakia":{"P":1,"W":1,"D":0,"L":0,"GF":3,"GA":2,"GD":1,"PTS":3},
"Latvia":{"P":1,"W":0,"D":0,"L":1,"GF":2,"GA":3,"GD":-1,"PTS":0},
"Finland":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":2,"GD":-2,"PTS":0}
},

"B4":{
"Scotland":{"P":1,"W":1,"D":0,"L":0,"GF":5,"GA":0,"GD":5,"PTS":3},
"Belgium":{"P":1,"W":1,"D":0,"L":0,"GF":3,"GA":0,"GD":3,"PTS":3},
"Israel":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":3,"GD":-3,"PTS":0},
"Luxembourg":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":5,"GD":-5,"PTS":0}
},

"C1":{
"Lithuania":{"P":1,"W":1,"D":0,"L":0,"GF":6,"GA":1,"GD":5,"PTS":3},
"Bosnia and Herzegovina":{"P":1,"W":1,"D":0,"L":0,"GF":3,"GA":1,"GD":2,"PTS":3},
"Estonia":{"P":1,"W":0,"D":0,"L":1,"GF":1,"GA":3,"GD":-2,"PTS":0},
"Liechtenstein":{"P":1,"W":0,"D":0,"L":1,"GF":1,"GA":6,"GD":-5,"PTS":0}
},

"C2":{
"Kosovo":{"P":1,"W":1,"D":0,"L":0,"GF":6,"GA":0,"GD":6,"PTS":3},
"Croatia":{"P":1,"W":1,"D":0,"L":0,"GF":1,"GA":0,"GD":1,"PTS":3},
"Bulgaria":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":1,"GD":-1,"PTS":0},
"Gibraltar":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":6,"GD":-6,"PTS":0}
},

"C3":{
"Azerbaijan":{"P":1,"W":1,"D":0,"L":0,"GF":2,"GA":0,"GD":2,"PTS":3},
"Hungary":{"P":1,"W":0,"D":1,"L":0,"GF":0,"GA":0,"GD":0,"PTS":1},
"Andorra":{"P":1,"W":0,"D":1,"L":0,"GF":0,"GA":0,"GD":0,"PTS":1},
"North Macedonia":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":2,"GD":-2,"PTS":0}
},

"C4":{
"Greece":{"P":1,"W":1,"D":0,"L":0,"GF":3,"GA":0,"GD":3,"PTS":3},
"Faroe Islands":{"P":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"PTS":0},
"Georgia":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":3,"GD":-3,"PTS":0}
},

"C5":{
"Romania":{"P":1,"W":1,"D":0,"L":0,"GF":1,"GA":0,"GD":1,"PTS":3},
"Cyprus":{"P":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"PTS":0},
"Moldova":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":1,"GD":-1,"PTS":0}
},

"C6":{
"Kazakhstan":{"P":1,"W":1,"D":0,"L":0,"GF":3,"GA":0,"GD":3,"PTS":3},
"Belarus":{"P":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"PTS":0},
"Armenia":{"P":1,"W":0,"D":0,"L":1,"GF":0,"GA":3,"GD":-3,"PTS":0}
}
}

def win_prob(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def simulate_match(team1, team2):
    """Simulate a single match using ELO ratings."""

    elo1 = ELO_RATINGS.get(team1, 1500)
    elo2 = ELO_RATINGS.get(team2, 1500)

    p = win_prob(elo1, elo2)
    r = random.random()

    if r < p * 0.75:
        g1 = random.randint(1, 4)
        g2 = random.randint(0, 2)
    elif r < p * 0.75 + (1 - p) * 0.75:
        g1 = random.randint(0, 2)
        g2 = random.randint(1, 4)
    else:
        g1 = g2 = random.randint(0, 2)

    return g1, g2


########################################
# TABLE UPDATE
########################################

def update_table(table, t1, t2, g1, g2):

    for t in (t1, t2):
        if t not in table:
            table[t] = {"P":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"PTS":0}

    table[t1]["P"] += 1
    table[t2]["P"] += 1

    table[t1]["GF"] += g1
    table[t1]["GA"] += g2
    table[t2]["GF"] += g2
    table[t2]["GA"] += g1

    if g1 > g2:
        table[t1]["W"] += 1
        table[t2]["L"] += 1
        table[t1]["PTS"] += 3

    elif g2 > g1:
        table[t2]["W"] += 1
        table[t1]["L"] += 1
        table[t2]["PTS"] += 3

    else:
        table[t1]["D"] += 1
        table[t2]["D"] += 1
        table[t1]["PTS"] += 1
        table[t2]["PTS"] += 1

    table[t1]["GD"] = table[t1]["GF"] - table[t1]["GA"]
    table[t2]["GD"] = table[t2]["GF"] - table[t2]["GA"]


########################################
# GROUP SIMULATION
########################################

def simulate_group(group_name, teams, standings):

    table = standings.get(group_name, {}).copy()

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):

            t1 = teams[i]
            t2 = teams[j]

            g1, g2 = simulate_match(t1, t2)

            update_table(table, t1, t2, g1, g2)

    ranking = sorted(
        table.items(),
        key=lambda x: (x[1]["PTS"], x[1]["GD"], x[1]["GF"]),
        reverse=True
    )

    return ranking


########################################
# RUN ALL GROUPS
########################################

def simulate_all_groups():

    results = {}

    for g, teams in GROUPS.items():
        results[g] = simulate_group(g, teams, STANDINGS)

    return results


########################################
# MAIN
########################################

if __name__ == "__main__":

    results = simulate_all_groups()

    for g, r in results.items():

        print("\n", g)

        for i, (team, stats) in enumerate(r, 1):
            print(i, team, stats)