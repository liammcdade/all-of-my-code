# season_25_26_data.py

ELO = {
    "Arsenal": 1862, "Man City": 1858, "Liverpool": 1709, "Aston Villa": 1629,
    "Man United": 1718, "Chelsea": 1618, "Brighton": 1644, "Newcastle": 1542,
    "Brentford": 1597, "Everton": 1549, "Bournemouth": 1651, "Fulham": 1514,
    "Crystal Palace": 1477, "Forest": 1506, "Leeds": 1498, "Tottenham": 1469,
    "West Ham": 1418, "Sunderland": 1451, "Wolves": 1256, "Burnley": 1312,
}

RD = {
    "Arsenal": 88, "Man City": 83, "Liverpool": 79, "Aston Villa": 82,
    "Man United": 80, "Chelsea": 79, "Brighton": 78, "Newcastle": 77,
    "Brentford": 77, "Everton": 79, "Bournemouth": 78, "Fulham": 77,
    "Crystal Palace": 79, "Forest": 81, "Leeds": 78, "Tottenham": 78,
    "West Ham": 81, "Sunderland": 77, "Wolves": 97, "Burnley": 83,
}

CURRENT_TABLE = {
    "Arsenal":        {"MP":36,"W":24,"D":7,"L":5,"GF":68,"GA":26,"GD":42,"Pts":79,"Rem":2},
    "Man City":       {"MP":35,"W":22,"D":8,"L":5,"GF":72,"GA":32,"GD":40,"Pts":74,"Rem":3},
    "Man United":     {"MP":36,"W":18,"D":11,"L":7,"GF":63,"GA":48,"GD":15,"Pts":65,"Rem":2},
    "Liverpool":      {"MP":36,"W":17,"D":8,"L":11,"GF":60,"GA":48,"GD":12,"Pts":59,"Rem":2},
    "Aston Villa":    {"MP":36,"W":17,"D":8,"L":11,"GF":50,"GA":46,"GD":4,"Pts":59,"Rem":2},
    "Bournemouth":    {"MP":36,"W":13,"D":16,"L":7,"GF":56,"GA":52,"GD":4,"Pts":55,"Rem":2},
    "Brighton":       {"MP":36,"W":14,"D":11,"L":11,"GF":52,"GA":42,"GD":10,"Pts":53,"Rem":2},
    "Brentford":      {"MP":36,"W":14,"D":9,"L":13,"GF":52,"GA":49,"GD":3,"Pts":51,"Rem":2},
    "Chelsea":        {"MP":36,"W":13,"D":10,"L":13,"GF":55,"GA":49,"GD":6,"Pts":49,"Rem":2},
    "Everton":        {"MP":36,"W":13,"D":10,"L":13,"GF":46,"GA":46,"GD":0,"Pts":49,"Rem":2},
    "Fulham":         {"MP":36,"W":14,"D":6,"L":16,"GF":44,"GA":50,"GD":-6,"Pts":48,"Rem":2},
    "Sunderland":     {"MP":36,"W":12,"D":12,"L":12,"GF":37,"GA":46,"GD":-9,"Pts":48,"Rem":2},
    "Newcastle":      {"MP":36,"W":13,"D":7,"L":16,"GF":50,"GA":52,"GD":-2,"Pts":46,"Rem":2},
    "Crystal Palace": {"MP":35,"W":11,"D":11,"L":13,"GF":38,"GA":44,"GD":-6,"Pts":44,"Rem":3},
    "Forest":         {"MP":36,"W":11,"D":10,"L":15,"GF":45,"GA":47,"GD":-2,"Pts":43,"Rem":2},
    "Leeds":          {"MP":36,"W":10,"D":14,"L":12,"GF":48,"GA":53,"GD":-5,"Pts":44,"Rem":2},
    "Tottenham":      {"MP":36,"W":9,"D":11,"L":16,"GF":46,"GA":55,"GD":-9,"Pts":38,"Rem":2},
    "West Ham":       {"MP":36,"W":9,"D":9,"L":18,"GF":42,"GA":62,"GD":-20,"Pts":36,"Rem":2},
    "Burnley":        {"MP":36,"W":4,"D":9,"L":23,"GF":37,"GA":73,"GD":-36,"Pts":21,"Rem":2},
    "Wolves":         {"MP":36,"W":3,"D":9,"L":24,"GF":25,"GA":66,"GD":-41,"Pts":18,"Rem":2},
}

FIXTURES = [
    ("Man City", "Crystal Palace"), ("Aston Villa", "Liverpool"),
    ("Man United", "Forest"), ("Brentford", "Crystal Palace"),
    ("Everton", "Sunderland"), ("Leeds", "Brighton"),
    ("Wolves", "Fulham"), ("Newcastle", "West Ham"),
    ("Arsenal", "Burnley"), ("Bournemouth", "Man City"),
    ("Chelsea", "Tottenham"), ("Brighton", "Man United"),
    ("Burnley", "Wolves"), ("Crystal Palace", "Arsenal"),
    ("Fulham", "Newcastle"), ("Liverpool", "Brentford"),
    ("Man City", "Aston Villa"), ("Forest", "Bournemouth"),
    ("Sunderland", "Chelsea"), ("Tottenham", "Everton"),
    ("West Ham", "Leeds"),
]

EUROPEAN_ELOS = {
    "EL": {"Aston Villa": 1875, "Freiburg": 1716, "Forest": 1842, "Sporting Braga": 1712},
    "CL": {"Bayern Munich": 2008, "Arsenal": 2053, "Paris Saint-Germain": 1965, "Atletico Madrid": 1844},
    "CONF": {"Strasbourg": 1713, "Shakhtar Donetsk": 1587, "Rayo Vallecano": 1681, "Crystal Palace": 1799},
    "FA": {"Chelsea": 1841, "Man City": 1970}
}

FORM_ADJUSTMENT = {
    "Arsenal": 18, "Man City": 27, "Man United": 18, "Aston Villa": 6,
    "Liverpool": 18, "Chelsea": -6, "Brentford": 9, "Bournemouth": 12,
    "Brighton": 9, "Everton": 3, "Sunderland": 0, "Fulham": 3,
    "Crystal Palace": -3, "Newcastle": -3, "Leeds": 0, "Forest": 3,
    "West Ham": 0, "Tottenham": -21, "Burnley": -27, "Wolves": -18,
}

INJURY_PENALTY = {
    "Bournemouth": 30, "Arsenal": 60, "Aston Villa": 20, "Brentford": 70,
    "Brighton": 50, "Burnley": 70, "Chelsea": 70, "Crystal Palace": 50,
    "Everton": 20, "Fulham": 30, "Leeds": 20, "Liverpool": 70,
    "Man City": 40, "Man United": 60, "Newcastle": 40, "Forest": 70,
    "Sunderland": 60, "Tottenham": 60, "West Ham": 10, "Wolves": 50,
}
