"""Unified Premier League + European + Carabao Cup simulation (optimized Python port)."""
import math
import random
import sys
import time
import functools
from collections import defaultdict, Counter

# =============================================================================
# CONSTANTS
# =============================================================================
HOME_ADVANTAGE_ELO = 40.0
ELO_SCALE = 400.0
LEAGUE_AVERAGE_ELO = 1500.0
MAX_GOALS = 10
NUM_PL_SIMS = 5000
PL_TOTAL_FIXTURES = 380
PL_ELO_MAX_PULL = 1.0
BASE_HOME_XG = 1.6644
BASE_AWAY_XG = 1.1200
XG_ELO_SENSITIVITY = 0.002
EXTRA_TIME_XG_FACTOR = 0.333

# ln(10)/400 — used to replace 10 ** (x/400) with exp(x * _ELO_LN_SCALE)
_ELO_LN_SCALE = math.log(10.0) / ELO_SCALE

_FATIGUE_BASE = {"UCL": 8.0, "UEL": 6.0, "UECL": 5.0}

_EURO_K = {
    ("UCL", "league"): 36.0, ("UCL", "early_ko"): 40.0, ("UCL", "late_ko"): 48.0,
    ("UEL", "league"): 28.0, ("UEL", "early_ko"): 32.0, ("UEL", "late_ko"): 38.0,
    ("UECL", "league"): 24.0, ("UECL", "early_ko"): 27.0, ("UECL", "late_ko"): 32.0,
    ("PL", "league"): 20.0,
}


def fatigue_base(comp):
    return _FATIGUE_BASE.get(comp, 0.0)


def euro_k(comp, stage):
    return _EURO_K.get((comp, stage), 20.0)


def knockout_k(comp, round_idx):
    if round_idx in (0, 1):
        return euro_k(comp, "early_ko")
    return euro_k(comp, "late_ko")


# =============================================================================
# RNG WRAPPER + POISSON
# =============================================================================
class Rng:
    __slots__ = ('_rng',)

    def __init__(self, seed):
        self._rng = random.Random(seed)

    def float(self):
        return self._rng.random()

    def poisson(self, lam):
        random = self._rng.random
        l = math.exp(-lam)
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= random()
            if p <= l:
                return k - 1

    def poisson_L(self, L):
        """Poisson sampler given L = exp(-lam). Avoids the exp() call."""
        random = self._rng.random
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= random()
            if p <= L:
                return k - 1

    def shuffle(self, lst):
        self._rng.shuffle(lst)


# =============================================================================
# ELO / GOAL HELPERS
# =============================================================================
def update_elo(elo_w, elo_l, k):
    expected = 1.0 / (1.0 + math.exp((elo_l - elo_w) * _ELO_LN_SCALE))
    return (elo_w + k * (1.0 - expected), elo_l + k * (expected - 1.0))


def expected_goals(elo_h, elo_a):
    d = elo_h - elo_a
    return (
        BASE_HOME_XG * math.exp(XG_ELO_SENSITIVITY * d),
        BASE_AWAY_XG * math.exp(-XG_ELO_SENSITIVITY * d),
    )


def sample_score(rng, lam_h, lam_a):
    h = min(rng.poisson(lam_h), MAX_GOALS)
    a = min(rng.poisson(lam_a), MAX_GOALS)
    return (h, a)


def max_consecutive_wins(results):
    best = 0
    cur = 0
    for r in results:
        if r == 'W':
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


# =============================================================================
# DATA TABLES
# =============================================================================
def preset_pl_elos():
    rows = [
        ("Man City", 1960.0), ("Arsenal", 2072.0), ("Man United", 1864.0),
        ("Liverpool", 1881.0), ("Brighton", 1832.0), ("Brentford", 1789.0),
        ("Aston Villa", 1922.0), ("Bournemouth", 1803.0), ("Chelsea", 1827.0),
        ("Everton", 1750.0), ("Leeds", 1760.0), ("Newcastle", 1779.0),
        ("Crystal Palace", 1787.0), ("Forest", 1775.0), ("Sunderland", 1716.0),
        ("Fulham", 1724.0), ("Hull", 1611.0), ("Tottenham", 1752.0),
        ("Ipswich", 1574.0), ("Coventry", 1500.0),
    ]
    return dict(rows)


def preset_ucl_elos():
    rows = [
        ("Arsenal", 2076.0), ("Bayern Munich", 2068.0), ("FC Barcelona", 2033.0),
        ("Paris Saint-Germain", 2025.0), ("Man City", 1985.0), ("Real Madrid", 1966.0),
        ("Sporting CP", 1906.0), ("Aston Villa", 1901.0), ("Inter Milan", 1892.0),
        ("Borussia Dortmund", 1881.0), ("Atletico Madrid", 1866.0), ("Liverpool", 1856.0),
        ("Man United", 1848.0), ("Roma", 1847.0), ("Real Betis", 1832.0),
        ("Bodø/Glimt", 1829.0), ("Club Brugge", 1826.0), ("FC Porto", 1820.0),
        ("Como", 1789.0), ("PSV Eindhoven", 1783.0), ("RB Leipzig", 1777.0),
        ("VfB Stuttgart", 1776.0), ("Napoli", 1766.0), ("Villarreal FC", 1753.0),
        ("Viking", 1752.0), ("RC Lens", 1745.0), ("AEK Athens", 1742.0),
        ("Fenerbahçe", 1740.0), ("Lille OSC", 1730.0), ("Galatasaray", 1722.0),
        ("Shakhtar Donetsk", 1703.0), ("Feyenoord", 1682.0), ("Slavia Prague", 1656.0),
        ("Sabah FK", 1646.0), ("LASK", 1616.0), ("Slovan Bratislava", 1616.0),
    ]
    return dict(rows)


def preset_uel_elos():
    rows = [
        ("Bayer Leverkusen", 1868.0), ("Benfica", 1854.0), ("Union Saint-Gilloise", 1824.0),
        ("Juventus", 1817.0), ("Bournemouth", 1803.0), ("Milan", 1793.0),
        ("Crystal Palace", 1787.0), ("Olympique Lyonnais", 1768.0), ("Olympiacos", 1725.0),
        ("Rennes", 1721.0), ("Sunderland", 1716.0), ("Omonia", 1715.0),
        ("Real Sociedad", 1698.0), ("Celta Vigo", 1696.0), ("Dinamo Zagreb", 1692.0),
        ("Marseille", 1678.0), ("Celtic", 1676.0), ("Lech Poznań", 1676.0),
        ("Sparta Prague", 1675.0), ("TSG Hoffenheim", 1670.0), ("Hapoel Be'er Sheva", 1669.0),
        ("Beşiktaş", 1645.0), ("Viktoria Plzeň", 1645.0), ("Red Bull Salzburg", 1642.0),
        ("AZ Alkmaar", 1641.0), ("Sturm Graz", 1620.0), ("Anderlecht", 1614.0),
        ("NK Celje", 1596.0), ("Levski Sofia", 1571.0), ("Jagiellonia Białystok", 1557.0),
        ("NEC Nijmegen", 1557.0), ("OFI Crete", 1495.0), ("Lillestrøm", 1463.0),
        ("Torreense", 1438.0), ("Ararat-Armenia", 1514.0), ("Ferencváros", 1747.0),
    ]
    return dict(rows)


def preset_uecl_elos():
    rows = [
        ("Brighton", 1832.0), ("Monaco", 1799.0), ("Freiburg", 1784.0),
        ("Atalanta", 1772.0), ("Midtjylland", 1743.0), ("Red Star Belgrade", 1735.0),
        ("Braga", 1705.0), ("Lugano", 1679.0), ("Ajax", 1673.0),
        ("FC Copenhagen", 1670.0), ("Panathinaikos", 1662.0), ("Getafe", 1654.0),
        ("Twente", 1644.0), ("Gent", 1643.0), ("Hajduk Split", 1634.0),
        ("FC Nordsjaelland", 1620.0), ("Universitatea Craiova", 1620.0), ("Trabzonspor", 1618.0),
        ("Pafos FC", 1613.0), ("Thun", 1599.0), ("AGF", 1580.0),
        ("Sint Truiden", 1573.0), ("Hearts", 1567.0), ("Brann", 1567.0),
        ("FK Jablonec", 1565.0), ("FK Riga", 1546.0), ("Borac Banja Luka", 1540.0),
        ("Mjallby", 1505.0), ("Egnatia Rrogozhine", 1496.0), ("CSKA Sofia", 1495.0),
        ("KuPS Kuopio", 1489.0), ("Inter Club d'Escaldes", 1481.0), ("Kairat", 1469.0),
        ("FK Kauno Zalgiris", 1465.0), ("Iberia", 1438.0), ("Lincoln Red Imps", 1408.0),
    ]
    return dict(rows)


def association_map():
    rows = [
        ("AEK Athens", "Greece"), ("LASK", "Austria"), ("Club Brugge", "Belgium"),
        ("Aston Villa", "England"), ("Borussia Dortmund", "Germany"), ("Villarreal FC", "Spain"),
        ("FC Porto", "Portugal"), ("Man City", "England"), ("Lille OSC", "France"),
        ("Real Betis", "Spain"), ("Real Madrid", "Spain"), ("Inter Milan", "Italy"),
        ("FC Barcelona", "Spain"), ("Feyenoord", "Netherlands"), ("VfB Stuttgart", "Germany"),
        ("Viking", "Norway"), ("Liverpool", "England"), ("Atletico Madrid", "Spain"),
        ("Paris Saint-Germain", "France"), ("Slovan Bratislava", "Slovakia"),
        ("Sporting CP", "Portugal"), ("Galatasaray", "Turkey"), ("Napoli", "Italy"),
        ("Arsenal", "England"), ("Fenerbahçe", "Turkey"), ("Roma", "Italy"),
        ("PSV Eindhoven", "Netherlands"), ("Shakhtar Donetsk", "Ukraine"),
        ("Como", "Italy"), ("RB Leipzig", "Germany"), ("Bayern Munich", "Germany"),
        ("Bodø/Glimt", "Norway"), ("Man United", "England"), ("Sabah FK", "Azerbaijan"),
        ("Slavia Prague", "Czech Republic"), ("RC Lens", "France"),
        ("Ararat-Armenia", "Armenia"), ("Sparta Prague", "Czech Republic"),
        ("Omonia", "Cyprus"), ("Celta Vigo", "Spain"), ("Milan", "Italy"),
        ("Benfica", "Portugal"), ("Bayer Leverkusen", "Germany"), ("NK Celje", "Slovenia"),
        ("Hapoel Be'er Sheva", "Israel"), ("Dinamo Zagreb", "Croatia"), ("Olympiacos", "Greece"),
        ("Jagiellonia Białystok", "Poland"), ("Anderlecht", "Belgium"),
        ("Olympique Lyonnais", "France"), ("Sturm Graz", "Austria"), ("Rennes", "France"),
        ("Sunderland", "England"), ("AZ Alkmaar", "Netherlands"), ("OFI Crete", "Greece"),
        ("TSG Hoffenheim", "Germany"), ("Levski Sofia", "Bulgaria"), ("Red Bull Salzburg", "Austria"),
        ("Beşiktaş", "Turkey"), ("Marseille", "France"), ("Celtic", "Scotland"),
        ("Ferencváros", "Hungary"), ("Crystal Palace", "England"), ("Lech Poznań", "Poland"),
        ("Viktoria Plzeň", "Czech Republic"), ("Union Saint-Gilloise", "Belgium"),
        ("Juventus", "Italy"), ("NEC Nijmegen", "Netherlands"), ("Lillestrøm", "Norway"),
        ("Torreense", "Portugal"), ("Real Sociedad", "Spain"), ("Bournemouth", "England"),
        ("Lugano", "Switzerland"), ("Red Star Belgrade", "Serbia"), ("Hajduk Split", "Croatia"),
        ("Ajax", "Netherlands"), ("Gent", "Belgium"), ("AGF", "Denmark"),
        ("Egnatia Rrogozhine", "Albania"), ("Midtjylland", "Denmark"), ("KuPS Kuopio", "Finland"),
        ("Trabzonspor", "Turkey"), ("Mjallby", "Sweden"), ("Inter Club d'Escaldes", "Andorra"),
        ("Panathinaikos", "Greece"), ("Borac Banja Luka", "Bosnia"), ("CSKA Sofia", "Bulgaria"),
        ("Monaco", "France"), ("FK Riga", "Latvia"), ("Kairat", "Kazakhstan"),
        ("Universitatea Craiova", "Romania"), ("Getafe", "Spain"), ("Atalanta", "Italy"),
        ("Pafos FC", "Cyprus"), ("Brighton", "England"), ("FK Kauno Zalgiris", "Lithuania"),
        ("FC Copenhagen", "Denmark"), ("Braga", "Portugal"), ("Twente", "Netherlands"),
        ("Thun", "Switzerland"), ("Hearts", "Scotland"), ("FC Nordsjaelland", "Denmark"),
        ("Sint Truiden", "Belgium"), ("Iberia", "Georgia"), ("Freiburg", "Germany"),
        ("FK Jablonec", "Czech Republic"), ("Brann", "Norway"), ("Lincoln Red Imps", "Gibraltar"),
    ]
    return dict(rows)


def assoc_entrants():
    rows = [
        ("England", 9), ("Spain", 8), ("Italy", 8), ("Germany", 8), ("France", 7),
        ("Netherlands", 6), ("Portugal", 6), ("Belgium", 5), ("Turkey", 5),
        ("Czech Republic", 5), ("Austria", 5), ("Greece", 5), ("Switzerland", 4),
        ("Scotland", 4), ("Denmark", 4), ("Norway", 4), ("Poland", 4), ("Croatia", 4),
        ("Serbia", 3), ("Romania", 3), ("Israel", 3), ("Cyprus", 3), ("Sweden", 3),
        ("Bulgaria", 3), ("Hungary", 3), ("Slovakia", 3), ("Slovenia", 2),
        ("Azerbaijan", 2), ("Kazakhstan", 2), ("Ukraine", 2), ("Russia", 2),
        ("Bosnia", 2), ("Albania", 2), ("Armenia", 2), ("Georgia", 2),
        ("Finland", 2), ("Latvia", 2), ("Lithuania", 2), ("Andorra", 1), ("Gibraltar", 1),
    ]
    return dict(rows)


ACTUAL_RESULTS_ARR = [
    (("Arsenal", "Coventry"), (3, 0)), (("Hull", "Man United"), (2, 0)),
    (("Everton", "Crystal Palace"), (2, 0)), (("Ipswich", "Sunderland"), (2, 1)),
    (("Forest", "Leeds"), (0, 1)), (("Brentford", "Tottenham"), (3, 0)),
    (("Brighton", "Aston Villa"), (4, 0)), (("Man City", "Bournemouth"), (2, 1)),
    (("Newcastle", "Liverpool"), (2, 2)), (("Fulham", "Chelsea"), (2, 3)),
    (("Crystal Palace", "Man City"), (1, 4)), (("Liverpool", "Forest"), (2, 2)),
    (("Bournemouth", "Everton"), (1, 1)), (("Coventry", "Hull"), (0, 1)),
    (("Tottenham", "Newcastle"), (0, 2)), (("Chelsea", "Brighton"), (4, 3)),
    (("Leeds", "Brentford"), (1, 1)), (("Sunderland", "Fulham"), (1, 0)),
    (("Man United", "Ipswich"), (5, 2)), (("Aston Villa", "Arsenal"), (0, 1)),
    (("Ipswich", "Liverpool"), (0, 2)), (("Newcastle", "Bournemouth"), (2, 2)),
    (("Brentford", "Sunderland"), (1, 1)), (("Brighton", "Leeds"), (1, 1)),
    (("Fulham", "Crystal Palace"), (2, 3)), (("Man City", "Coventry"), (1, 0)),
    (("Forest", "Tottenham"), (0, 0)), (("Hull", "Aston Villa"), (0, 0)),
    (("Everton", "Man United"), (2, 2)), (("Arsenal", "Chelsea"), (2, 1)),
    (("Aston Villa", "Forest"), (1, 2)), (("Bournemouth", "Brentford"), (2, 2)),
    (("Chelsea", "Hull"), (2, 2)), (("Crystal Palace", "Ipswich"), (2, 3)),
    (("Liverpool", "Fulham"), (0, 0)), (("Tottenham", "Everton"), (0, 0)),
    (("Sunderland", "Arsenal"), (0, 2)), (("Coventry", "Brighton"), (0, 5)),
    (("Man United", "Man City"), (0, 1)), (("Leeds", "Newcastle"), (4, 1)),
    (("Brentford", "Chelsea"), (3, 0)), (("Tottenham", "Aston Villa"), (2, 3)),
    (("Brighton", "Arsenal"), (3, 0)), (("Everton", "Ipswich"), (1, 0)),
    (("Newcastle", "Hull"), (2, 1)), (("Forest", "Coventry"), (0, 1)),
    (("Bournemouth", "Liverpool"), (0, 1)), (("Leeds", "Crystal Palace"), (0, 0)),
    (("Man City", "Sunderland"), (5, 3)), (("Fulham", "Man United"), (1, 1)),
    (("Arsenal", "Leeds"), (2, 1)), (("Chelsea", "Bournemouth"), (5, 1)),
    (("Sunderland", "Brighton"), (0, 2)), (("Aston Villa", "Brentford"), (2, 2)),
    (("Ipswich", "Fulham"), (2, 1)), (("Man United", "Tottenham"), (1, 1)),
    (("Coventry", "Newcastle"), (4, 1)), (("Crystal Palace", "Forest"), (3, 1)),
    (("Hull", "Everton"), (2, 2)), (("Liverpool", "Man City"), (0, 3)),
    (("Everton", "Chelsea"), (0, 2)), (("Brentford", "Liverpool"), (1, 2)),
    (("Fulham", "Hull"), (1, 0)), (("Man City", "Ipswich"), (3, 2)),
    (("Newcastle", "Aston Villa"), (0, 1)), (("Brighton", "Crystal Palace"), (5, 0)),
    (("Bournemouth", "Sunderland"), (2, 0)), (("Leeds", "Man United"), (0, 1)),
    (("Forest", "Arsenal"), (0, 1)),
]

CL_FIXTURES_ARR = [
    [("AEK Athens", "LASK"), ("Club Brugge", "Aston Villa"), ("Borussia Dortmund", "Villarreal FC"),
     ("FC Porto", "Man City"), ("Lille OSC", "Real Betis"), ("Real Madrid", "Inter Milan"),
     ("FC Barcelona", "Feyenoord"), ("VfB Stuttgart", "Viking"), ("Liverpool", "Atletico Madrid"),
     ("Paris Saint-Germain", "Slovan Bratislava"), ("Sporting CP", "Galatasaray"),
     ("Napoli", "Arsenal"), ("Fenerbahçe", "Roma"), ("PSV Eindhoven", "Shakhtar Donetsk"),
     ("Como", "RB Leipzig"), ("Bayern Munich", "Bodø/Glimt"), ("Man United", "Sabah FK"),
     ("Slavia Prague", "RC Lens")],
    [("RC Lens", "Sporting CP"), ("Sabah FK", "Slavia Prague"), ("Arsenal", "Lille OSC"),
     ("Atletico Madrid", "Man United"), ("Inter Milan", "Club Brugge"), ("Galatasaray", "FC Barcelona"),
     ("RB Leipzig", "PSV Eindhoven"), ("Viking", "Bayern Munich"), ("Villarreal FC", "Napoli"),
     ("Feyenoord", "Como"), ("LASK", "Liverpool"), ("Roma", "Real Madrid"),
     ("Aston Villa", "Fenerbahçe"), ("Shakhtar Donetsk", "AEK Athens"),
     ("Bodø/Glimt", "Borussia Dortmund"), ("Man City", "Paris Saint-Germain"),
     ("Real Betis", "FC Porto"), ("Slovan Bratislava", "VfB Stuttgart")],
    [("Fenerbahçe", "Slavia Prague"), ("Sabah FK", "Borussia Dortmund"), ("Roma", "Slovan Bratislava"),
     ("FC Porto", "PSV Eindhoven"), ("Liverpool", "Villarreal FC"), ("Man City", "AEK Athens"),
     ("Paris Saint-Germain", "FC Barcelona"), ("Napoli", "Bodø/Glimt"),
     ("VfB Stuttgart", "Atletico Madrid"), ("Como", "Man United"), ("Lille OSC", "Galatasaray"),
     ("Aston Villa", "Viking"), ("Club Brugge", "RC Lens"), ("Bayern Munich", "Arsenal"),
     ("Inter Milan", "Shakhtar Donetsk"), ("Real Madrid", "RB Leipzig"), ("Real Betis", "Feyenoord"),
     ("Sporting CP", "LASK")],
    [("Shakhtar Donetsk", "Sporting CP"), ("Galatasaray", "VfB Stuttgart"), ("Atletico Madrid", "Bayern Munich"),
     ("FC Barcelona", "Aston Villa"), ("Feyenoord", "Inter Milan"), ("Bodø/Glimt", "Lille OSC"),
     ("LASK", "Slovan Bratislava"), ("Man United", "Roma"), ("Villarreal FC", "Paris Saint-Germain"),
     ("AEK Athens", "Real Madrid"), ("Fenerbahçe", "Liverpool"), ("Borussia Dortmund", "Real Betis"),
     ("FC Porto", "Napoli"), ("PSV Eindhoven", "Club Brugge"), ("RB Leipzig", "Man City"),
     ("RC Lens", "Como"), ("Slavia Prague", "Arsenal"), ("Viking", "Sabah FK")],
    [("Bodø/Glimt", "LASK"), ("Galatasaray", "Aston Villa"), ("Arsenal", "Borussia Dortmund"),
     ("Como", "AEK Athens"), ("Feyenoord", "FC Porto"), ("Man City", "Napoli"), ("RB Leipzig", "RC Lens"),
     ("Real Madrid", "PSV Eindhoven"), ("Slovan Bratislava", "Real Betis"), ("Sabah FK", "FC Barcelona"),
     ("Slavia Prague", "Villarreal FC"), ("Atletico Madrid", "Viking"), ("Club Brugge", "Liverpool"),
     ("Inter Milan", "VfB Stuttgart"), ("Shakhtar Donetsk", "Fenerbahçe"), ("Lille OSC", "Bayern Munich"),
     ("Paris Saint-Germain", "Roma"), ("Sporting CP", "Man United")],
    [("Viking", "Feyenoord"), ("Villarreal FC", "Sabah FK"), ("AEK Athens", "Galatasaray"),
     ("Roma", "Sporting CP"), ("Aston Villa", "Paris Saint-Germain"), ("FC Barcelona", "Man City"),
     ("Bayern Munich", "Slavia Prague"), ("Man United", "RB Leipzig"), ("Napoli", "Club Brugge"),
     ("Real Betis", "Como"), ("Slovan Bratislava", "Shakhtar Donetsk"), ("Arsenal", "Real Madrid"),
     ("Borussia Dortmund", "Inter Milan"), ("LASK", "Fenerbahçe"), ("Liverpool", "FC Porto"),
     ("PSV Eindhoven", "Atletico Madrid"), ("RC Lens", "Bodø/Glimt"), ("VfB Stuttgart", "Lille OSC")],
    [("Bodø/Glimt", "Atletico Madrid"), ("Galatasaray", "Feyenoord"), ("AEK Athens", "Roma"),
     ("Aston Villa", "Borussia Dortmund"), ("Inter Milan", "Liverpool"), ("FC Porto", "Slavia Prague"),
     ("Lille OSC", "Slovan Bratislava"), ("Real Madrid", "LASK"), ("VfB Stuttgart", "Club Brugge"),
     ("Fenerbahçe", "Villarreal FC"), ("Sabah FK", "Napoli"), ("Como", "Paris Saint-Germain"),
     ("Man United", "Bayern Munich"), ("RB Leipzig", "Shakhtar Donetsk"), ("RC Lens", "Man City"),
     ("Real Betis", "Arsenal"), ("Sporting CP", "FC Barcelona"), ("Viking", "PSV Eindhoven")],
    [("Arsenal", "Sabah FK"), ("Roma", "Lille OSC"), ("Atletico Madrid", "Fenerbahçe"),
     ("Borussia Dortmund", "AEK Athens"), ("Club Brugge", "Bodø/Glimt"), ("Bayern Munich", "Real Betis"),
     ("FC Barcelona", "Como"), ("Shakhtar Donetsk", "Real Madrid"), ("Feyenoord", "RB Leipzig"),
     ("LASK", "FC Porto"), ("Liverpool", "RC Lens"), ("Man City", "Sporting CP"),
     ("Paris Saint-Germain", "Galatasaray"), ("PSV Eindhoven", "VfB Stuttgart"),
     ("Slavia Prague", "Aston Villa"), ("Napoli", "Viking"), ("Villarreal FC", "Man United"),
     ("Slovan Bratislava", "Inter Milan")],
]

CL_ACTUAL_RESULTS_ARR = [
    (("AEK Athens", "LASK"), (1, 0)), (("Club Brugge", "Aston Villa"), (2, 3)),
    (("Borussia Dortmund", "Villarreal FC"), (3, 2)), (("FC Porto", "Man City"), (0, 2)),
    (("Lille OSC", "Real Betis"), (2, 3)), (("Real Madrid", "Inter Milan"), (2, 1)),
    (("FC Barcelona", "Feyenoord"), (5, 1)), (("VfB Stuttgart", "Viking"), (3, 1)),
    (("Liverpool", "Atletico Madrid"), (2, 1)), (("Paris Saint-Germain", "Slovan Bratislava"), (6, 1)),
    (("Sporting CP", "Galatasaray"), (3, 1)), (("Napoli", "Arsenal"), (0, 1)),
    (("Fenerbahçe", "Roma"), (1, 1)), (("PSV Eindhoven", "Shakhtar Donetsk"), (1, 1)),
    (("Como", "RB Leipzig"), (4, 1)), (("Bayern Munich", "Bodø/Glimt"), (5, 0)),
    (("Man United", "Sabah FK"), (4, 0)), (("Slavia Prague", "RC Lens"), (2, 3)),
    (("RC Lens", "Sporting CP"), (0, 2)), (("Sabah FK", "Slavia Prague"), (2, 0)),
    (("Arsenal", "Lille OSC"), (3, 0)), (("Atletico Madrid", "Man United"), (2, 0)),
    (("Galatasaray", "FC Barcelona"), (1, 4)), (("Inter Milan", "Club Brugge"), (3, 4)),
    (("RB Leipzig", "PSV Eindhoven"), (1, 0)), (("Viking", "Bayern Munich"), (3, 3)),
    (("Villarreal FC", "Napoli"), (3, 1)), (("LASK", "Liverpool"), (3, 6)),
    (("Feyenoord", "Como"), (3, 2)), (("Man City", "Paris Saint-Germain"), (2, 4)),
    (("Roma", "Real Madrid"), (3, 4)), (("Bodø/Glimt", "Borussia Dortmund"), (1, 0)),
    (("Real Betis", "FC Porto"), (3, 2)), (("Shakhtar Donetsk", "AEK Athens"), (3, 1)),
    (("Slovan Bratislava", "VfB Stuttgart"), (0, 3)), (("Aston Villa", "Fenerbahçe"), (6, 0)),
]

UEL_FIXTURES_RAW = [
    [("Ararat-Armenia", "Sparta Praha"), ("Omonia", "Celta"), ("Milan", "Benfica"),
     ("Leverkusen", "Celje"), ("H. Beer-Sheva", "GNK Dinamo"), ("Olympiacos", "Jagiellonia"),
     ("Anderlecht", "Lyon"), ("Sturm Graz", "Rennes"), ("Sunderland", "AZ Alkmaar"),
     ("OFI Crete", "Hoffenheim"), ("Levski Sofia", "Salzburg"), ("Beşiktaş", "Marseille"),
     ("Celtic", "Ferencváros"), ("Crystal Palace", "Lech Poznań"), ("Viktoria Plzeň", "Union SG"),
     ("Juventus", "N.E.C."), ("Lillestrøm", "Torreense"), ("Real Sociedad", "Bournemouth")],
    [("Sparta Praha", "Lillestrøm"), ("AZ Alkmaar", "H. Beer-Sheva"), ("Salzburg", "Milan"),
     ("Lech Poznań", "Leverkusen"), ("Celje", "Omonia"), ("Lyon", "Crystal Palace"),
     ("Union SG", "Real Sociedad"), ("Torreense", "Sunderland"), ("Bournemouth", "Sturm Graz"),
     ("Ferencváros", "Viktoria Plzeň"), ("GNK Dinamo", "Anderlecht"), ("Jagiellonia", "Ararat-Armenia"),
     ("N.E.C.", "Levski Sofia"), ("Marseille", "Olympiacos"), ("Celta", "Juventus"),
     ("Benfica", "Celtic"), ("Rennes", "OFI Crete"), ("Hoffenheim", "Beşiktaş")],
    [("Ararat-Armenia", "AZ Alkmaar"), ("Ferencváros", "Torreense"), ("GNK Dinamo", "N.E.C."),
     ("Juventus", "Rennes"), ("Lech Poznań", "Sunderland"), ("OFI Crete", "Leverkusen"),
     ("Union SG", "H. Beer-Sheva"), ("Sturm Graz", "Marseille"), ("Bournemouth", "Milan"),
     ("Beşiktaş", "Crystal Palace"), ("Celtic", "Celta"), ("Viktoria Plzeň", "Levski Sofia"),
     ("Jagiellonia", "Anderlecht"), ("Lillestrøm", "Real Sociedad"), ("Celje", "Salzburg"),
     ("Olympiacos", "Sparta Praha"), ("Omonia", "Benfica"), ("Hoffenheim", "Lyon")],
    [("Milan", "Ferencváros"), ("Sparta Praha", "Bournemouth"), ("Crystal Palace", "Hoffenheim"),
     ("Lillestrøm", "Viktoria Plzeň"), ("N.E.C.", "Omonia"), ("Levski Sofia", "Jagiellonia"),
     ("Real Sociedad", "Lyon"), ("Anderlecht", "Salzburg"), ("Rennes", "Olympiacos"),
     ("AZ Alkmaar", "Juventus"), ("Leverkusen", "Marseille"), ("Celtic", "Beşiktaş"),
     ("H. Beer-Sheva", "OFI Crete"), ("Celta", "Union SG"), ("Torreense", "Ararat-Armenia"),
     ("Sturm Graz", "Celje"), ("Benfica", "Lech Poznań"), ("Sunderland", "GNK Dinamo")],
    [("Beşiktaş", "H. Beer-Sheva"), ("Salzburg", "Ararat-Armenia"), ("Viktoria Plzeň", "Benfica"),
     ("GNK Dinamo", "Leverkusen"), ("Olympiacos", "Milan"), ("Marseille", "Levski Sofia"),
     ("Union SG", "Lech Poznań"), ("Celta", "Bournemouth"), ("Sparta Praha", "AZ Alkmaar"),
     ("Crystal Palace", "Real Sociedad"), ("Ferencváros", "Celje"), ("Juventus", "Omonia"),
     ("N.E.C.", "Rennes"), ("OFI Crete", "Anderlecht"), ("Lyon", "Lillestrøm"),
     ("Torreense", "Celtic"), ("Sunderland", "Jagiellonia"), ("Hoffenheim", "Sturm Graz")],
    [("AZ Alkmaar", "Sturm Graz"), ("Ararat-Armenia", "N.E.C."), ("H. Beer-Sheva", "Juventus"),
     ("Jagiellonia", "Crystal Palace"), ("Marseille", "Celta"), ("Omonia", "Celtic"),
     ("Anderlecht", "Hoffenheim"), ("Rennes", "GNK Dinamo"), ("Milan", "Sunderland"),
     ("Bournemouth", "Viktoria Plzeň"), ("Leverkusen", "Beşiktaş"), ("Salzburg", "Sparta Praha"),
     ("Lech Poznań", "Ferencváros"), ("Celje", "Olympiacos"), ("Lyon", "Union SG"),
     ("Levski Sofia", "Lillestrøm"), ("Real Sociedad", "Torreense"), ("Benfica", "OFI Crete")],
    [("Beşiktaş", "Union SG"), ("Ararat-Armenia", "Celje"), ("Ferencváros", "Juventus"),
     ("Jagiellonia", "Lyon"), ("Lillestrøm", "Bournemouth"), ("N.E.C.", "Benfica"),
     ("Olympiacos", "Hoffenheim"), ("Real Sociedad", "Viktoria Plzeň"), ("Sturm Graz", "OFI Crete"),
     ("AZ Alkmaar", "GNK Dinamo"), ("Leverkusen", "Salzburg"), ("Celtic", "Marseille"),
     ("Crystal Palace", "Sparta Praha"), ("H. Beer-Sheva", "Celta"), ("Lech Poznań", "Torreense"),
     ("Levski Sofia", "Milan"), ("Anderlecht", "Sunderland"), ("Rennes", "Omonia")],
    [("Milan", "Ararat-Armenia"), ("Sparta Praha", "Rennes"), ("Bournemouth", "H. Beer-Sheva"),
     ("Salzburg", "Crystal Palace"), ("Viktoria Plzeň", "Jagiellonia"), ("GNK Dinamo", "Sturm Graz"),
     ("Juventus", "Real Sociedad"), ("Celje", "N.E.C."), ("OFI Crete", "Lech Poznań"),
     ("Marseille", "Anderlecht"), ("Lyon", "Leverkusen"), ("Omonia", "Beşiktaş"),
     ("Union SG", "Celtic"), ("Celta", "Lillestrøm"), ("Torreense", "Olympiacos"),
     ("Benfica", "AZ Alkmaar"), ("Sunderland", "Levski Sofia"), ("Hoffenheim", "Ferencváros")],
]

UEL_NAME_MAP = {
    "Sparta Praha": "Sparta Prague", "Celta": "Celta Vigo",
    "Leverkusen": "Bayer Leverkusen", "Celje": "NK Celje",
    "H. Beer-Sheva": "Hapoel Be'er Sheva", "GNK Dinamo": "Dinamo Zagreb",
    "Lyon": "Olympique Lyonnais", "Salzburg": "Red Bull Salzburg",
    "Hoffenheim": "TSG Hoffenheim", "N.E.C.": "NEC Nijmegen",
    "Union SG": "Union Saint-Gilloise", "Jagiellonia": "Jagiellonia Białystok",
}


def standardise_uel(name):
    return UEL_NAME_MAP.get(name, name)


UEL_ACTUAL_RESULTS_ARR = [
    (("Ararat-Armenia", "Sparta Prague"), (1, 4)), (("Omonia", "Celta Vigo"), (1, 0)),
    (("Milan", "Benfica"), (0, 2)), (("Bayer Leverkusen", "NK Celje"), (2, 0)),
    (("Hapoel Be'er Sheva", "Dinamo Zagreb"), (0, 0)), (("Olympiacos", "Jagiellonia Białystok"), (2, 1)),
    (("Anderlecht", "Olympique Lyonnais"), (1, 2)), (("Sturm Graz", "Rennes"), (0, 0)),
    (("Sunderland", "AZ Alkmaar"), (1, 0)), (("OFI Crete", "TSG Hoffenheim"), (2, 0)),
    (("Levski Sofia", "Red Bull Salzburg"), (0, 1)), (("Beşiktaş", "Marseille"), (4, 1)),
    (("Celtic", "Ferencváros"), (1, 3)), (("Crystal Palace", "Lech Poznań"), (4, 0)),
    (("Viktoria Plzeň", "Union Saint-Gilloise"), (0, 3)), (("Juventus", "NEC Nijmegen"), (5, 0)),
    (("Lillestrøm", "Torreense"), (1, 2)), (("Real Sociedad", "Bournemouth"), (1, 2)),
    (("Red Bull Salzburg", "Milan"), (0, 4)), (("Lech Poznań", "Bayer Leverkusen"), (0, 4)),
    (("Olympique Lyonnais", "Crystal Palace"), (3, 2)), (("NK Celje", "Omonia"), (0, 3)),
    (("Torreense", "Sunderland"), (1, 2)), (("AZ Alkmaar", "Hapoel Be'er Sheva"), (2, 1)),
    (("Sparta Prague", "Lillestrøm"), (1, 1)), (("Union Saint-Gilloise", "Real Sociedad"), (1, 1)),
    (("Benfica", "Celtic"), (4, 1)), (("Bournemouth", "Sturm Graz"), (3, 0)),
    (("Celta Vigo", "Juventus"), (1, 2)), (("Ferencváros", "Viktoria Plzeň"), (2, 1)),
    (("Rennes", "OFI Crete"), (2, 1)), (("Dinamo Zagreb", "Anderlecht"), (1, 0)),
    (("NEC Nijmegen", "Levski Sofia"), (1, 1)), (("TSG Hoffenheim", "Beşiktaş"), (2, 3)),
    (("Jagiellonia Białystok", "Ararat-Armenia"), (3, 1)), (("Marseille", "Olympiacos"), (0, 1)),
]

UECL_FIXTURES_RAW = [
    [("Lugano", "Crvena Zvezda"), ("Hajduk Split", "Ajax"), ("Gent", "Aarhus"), ("Egnatia", "Midtjylland"),
     ("KuPS Kuopio", "Trabzonspor"), ("Mjällby", "Inter Escaldes"), ("Panathinaikos", "Borac"),
     ("CSKA Sofia", "Monaco"), ("Riga", "Kairat Almaty"), ("Universitatea Craiova", "Getafe"),
     ("Atalanta", "Pafos"), ("Brighton", "Kauno Žalgiris"), ("Copenhagen", "Braga"), ("Twente", "Thun"),
     ("Hearts", "Nordsjælland"), ("Sint-Truidense", "Iberia Tbilisi"), ("Freiburg", "Jablonec"),
     ("Brann", "Lincoln Red Imps")],
    [("Kairat Almaty", "Panathinaikos"), ("Iberia Tbilisi", "Mjällby"), ("Nordsjælland", "CSKA Sofia"),
     ("Crvena Zvezda", "Copenhagen"), ("Jablonec", "Brighton"), ("Kauno Žalgiris", "Brann"),
     ("Getafe", "Lugano"), ("Inter Escaldes", "Universitatea Craiova"), ("Pafos", "Riga"),
     ("Trabzonspor", "Hearts"), ("Ajax", "Atalanta"), ("Aarhus", "Egnatia"), ("Monaco", "Freiburg"),
     ("Midtjylland", "Sint-Truidense"), ("Thun", "Hajduk Split"), ("Borac", "KuPS Kuopio"),
     ("Lincoln Red Imps", "Twente"), ("Braga", "Gent")],
    [("Aarhus", "Braga"), ("Atalanta", "Kairat Almaty"), ("Midtjylland", "Ajax"), ("Thun", "Hearts"),
     ("Crvena Zvezda", "Inter Escaldes"), ("KuPS Kuopio", "Gent"), ("Lincoln Red Imps", "Hajduk Split"),
     ("Mjällby", "Borac"), ("Trabzonspor", "Freiburg"), ("Monaco", "Nordsjælland"),
     ("Copenhagen", "Iberia Tbilisi"), ("Lugano", "Kauno Žalgiris"), ("Twente", "Pafos"),
     ("Getafe", "Brighton"), ("Sint-Truidense", "Brann"), ("Panathinaikos", "CSKA Sofia"),
     ("Riga", "Jablonec"), ("Universitatea Craiova", "Egnatia")],
    [("Kairat Almaty", "Mjällby"), ("Ajax", "Thun"), ("Brighton", "Universitatea Craiova"),
     ("Iberia Tbilisi", "Getafe"), ("Jablonec", "Lugano"), ("Kauno Žalgiris", "Riga"),
     ("Hearts", "Monaco"), ("Egnatia", "Lincoln Red Imps"), ("Pafos", "Midtjylland"),
     ("Brann", "Aarhus"), ("Nordsjælland", "Panathinaikos"), ("Borac", "Atalanta"),
     ("Hajduk Split", "Sint-Truidense"), ("Inter Escaldes", "Copenhagen"), ("Gent", "Crvena Zvezda"),
     ("CSKA Sofia", "Trabzonspor"), ("Braga", "KuPS Kuopio"), ("Freiburg", "Twente")],
    [("Kairat Almaty", "Universitatea Craiova"), ("Copenhagen", "Lugano"), ("Iberia Tbilisi", "Crvena Zvezda"),
     ("Getafe", "Inter Escaldes"), ("KuPS Kuopio", "CSKA Sofia"), ("Lincoln Red Imps", "Midtjylland"),
     ("Riga", "Atalanta"), ("Freiburg", "Panathinaikos"), ("Brann", "Braga"), ("Trabzonspor", "Jablonec"),
     ("Aarhus", "Twente"), ("Brighton", "Monaco"), ("Thun", "Gent"), ("Hearts", "Borac"),
     ("Hajduk Split", "Nordsjælland"), ("Sint-Truidense", "Ajax"), ("Egnatia", "Kauno Žalgiris"),
     ("Mjällby", "Pafos")],
    [("Ajax", "Getafe"), ("Monaco", "Lincoln Red Imps"), ("Atalanta", "Mjällby"), ("Lugano", "Sint-Truidense"),
     ("Midtjylland", "Hajduk Split"), ("Nordsjælland", "KuPS Kuopio"), ("Twente", "Kairat Almaty"),
     ("Borac", "Riga"), ("Crvena Zvezda", "Trabzonspor"), ("Jablonec", "Iberia Tbilisi"),
     ("Kauno Žalgiris", "Freiburg"), ("Inter Escaldes", "Aarhus"), ("Gent", "Brann"),
     ("Pafos", "Hearts"), ("Panathinaikos", "Brighton"), ("CSKA Sofia", "Thun"),
     ("Braga", "Egnatia"), ("Universitatea Craiova", "Copenhagen")],
]

UECL_NAME_MAP = {
    "Crvena Zvezda": "Red Star Belgrade", "Sint-Truidense": "Sint Truiden",
    "Nordsjælland": "FC Nordsjaelland", "Kauno Žalgiris": "FK Kauno Zalgiris",
    "Borac": "Borac Banja Luka", "Jablonec": "FK Jablonec", "Riga": "FK Riga",
    "Aarhus": "AGF", "Inter Escaldes": "Inter Club d'Escaldes",
    "Iberia Tbilisi": "Iberia", "Egnatia": "Egnatia Rrogozhine",
    "Pafos": "Pafos FC", "Mjällby": "Mjallby", "Kairat Almaty": "Kairat",
    "Copenhagen": "FC Copenhagen", "KuPS": "KuPS Kuopio",
}


def standardise_uecl(name):
    return UECL_NAME_MAP.get(name, name)


UECL_ACTUAL_RESULTS_ARR = [
    (("Hajduk Split", "Ajax"), (2, 1)), (("CSKA Sofia", "Monaco"), (1, 2)),
    (("Lugano", "Red Star Belgrade"), (3, 2)), (("KuPS Kuopio", "Trabzonspor"), (2, 4)),
    (("Panathinaikos", "Borac Banja Luka"), (2, 1)), (("Mjallby", "Inter Club d'Escaldes"), (2, 0)),
    (("Gent", "AGF"), (1, 0)), (("Egnatia Rrogozhine", "Midtjylland"), (1, 1)),
    (("Universitatea Craiova", "Getafe"), (1, 1)), (("FK Riga", "Kairat"), (1, 1)),
    (("Brighton", "FK Kauno Zalgiris"), (4, 0)), (("Atalanta", "Pafos FC"), (3, 1)),
    (("Freiburg", "FK Jablonec"), (3, 2)), (("Hearts", "FC Nordsjaelland"), (1, 1)),
    (("Sint Truiden", "Iberia"), (2, 0)), (("Brann", "Lincoln Red Imps"), (2, 1)),
    (("FC Copenhagen", "Braga"), (3, 0)), (("Twente", "Thun"), (1, 0)),
]


# =============================================================================
# HELPERS — build lookup tables
# =============================================================================
def build_full_round_robin(actual):
    teams = sorted({t for (h, a), _ in actual for t in (h, a)})
    fixtures = []
    for home in teams:
        for away in teams:
            if home != away:
                fixtures.append((home, away))
    return fixtures


def results_to_map(arr):
    return dict(arr)


def flatten_fixtures(fixtures):
    return [f for r in fixtures for f in r]


# =============================================================================
# ELO REGRESSION / RATING BUILDERS
# =============================================================================
def regress_elos(elos, games_played, total_games, mean, max_pull):
    if total_games == 0:
        return dict(elos)
    frac = max(0.0, min(1.0, games_played / total_games))
    pull = max(0.0, min(1.0, max_pull)) * (1.0 - frac)
    return {t: mean + (e - mean) * (1.0 - pull) for t, e in elos.items()}


def build_current_pl_ratings(actual, pl_teams, preset, k_prior):
    base = {t: preset.get(t, LEAGUE_AVERAGE_ELO) for t in pl_teams}
    observed = dict(base)
    for (h, a), (hg, ag) in actual.items():
        eh, ea = observed[h], observed[a]
        if hg > ag:
            nh, na = update_elo(eh, ea, 20.0)
            observed[h], observed[a] = nh, na
        elif ag > hg:
            na, nh = update_elo(ea, eh, 20.0)
            observed[a], observed[h] = na, nh
        else:
            exp_h = 1.0 / (1.0 + math.exp((ea - eh) * _ELO_LN_SCALE))
            observed[h] = eh + 20.0 * (0.5 - exp_h)
            observed[a] = ea + 20.0 * (exp_h - 0.5)
    n = len(actual)
    w_prior = k_prior / (k_prior + n)
    return {t: w_prior * base[t] + (1.0 - w_prior) * observed[t] for t in pl_teams}


# =============================================================================
# EUROPEAN COMPETITION
# =============================================================================
class EuroSimResult:
    __slots__ = ('winner', 'elim_rounds', 'ranking', 'league_points', 'league_wins',
                 'league_draws', 'ko_match_pts', 'team_results')

    def __init__(self, winner, elim_rounds, ranking, league_points, league_wins,
                 league_draws, ko_match_pts, team_results):
        self.winner = winner
        self.elim_rounds = elim_rounds
        self.ranking = ranking
        self.league_points = league_points
        self.league_wins = league_wins
        self.league_draws = league_draws
        self.ko_match_pts = ko_match_pts
        self.team_results = team_results


class EuropeanCompetition:
    def __init__(self, name, fixtures, pl_elos, pl_teams, actual_results, preset=None):
        team_set = set()
        for r in fixtures:
            for h, a in r:
                team_set.add(h)
                team_set.add(a)
        self.teams = sorted(team_set)
        self.name = name

        base_elos = {}
        for t in self.teams:
            if preset is not None and t in preset:
                e = preset[t]
            elif t in pl_teams and t in pl_elos:
                e = pl_elos[t]
            else:
                e = LEAGUE_AVERAGE_ELO
            base_elos[t] = e
        self.base_elos = base_elos
        self.elos = dict(base_elos)

        # English (PL) teams that participate in this competition — used to
        # decide when to early-stop the knockout phase.
        self.english_teams = frozenset(t for t in self.teams if t in pl_teams)

        team_to_idx = {t: i for i, t in enumerate(self.teams)}
        self.team_to_idx = team_to_idx

        flat = flatten_fixtures(fixtures)
        self.fixture_h = []
        self.fixture_a = []
        self.lam_h_pre = []
        self.lam_a_pre = []
        self.actual_hg = [0] * len(flat)
        self.actual_ag = [0] * len(flat)
        mask = [False] * len(flat)

        for i, (h, a) in enumerate(flat):
            self.fixture_h.append(team_to_idx[h])
            self.fixture_a.append(team_to_idx[a])
            eh = base_elos[h] + HOME_ADVANTAGE_ELO
            ea = base_elos[a]
            lh, la = expected_goals(eh, ea)
            self.lam_h_pre.append(lh)
            self.lam_a_pre.append(la)
            if (h, a) in actual_results:
                hg, ag = actual_results[(h, a)]
                self.actual_hg[i] = hg
                self.actual_ag[i] = ag
                mask[i] = True
        self.actual_mask = mask
        self.has_actual = any(mask)

        # Precompute exp(-lam) for the Poisson sampler — these are fixed per sim.
        self.exp_h_pre = [math.exp(-l) for l in self.lam_h_pre]
        self.exp_a_pre = [math.exp(-l) for l in self.lam_a_pre]

    def simulate(self, rng, track=(), stop_when_no_pl_teams=True):
        self.elos = self.base_elos.copy()
        n_teams = len(self.teams)
        n_fix = len(self.fixture_h)
        k = euro_k(self.name, "league")

        teams_list = self.teams
        team_to_idx = self.team_to_idx
        track_idx_set = {team_to_idx[t] for t in track if t in team_to_idx}
        team_results_idx = {idx: [] for idx in track_idx_set}

        # --- League phase: single fused pass (sample + tables + Elo + tracking) ---
        pts = [0] * n_teams
        wins = [0] * n_teams
        draws = [0] * n_teams
        gf = [0] * n_teams
        ga = [0] * n_teams
        away_goals = [0] * n_teams
        away_wins = [0] * n_teams

        random = rng._rng.random
        exp_h_pre = self.exp_h_pre
        exp_a_pre = self.exp_a_pre
        fixture_h = self.fixture_h
        fixture_a = self.fixture_a
        elos = self.elos
        has_actual = self.has_actual
        actual_mask = self.actual_mask
        actual_hg = self.actual_hg
        actual_ag = self.actual_ag

        for i in range(n_fix):
            # Poisson sample for home (inlined, L precomputed)
            L = exp_h_pre[i]
            kk = 0
            p = 1.0
            while True:
                kk += 1
                p *= random()
                if p <= L:
                    break
            hg_v = kk - 1
            if hg_v > MAX_GOALS:
                hg_v = MAX_GOALS

            L = exp_a_pre[i]
            kk = 0
            p = 1.0
            while True:
                kk += 1
                p *= random()
                if p <= L:
                    break
            ag_v = kk - 1
            if ag_v > MAX_GOALS:
                ag_v = MAX_GOALS

            if has_actual and actual_mask[i]:
                hg_v = actual_hg[i]
                ag_v = actual_ag[i]

            h = fixture_h[i]
            a = fixture_a[i]

            gf[h] += hg_v; ga[h] += ag_v
            gf[a] += ag_v; ga[a] += hg_v
            away_goals[a] += ag_v

            if hg_v > ag_v:
                pts[h] += 3; wins[h] += 1
                rh, ra = 'W', 'L'
            elif ag_v > hg_v:
                pts[a] += 3; wins[a] += 1; away_wins[a] += 1
                rh, ra = 'L', 'W'
            else:
                pts[h] += 1; pts[a] += 1
                draws[h] += 1; draws[a] += 1
                rh, ra = 'D', 'D'

            # Sequential Elo update
            th = teams_list[h]
            ta = teams_list[a]
            eh = elos[th]
            ea = elos[ta]
            if hg_v > ag_v:
                nh, na = update_elo(eh, ea, k)
                elos[th] = nh; elos[ta] = na
            elif ag_v > hg_v:
                na, nh = update_elo(ea, eh, k)
                elos[ta] = na; elos[th] = nh
            else:
                exp_h = 1.0 / (1.0 + math.exp((ea - eh) * _ELO_LN_SCALE))
                elos[th] = eh + k * (0.5 - exp_h)
                elos[ta] = ea + k * (exp_h - 0.5)

            if h in track_idx_set:
                team_results_idx[h].append(rh)
            if a in track_idx_set:
                team_results_idx[a].append(ra)

        gd = [gf[i] - ga[i] for i in range(n_teams)]
        opp_pts = [0] * n_teams
        opp_gd = [0] * n_teams
        opp_gf = [0] * n_teams
        for i in range(n_fix):
            h = fixture_h[i]; a = fixture_a[i]
            opp_pts[h] += pts[a]; opp_pts[a] += pts[h]
            opp_gd[h] += gd[a]; opp_gd[a] += gd[h]
            opp_gf[h] += gf[a]; opp_gf[a] += gf[h]

        tiebreak = [rng.float() * 0.0001 for _ in range(n_teams)]
        order = list(range(n_teams))
        order.sort(key=lambda i: (
            -pts[i], -gd[i], -gf[i], -away_goals[i], -wins[i], -away_wins[i],
            -opp_pts[i], -opp_gd[i], -opp_gf[i], tiebreak[i]))
        ranking = [teams_list[i] for i in order]

        # Convert tracked results to name keys (matches original semantics)
        team_results = {teams_list[idx]: v for idx, v in team_results_idx.items()}

        # --- Knockout phase (may early-stop if no English teams remain) ---
        qualified = ranking[:24]
        winner, elim_rounds, ko_match_pts, ko_team_results = \
            simulate_knockout_phase(qualified, self.elos, self.name, rng,
                                    track=track,
                                    english_teams=self.english_teams,
                                    stop_when_no_english=stop_when_no_pl_teams)

        for t in self.teams:
            elim_rounds.setdefault(t, -1)

        combined = {}
        for t in track:
            if t not in team_to_idx:
                continue
            v = list(team_results.get(t, []))
            v.extend(ko_team_results.get(t, []))
            combined[t] = v

        league_points = {teams_list[i]: pts[i] for i in range(n_teams)}
        league_wins = {teams_list[i]: wins[i] for i in range(n_teams)}
        league_draws = {teams_list[i]: draws[i] for i in range(n_teams)}
        ko_pts_full = {t: ko_match_pts.get(t, 0.0) for t in self.teams}

        return EuroSimResult(
            winner=winner,
            elim_rounds=elim_rounds,
            ranking=ranking,
            league_points=league_points,
            league_wins=league_wins,
            league_draws=league_draws,
            ko_match_pts=ko_pts_full,
            team_results=combined,
        )


# =============================================================================
# KNOCKOUT PHASE (with English-team early stopping)
# =============================================================================
def simulate_two_legged_tie(team1, team2, elos, comp, round_idx, rng):
    e1 = elos.get(team1, LEAGUE_AVERAGE_ELO)
    e2 = elos.get(team2, LEAGUE_AVERAGE_ELO)

    # Leg 1: team2 at home
    lh1, la1 = expected_goals(e2 + HOME_ADVANTAGE_ELO, e1)
    l1_h, l1_a = sample_score(rng, lh1, la1)
    if l1_h > l1_a:
        r1_t1, r1_t2 = 'L', 'W'
    elif l1_h < l1_a:
        r1_t1, r1_t2 = 'W', 'L'
    else:
        r1_t1, r1_t2 = 'D', 'D'

    # Leg 2: team1 at home
    lh2, la2 = expected_goals(e1 + HOME_ADVANTAGE_ELO, e2)
    l2_h, l2_a = sample_score(rng, lh2, la2)
    if l2_h > l2_a:
        r2_t1, r2_t2 = 'W', 'L'
    elif l2_h < l2_a:
        r2_t1, r2_t2 = 'L', 'W'
    else:
        r2_t1, r2_t2 = 'D', 'D'

    agg1 = l1_a + l2_h
    agg2 = l1_h + l2_a

    _W = 2.0
    _D = 1.0
    pts_map = {
        team1: (_W if r1_t1 == 'W' else _D if r1_t1 == 'D' else 0.0)
             + (_W if r2_t1 == 'W' else _D if r2_t1 == 'D' else 0.0),
        team2: (_W if r1_t2 == 'W' else _D if r1_t2 == 'D' else 0.0)
             + (_W if r2_t2 == 'W' else _D if r2_t2 == 'D' else 0.0),
    }
    leg_results = {team1: [r1_t1, r2_t1], team2: [r1_t2, r2_t2]}

    if agg1 > agg2:
        winner, loser = team1, team2
    elif agg2 > agg1:
        winner, loser = team2, team1
    else:
        eth, eta = expected_goals(e1 + HOME_ADVANTAGE_ELO, e2)
        et1, et2 = sample_score(rng, eth * EXTRA_TIME_XG_FACTOR, eta * EXTRA_TIME_XG_FACTOR)
        tot1 = l1_a + l2_h + et1
        tot2 = l1_h + l2_a + et2
        if tot1 > tot2:
            winner, loser = team1, team2
        elif tot2 > tot1:
            winner, loser = team2, team1
        else:
            p1 = 1.0 / (1.0 + math.exp(-(e1 - e2) * _ELO_LN_SCALE))
            if rng.float() < p1:
                winner, loser = team1, team2
            else:
                winner, loser = team2, team1

    k = knockout_k(comp, round_idx)
    nw, nl = update_elo(elos[winner], elos[loser], k)
    elos[winner], elos[loser] = nw, nl
    return winner, pts_map, leg_results


def simulate_knockout_phase(qualified, elos, comp, rng, track=(),
                            english_teams=frozenset(),
                            stop_when_no_english=True):
    track_set = set(track)
    top8 = qualified[:8]
    playoff = qualified[8:24]
    elim_rounds = {t: -1 for t in qualified}
    ko_pts = {t: 0.0 for t in qualified}
    team_results = {t: [] for t in qualified if t in track_set}

    # ---- Early stop #1: no English teams qualified for the knockouts at all ----
    if stop_when_no_english and not any(t in english_teams for t in qualified):
        return None, elim_rounds, ko_pts, team_results

    def run_round(participants, round_idx):
        winners = []
        if round_idx == 0 and len(participants) == 16:
            pods = [(0, 15), (1, 14), (2, 13), (3, 12)]
            for s_lo, u_hi in pods:
                seeded = [participants[s_lo], participants[s_lo + 1]]
                unseeded = [participants[u_hi - 1], participants[u_hi]]
                rng.shuffle(seeded)
                rng.shuffle(unseeded)
                for home, away in [(seeded[0], unseeded[0]), (seeded[1], unseeded[1])]:
                    w, kp, lr = simulate_two_legged_tie(home, away, elos, comp, round_idx, rng)
                    for t, v in kp.items():
                        ko_pts[t] += v
                    for t, v in lr.items():
                        if t in track_set:
                            team_results[t].extend(v)
                    winners.append(w)
        else:
            n = len(participants)
            for i in range(n // 2):
                w, kp, lr = simulate_two_legged_tie(
                    participants[i], participants[n - 1 - i], elos, comp, round_idx, rng)
                for t, v in kp.items():
                    ko_pts[t] += v
                for t, v in lr.items():
                    if t in track_set:
                        team_results[t].extend(v)
                winners.append(w)
        return winners

    # Playoff (round 0)
    winners = run_round(playoff, 0)
    winner_set = set(winners)
    for t in playoff:
        if t not in winner_set:
            elim_rounds[t] = 0

    # Pod shuffles for R16
    pod_a = winners[0:2].copy()
    pod_b = winners[2:4].copy()
    pod_c = winners[4:6].copy()
    pod_d = winners[6:8].copy()
    for p in (pod_a, pod_b, pod_c, pod_d):
        rng.shuffle(p)

    r16_field = [
        top8[0], top8[1], pod_d[0], pod_d[1],
        top8[2], top8[3], pod_c[0], pod_c[1],
        top8[4], top8[5], pod_b[0], pod_b[1],
        top8[6], top8[7], pod_a[0], pod_a[1],
    ]

    current = r16_field
    for round_idx in range(1, 4):
        # ---- Early stop #2: no English teams remaining in this round ----
        if stop_when_no_english and not any(t in english_teams for t in current):
            return None, elim_rounds, ko_pts, team_results

        winners = run_round(current, round_idx)
        winner_set = set(winners)
        for t in current:
            if t not in winner_set:
                elim_rounds[t] = round_idx
        current = winners

    # ---- Early stop #3: no English teams in the final ----
    if stop_when_no_english and not any(t in english_teams for t in current):
        return None, elim_rounds, ko_pts, team_results

    if len(current) == 2:
        t1, t2 = current[0], current[1]
        lh, la = expected_goals(elos.get(t1, LEAGUE_AVERAGE_ELO),
                                elos.get(t2, LEAGUE_AVERAGE_ELO))
        g1, g2 = sample_score(rng, lh, la)
        if g1 != g2:
            winner, loser = (t1, t2) if g1 > g2 else (t2, t1)
        else:
            eth, eta = expected_goals(elos[t1], elos[t2])
            et1, et2 = sample_score(rng, eth * EXTRA_TIME_XG_FACTOR, eta * EXTRA_TIME_XG_FACTOR)
            if et1 != et2:
                winner, loser = (t1, t2) if et1 > et2 else (t2, t1)
            else:
                p1 = 1.0 / (1.0 + math.exp(-(elos[t1] - elos[t2]) * _ELO_LN_SCALE))
                winner, loser = (t1, t2) if rng.float() < p1 else (t2, t1)

        ko_pts[winner] += 2.0
        if t1 in track_set:
            team_results[t1].append('W' if winner == t1 else 'L')
        if t2 in track_set:
            team_results[t2].append('W' if winner == t2 else 'L')

        k = euro_k(comp, "late_ko")
        nw, nl = update_elo(elos[winner], elos[loser], k)
        elos[winner], elos[loser] = nw, nl
        elim_rounds[winner] = 5
        elim_rounds[loser] = 4
        return winner, elim_rounds, ko_pts, team_results

    w = current[0] if current else None
    return w, elim_rounds, ko_pts, team_results


# =============================================================================
# UEFA COEFFICIENT
# =============================================================================
def club_coeff_points(comp, league_position, elimination_round, league_wins, league_draws, ko_match_points):
    total = 2.0 * league_wins + league_draws + ko_match_points

    def tier(top_bonus, pos, tier_start):
        return top_bonus - 0.25 * (pos - tier_start)

    if comp == "UCL":
        if league_position <= 8:
            total += tier(12.0, league_position, 1)
        elif league_position <= 24:
            total += tier(8.0, league_position, 9)
        else:
            total += max(tier(4.0, league_position, 25), 0.0)
        total += min(4, max(0, elimination_round)) * 1.5
    elif comp == "UEL":
        if league_position <= 8:
            total += tier(6.0, league_position, 1)
        elif league_position <= 24:
            total += max(tier(4.0, league_position, 9), 0.0)
        total += min(4, max(0, elimination_round)) * 1.0
    elif comp == "UECL":
        if league_position <= 8:
            total += tier(4.0, league_position, 1)
        elif league_position <= 24:
            total += max(tier(2.0, league_position, 9), 0.0)
        total += min(4, max(0, elimination_round)) * 0.5
    return total


def all_association_coefficients(ucl, uel, uecl, assoc_map, entrants):
    assoc_clubs = defaultdict(dict)

    def add(r, comp):
        rank_map = {t: i + 1 for i, t in enumerate(r.ranking)}
        for team, elim in r.elim_rounds.items():
            assoc = assoc_map.get(team)
            if assoc is None:
                continue
            pos = rank_map.get(team, 99)
            assoc_clubs[assoc][team] = (
                comp, pos, elim,
                r.league_wins[team], r.league_draws[team], r.ko_match_pts[team],
            )

    add(ucl, "UCL")
    add(uel, "UEL")
    add(uecl, "UECL")

    out = {}
    for assoc, teams in assoc_clubs.items():
        if not teams:
            continue
        total_pts = sum(club_coeff_points(c, p, e, w, d, ko)
                        for c, p, e, w, d, ko in teams.values())
        denom = entrants.get(assoc, len(teams))
        out[assoc] = math.floor(total_pts * 1000.0 / denom) / 1000.0 if denom > 0 else 0.0
    return out


# =============================================================================
# PL SIMULATOR
# =============================================================================
class PLSimulator:
    def __init__(self, fixtures, current_ratings, actual_results):
        teams = sorted({t for f in fixtures for t in f})
        team_to_idx = {t: i for i, t in enumerate(teams)}
        self.team_to_idx = team_to_idx

        n_fixtures = len(fixtures)
        home_idx, away_idx, base_diff = [], [], []
        actual_hg = [0] * n_fixtures
        actual_ag = [0] * n_fixtures
        actual_mask = [False] * n_fixtures

        for i, (h, a) in enumerate(fixtures):
            home_idx.append(team_to_idx[h])
            away_idx.append(team_to_idx[a])
            rh = current_ratings.get(h, LEAGUE_AVERAGE_ELO)
            ra = current_ratings.get(a, LEAGUE_AVERAGE_ELO)
            base_diff.append(rh - ra + HOME_ADVANTAGE_ELO)
            if (h, a) in actual_results:
                hg, ag = actual_results[(h, a)]
                actual_hg[i], actual_ag[i] = hg, ag
                actual_mask[i] = True

        self.teams = teams
        self.n_fixtures = n_fixtures
        self.home_idx = home_idx
        self.away_idx = away_idx
        self.base_diff = base_diff
        self.inv_progress = [
            1.0 - i / (n_fixtures - 1.0) if n_fixtures > 1 else 1.0
            for i in range(n_fixtures)
        ]
        self.actual_hg = actual_hg
        self.actual_ag = actual_ag
        self.actual_mask = actual_mask
        self.has_actual = any(actual_mask)

        # Precompute baseline lambdas and exp(-lam) for the no-fatigue case.
        base_lam_h = [BASE_HOME_XG * math.exp(XG_ELO_SENSITIVITY * d) for d in base_diff]
        base_lam_a = [BASE_AWAY_XG * math.exp(-XG_ELO_SENSITIVITY * d) for d in base_diff]
        self.base_exp_h = [math.exp(-l) for l in base_lam_h]
        self.base_exp_a = [math.exp(-l) for l in base_lam_a]

    def simulate_season(self, fatigue_info, rng, track=()):
        n = len(self.teams)
        team_to_idx = self.team_to_idx
        teams_list = self.teams

        fatigue_arr = [0.0] * n
        active = [False] * n
        for team, (round_, comp) in fatigue_info.items():
            idx = team_to_idx.get(team)
            if idx is not None:
                fatigue_arr[idx] = fatigue_base(comp)
                if round_ >= 0:
                    active[idx] = True

        track_idx_set = {team_to_idx[t] for t in track if t in team_to_idx}
        team_results_idx = {idx: [] for idx in track_idx_set}

        pts = [0] * n
        gf = [0] * n
        ga = [0] * n

        random = rng._rng.random
        home_idx = self.home_idx
        away_idx = self.away_idx
        base_diff = self.base_diff
        inv_progress = self.inv_progress
        base_exp_h = self.base_exp_h
        base_exp_a = self.base_exp_a
        has_actual = self.has_actual
        actual_mask = self.actual_mask
        actual_hg = self.actual_hg
        actual_ag = self.actual_ag

        for i in range(self.n_fixtures):
            h = home_idx[i]
            a = away_idx[i]

            if active[h] or active[a]:
                h_fat = fatigue_arr[h] * inv_progress[i] if active[h] else 0.0
                a_fat = fatigue_arr[a] * inv_progress[i] if active[a] else 0.0
                diff = base_diff[i] - h_fat + a_fat
                lam_h = BASE_HOME_XG * math.exp(XG_ELO_SENSITIVITY * diff)
                lam_a = BASE_AWAY_XG * math.exp(-XG_ELO_SENSITIVITY * diff)
                L_h = math.exp(-lam_h)
                L_a = math.exp(-lam_a)
            else:
                L_h = base_exp_h[i]
                L_a = base_exp_a[i]

            # Inlined Poisson sampling
            kk = 0
            p = 1.0
            while True:
                kk += 1
                p *= random()
                if p <= L_h:
                    break
            hg = kk - 1
            if hg > MAX_GOALS:
                hg = MAX_GOALS

            kk = 0
            p = 1.0
            while True:
                kk += 1
                p *= random()
                if p <= L_a:
                    break
            ag = kk - 1
            if ag > MAX_GOALS:
                ag = MAX_GOALS

            if has_actual and actual_mask[i]:
                hg = actual_hg[i]
                ag = actual_ag[i]

            gf[h] += hg; ga[h] += ag
            gf[a] += ag; ga[a] += hg

            if hg > ag:
                pts[h] += 3
                if h in track_idx_set:
                    team_results_idx[h].append('W')
                if a in track_idx_set:
                    team_results_idx[a].append('L')
            elif ag > hg:
                pts[a] += 3
                if a in track_idx_set:
                    team_results_idx[a].append('W')
                if h in track_idx_set:
                    team_results_idx[h].append('L')
            else:
                pts[h] += 1; pts[a] += 1
                if h in track_idx_set:
                    team_results_idx[h].append('D')
                if a in track_idx_set:
                    team_results_idx[a].append('D')

        gd = [gf[i] - ga[i] for i in range(n)]
        tiebreak = [rng.float() * 0.0001 for _ in range(n)]
        order = list(range(n))
        order.sort(key=lambda i: (-pts[i], -gd[i], -gf[i], tiebreak[i]))
        ranked = [teams_list[i] for i in order]
        points_map = {teams_list[i]: pts[i] for i in range(n)}
        team_results = {teams_list[idx]: v for idx, v in team_results_idx.items()}
        return ranked, points_map, team_results


# =============================================================================
# EUROPEAN SPOT ALLOCATION
# =============================================================================
def allocate_european_spots(ranking, carabao_winner, pl_teams, ucl_winner, uel_winner,
                            uecl_winner, has_eps, fa_cup_winner):
    ucl = set(ranking[:4])
    for w in (ucl_winner, uel_winner):
        if w and w in pl_teams:
            ucl.add(w)
    if has_eps:
        for t in ranking:
            if t not in ucl:
                ucl.add(t)
                break

    uel = set()
    for t in ranking:
        if t not in ucl:
            uel.add(t)
            break

    if fa_cup_winner and fa_cup_winner in pl_teams:
        if fa_cup_winner not in ucl and fa_cup_winner not in uel:
            uel.add(fa_cup_winner)
        else:
            for t in ranking:
                if t not in ucl and t not in uel:
                    uel.add(t); break

    uecl = set()
    if carabao_winner in pl_teams and carabao_winner not in ucl and carabao_winner not in uel:
        uecl.add(carabao_winner)
    else:
        for t in ranking:
            if t not in ucl and t not in uel and t not in uecl:
                uecl.add(t); break

    if uecl_winner and uecl_winner in pl_teams and uecl_winner not in ucl:
        uel.add(uecl_winner)
        if uecl_winner in uecl:
            uecl.remove(uecl_winner)
            for t in ranking:
                if t not in ucl and t not in uel and t not in uecl:
                    uecl.add(t); break

    return {"UCL": ucl, "UEL": uel, "UECL": uecl}


# =============================================================================
# CARABAO CUP
# =============================================================================
_carabao_elo_cache = None
_fa_cup_data_cache = None

_CARABAO_NAME_MAP = {
    "Bradford City": "Bradford",
    "Peterborough United": "Peterboro",
    "Manchester City": "Man City",
    "Brighton & Hove Albion": "Brighton",
    "Newcastle United": "Newcastle",
    "Forest": "Nott'm Forest",
}


def carabao_elo():
    global _carabao_elo_cache
    if _carabao_elo_cache is None:
        rows = [
            ("Man City", 2010.78), ("Arsenal", 1989.36), ("Liverpool", 1860.73), ("Man United", 1850.89),
            ("Brighton", 1841.02), ("Bournemouth", 1824.06), ("Brentford", 1821.52), ("Aston Villa", 1786.13),
            ("Leeds", 1775.33), ("Everton", 1767.65), ("Newcastle", 1764.91), ("Chelsea", 1762.58),
            ("Nott'm Forest", 1747.80), ("Fulham", 1711.90), ("Crystal Palace", 1699.56), ("West Ham", 1681.57),
            ("Sunderland", 1672.82), ("Tottenham", 1639.38), ("Wolves", 1547.95), ("Ipswich", 1532.58),
            ("Coventry", 1504.38), ("Burnley", 1500.92), ("Southampton", 1447.66), ("Hull", 1436.60),
            ("Lincoln", 1417.82), ("Millwall", 1395.48), ("Middlesbrough", 1350.22), ("Norwich", 1334.15),
            ("Wrexham", 1327.65), ("Derby", 1304.65), ("Swansea", 1304.53), ("Birmingham", 1304.14),
            ("Cardiff", 1303.61), ("Sheffield United", 1286.61), ("Plymouth", 1275.66), ("Luton", 1274.00),
            ("Portsmouth", 1261.50), ("Stockport", 1256.67), ("Bolton", 1250.53), ("Bristol City", 1247.50),
            ("Blackburn", 1236.45), ("West Brom", 1233.42), ("Mansfield", 1230.42), ("Leicester", 1228.54),
            ("Stevenage", 1221.06), ("Milton Keynes Dons", 1218.28), ("Bromley", 1217.81), ("Bradford", 1213.60),
            ("QPR", 1212.89), ("Preston", 1212.75), ("Charlton", 1207.22), ("Oxford", 1197.43),
            ("Cambridge", 1197.04), ("Wycombe", 1195.17), ("Chesterfield", 1193.11), ("Blackpool", 1192.83),
            ("Huddersfield", 1190.23), ("Reading", 1186.25), ("Watford", 1185.31), ("Grimsby", 1181.03),
            ("Salford", 1174.96), ("Barnet", 1174.09), ("Stoke", 1167.18), ("Doncaster", 1165.70),
            ("Notts County", 1161.57), ("Bury", 1150.20), ("Wigan", 1139.49), ("Burton", 1132.10),
            ("Barnsley", 1128.18), ("Leyton Orient", 1121.87), ("Swindon", 1115.87), ("Colchester", 1114.39),
            ("Bristol Rvs", 1107.08), ("Oldham", 1105.14), ("Port Vale", 1100.96), ("Peterboro", 1095.20),
            ("Exeter", 1092.60), ("Wimbledon", 1090.09), ("Kidderminster", 1088.40), ("Crewe", 1086.77),
            ("Fleetwood Town", 1078.01), ("AFC Wimbledon", 1066.28), ("Walsall", 1055.97), ("Rotherham", 1038.82),
            ("Aldershot", 1028.07), ("Sutton", 1024.15), ("Sheffield Weds", 1023.03), ("Scarborough", 1021.02),
            ("Cheltenham", 1020.13), ("Hereford", 1018.21), ("Southend", 1015.77), ("Accrington", 1000.25),
            ("Gillingham", 999.92), ("Hartlepool", 996.02), ("Carlisle", 994.44), ("Crawley Town", 994.04),
            ("Shrewsbury", 993.95), ("Torquay", 991.08), ("Rochdale", 985.99), ("Newport County", 981.89),
            ("Boston", 980.87), ("Rushden & D", 979.65), ("Macclesfield", 979.06), ("Forest Green", 979.06),
            ("Harrogate", 976.24), ("Northampton", 959.87), ("York", 955.72), ("Dag and Red", 948.85),
            ("Halifax", 945.06), ("Darlington", 944.05), ("Tranmere", 942.64), ("Barrow", 933.53),
            ("Morecambe", 931.23), ("Yeovil", 924.14), ("Chester", 917.06), ("Scunthorpe", 847.02),
        ]
        _carabao_elo_cache = dict(rows)
    return _carabao_elo_cache


def carabao_name_map(name):
    return _CARABAO_NAME_MAP.get(name, name)


@functools.lru_cache(maxsize=None)
def get_carabao_elo(team):
    key = carabao_name_map(team)
    return carabao_elo().get(key, 1500.0)


def carabao_leg_score(rng, eh, ea):
    lh, la = expected_goals(eh, ea)
    return min(rng.poisson(lh), MAX_GOALS), min(rng.poisson(la), MAX_GOALS)


def carabao_penalty_winner(rng, a, b):
    ea = get_carabao_elo(a)
    eb = get_carabao_elo(b)
    p = 1.0 / (1.0 + math.exp((eb - ea) * _ELO_LN_SCALE))
    return a if rng.float() < p else b


def sim_carabao_match(rng, team_a, team_b, extra_time):
    ea = get_carabao_elo(team_a)
    eb = get_carabao_elo(team_b)
    hg, ag = carabao_leg_score(rng, ea + HOME_ADVANTAGE_ELO, eb)
    if hg > ag:
        return team_a
    if ag > hg:
        return team_b
    if extra_time:
        if rng.float() < 0.20:
            return carabao_penalty_winner(rng, team_a, team_b)
        et_h, et_a = carabao_leg_score(rng, ea + HOME_ADVANTAGE_ELO, eb)
        if et_h != et_a:
            return team_a if et_h > et_a else team_b
    return carabao_penalty_winner(rng, team_a, team_b)


def sim_carabao_two_legged(rng, a, b):
    ea = get_carabao_elo(a)
    eb = get_carabao_elo(b)
    h1, a1 = carabao_leg_score(rng, ea + HOME_ADVANTAGE_ELO, eb)
    h2, a2 = carabao_leg_score(rng, eb + HOME_ADVANTAGE_ELO, ea)
    agg_a = h1 + a2
    agg_b = a1 + h2
    if agg_a > agg_b:
        return a
    if agg_b > agg_a:
        return b
    return carabao_penalty_winner(rng, a, b)


def run_carabao_tournament(rng):
    R4 = [
        ("Bradford City", "Peterborough United"),
        ("Fleetwood Town", "Arsenal"),
        ("Manchester City", "Brighton & Hove Albion"),
        ("Bournemouth", "Aston Villa"),
        ("Fulham", "Crystal Palace"),
        ("Sunderland", "Brentford"),
        ("Liverpool", "Chelsea"),
        ("Everton", "Newcastle United"),
    ]
    winners = [sim_carabao_match(rng, a, b, False) for a, b in R4]

    rng.shuffle(winners)
    qf = []
    for i in range(0, len(winners), 2):
        qf.append(sim_carabao_match(rng, winners[i], winners[i + 1], False))

    rng.shuffle(qf)
    sf = []
    for i in range(0, len(qf), 2):
        sf.append(sim_carabao_two_legged(rng, qf[i], qf[i + 1]))

    rng.shuffle(sf)
    return sim_carabao_match(rng, sf[0], sf[1], True)


# =============================================================================
# FA CUP (odds-based)
# =============================================================================
def fa_cup_data():
    global _fa_cup_data_cache
    if _fa_cup_data_cache is None:
        odds = [
            ("Arsenal", "9/2"), ("Man City", "5/1"), ("Liverpool", "13/2"), ("Man United", "7/1"),
            ("Chelsea", "8/1"), ("Aston Villa", "12/1"), ("Tottenham", "12/1"), ("Newcastle", "18/1"),
            ("Brighton", "22/1"), ("Brentford", "28/1"), ("Bournemouth", "28/1"), ("Everton", "28/1"),
            ("Fulham", "33/1"), ("Leeds", "33/1"), ("Crystal Palace", "33/1"), ("Nott'm Forest", "33/1"),
            ("Sunderland", "50/1"), ("Ipswich", "66/1"), ("Coventry", "66/1"), ("Hull", "80/1"),
            ("Burnley", "80/1"), ("Wolves", "80/1"), ("West Ham", "80/1"), ("Norwich", "150/1"),
            ("Sheffield United", "150/1"), ("Wrexham", "150/1"), ("Birmingham", "150/1"),
            ("Middlesbrough", "150/1"), ("Southampton", "150/1"), ("Derby", "200/1"),
            ("Bristol City", "200/1"), ("West Brom", "200/1"), ("Stoke", "200/1"), ("Millwall", "200/1"),
            ("Watford", "250/1"), ("Charlton", "250/1"), ("Blackburn", "250/1"), ("Preston", "250/1"),
            ("Lincoln", "250/1"), ("QPR", "250/1"), ("Swansea", "250/1"), ("Bolton", "250/1"),
            ("Portsmouth", "250/1"), ("Cardiff", "250/1"),
        ]
        names = []
        raw = []
        for name, s in odds:
            num_s, den_s = s.split('/')
            num, den = float(num_s), float(den_s)
            names.append(name)
            raw.append(den / (num + den))
        total = sum(raw)
        weights = [p / total for p in raw]
        _fa_cup_data_cache = (names, weights)
    return _fa_cup_data_cache


def sample_fa_cup_winner(rng):
    names, weights = fa_cup_data()
    r = rng.float()
    cum = 0.0
    for i, w in enumerate(weights):
        cum += w
        if r < cum:
            return names[i]
    return names[-1]


# =============================================================================
# HUNGARIAN ALGORITHM
# =============================================================================
def hungarian(cost):
    n = len(cost)
    if n == 0:
        return []
    a = [[0.0] * (n + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(n):
            a[i + 1][j + 1] = cost[i][j]
    u = [0.0] * (n + 1)
    v = [0.0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)
    INF = float('inf')

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = INF
            j1 = 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = a[i0][j] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(0, n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    result = [0] * n
    for j in range(1, n + 1):
        if p[j] > 0:
            result[p[j] - 1] = j - 1
    return result


# =============================================================================
# PROGRESS RENDERER
# =============================================================================
def render_progress(done, total, start):
    frac = done / max(total, 1)
    elapsed = time.time() - start
    eta = elapsed * (1.0 - frac) / frac if done > 0 else 0.0
    width = 30
    filled = min(round(frac * width), width)
    if filled >= width:
        bar = '[' + ('=' * width) + ']'
    else:
        bar = '[' + ('=' * filled) + '>' + (' ' * (width - filled - 1)) + ']'
    return f"{bar} {frac*100:.1f}%  ETA {eta:.0f}s"


def spot_pct_map(spots):
    n = len(spots) or 1
    counts = Counter(spots)
    return {k: v / n * 100.0 for k, v in counts.items()}


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("\n" + "=" * 80)
    print("UNIFIED PREMIER LEAGUE + EUROPEAN + CARABAO CUP SIMULATION (Python)")
    print("=" * 80)

    seed = (int(time.time()) ^ (time.time_ns() % 1_000_000_000)) & 0xFFFFFFFFFFFFFFFF
    rng = Rng(seed)

    pl_preset = preset_pl_elos()
    ucl_preset = preset_ucl_elos()
    uel_preset = preset_uel_elos()
    uecl_preset = preset_uecl_elos()
    assoc_map = association_map()
    entrants = assoc_entrants()

    actual_results = results_to_map(ACTUAL_RESULTS_ARR)
    cl_actual = results_to_map(CL_ACTUAL_RESULTS_ARR)
    uel_actual = results_to_map(UEL_ACTUAL_RESULTS_ARR)
    uecl_actual = results_to_map(UECL_ACTUAL_RESULTS_ARR)

    fixtures_list = build_full_round_robin(ACTUAL_RESULTS_ARR)
    pl_teams = {t for f in fixtures_list for t in f}

    preset_mean = sum(pl_preset.values()) / len(pl_preset)
    pl_elos_built = build_current_pl_ratings(actual_results, pl_teams, pl_preset, 50.0)
    TOTAL_GAMES_ALL_COMPS = PL_TOTAL_FIXTURES + 144 + 144 + 108
    games_played_all = len(actual_results) + len(cl_actual) + len(uel_actual) + len(uecl_actual)

    pl_elos = regress_elos(pl_elos_built, games_played_all, TOTAL_GAMES_ALL_COMPS,
                           preset_mean, PL_ELO_MAX_PULL)
    ucl_elos = regress_elos(ucl_preset, games_played_all, TOTAL_GAMES_ALL_COMPS,
                            LEAGUE_AVERAGE_ELO, PL_ELO_MAX_PULL)
    uel_elos = regress_elos(uel_preset, games_played_all, TOTAL_GAMES_ALL_COMPS,
                            LEAGUE_AVERAGE_ELO, PL_ELO_MAX_PULL)
    uecl_elos = regress_elos(uecl_preset, games_played_all, TOTAL_GAMES_ALL_COMPS,
                             LEAGUE_AVERAGE_ELO, PL_ELO_MAX_PULL)

    uel_fixtures_std = [[(standardise_uel(h), standardise_uel(a)) for (h, a) in r]
                        for r in UEL_FIXTURES_RAW]
    uecl_fixtures_std = [[(standardise_uecl(h), standardise_uecl(a)) for (h, a) in r]
                         for r in UECL_FIXTURES_RAW]

    ucl_comp = EuropeanCompetition("UCL", CL_FIXTURES_ARR, pl_elos, pl_teams, cl_actual, ucl_elos)
    uel_comp = EuropeanCompetition("UEL", uel_fixtures_std, pl_elos, pl_teams, uel_actual, uel_elos)
    uecl_comp = EuropeanCompetition("UECL", uecl_fixtures_std, pl_elos, pl_teams, uecl_actual, uecl_elos)
    pl_sim = PLSimulator(fixtures_list, pl_elos, actual_results)

    # Accumulators
    points_dist = {t: [] for t in pl_teams}
    position_counts = {t: defaultdict(int) for t in pl_teams}
    title_counts = defaultdict(int)
    ucl_qual_counts = defaultdict(int)
    uel_qual_counts = defaultdict(int)
    uecl_qual_counts = defaultdict(int)
    relegation_counts = defaultdict(int)
    euro_win_counts = {"UCL": defaultdict(int), "UEL": defaultdict(int), "UECL": defaultdict(int)}
    carabao_wins = defaultdict(int)
    fa_cup_wins = defaultdict(int)
    english_three_comp = 0

    eps_earned = 0
    fifth_place_ucl = 0
    england_coeff_accum = []
    assoc_coeff_accum = defaultdict(list)
    assoc_top2_count = defaultdict(int)

    manutd_streaks = []
    manutd_5plus = 0
    manutd_streak_max = 0

    euro_positions = {c: defaultdict(lambda: defaultdict(int)) for c in ("UCL", "UEL", "UECL")}
    euro_points = {c: defaultdict(list) for c in ("UCL", "UEL", "UECL")}

    pl_ucl_spots, pl_uel_spots, pl_uecl_spots, pl_total_spots = [], [], [], []
    pl_ucl_min, pl_ucl_max = 10 ** 9, 0
    pl_uel_min, pl_uel_max = 10 ** 9, 0
    pl_uecl_min, pl_uecl_max = 10 ** 9, 0
    pl_total_min, pl_total_max = 10 ** 9, 0

    start = time.time()
    last_update = 0

    for sim_i in range(NUM_PL_SIMS):
        step = max(NUM_PL_SIMS // 200, 1)
        if sim_i - last_update >= step:
            last_update = sim_i
            sys.stderr.write("\r" + render_progress(sim_i, NUM_PL_SIMS, start))
            sys.stderr.flush()

        ucl_res = ucl_comp.simulate(rng, track={"Man United"})
        uel_res = uel_comp.simulate(rng)
        uecl_res = uecl_comp.simulate(rng)

        for comp_name, res in (("UCL", ucl_res), ("UEL", uel_res), ("UECL", uecl_res)):
            pos_map = euro_positions[comp_name]
            pts_map = euro_points[comp_name]
            for pos, team in enumerate(res.ranking):
                pos_map[team][pos + 1] += 1
                pts_map[team].append(res.league_points[team])

        # Fatigue info
        fatigue_info = {}
        for team in pl_teams:
            if team in ucl_res.elim_rounds:
                fatigue_info[team] = (ucl_res.elim_rounds[team], "UCL")
            elif team in uel_res.elim_rounds:
                fatigue_info[team] = (uel_res.elim_rounds[team], "UEL")
            elif team in uecl_res.elim_rounds:
                fatigue_info[team] = (uecl_res.elim_rounds[team], "UECL")

        ranking, points, pl_team_results = pl_sim.simulate_season(
            fatigue_info, rng, track={"Man United"})

        carabao_winner = run_carabao_tournament(rng)
        fa_cup_winner = sample_fa_cup_winner(rng)

        # Man United streak
        if "Man United" in pl_teams:
            mr = list(pl_team_results.get("Man United", []))
            if "Man United" in ucl_res.team_results:
                mr.extend(ucl_res.team_results["Man United"])
            s = max_consecutive_wins(mr)
            manutd_streaks.append(s)
            if s >= 5:
                manutd_5plus += 1
            if s > manutd_streak_max:
                manutd_streak_max = s

        # Coefficients
        coeffs = all_association_coefficients(ucl_res, uel_res, uecl_res, assoc_map, entrants)
        ranked = sorted(coeffs.items(), key=lambda x: -x[1])
        top2 = {a for a, _ in ranked[:2]}
        has_eps = "England" in top2
        if has_eps:
            eps_earned += 1
        england_coeff_accum.append(coeffs.get("England", 0.0))
        for assoc, coeff in ranked[:8]:
            assoc_coeff_accum[assoc].append(coeff)
            if assoc in top2:
                assoc_top2_count[assoc] += 1

        # Spot allocation
        spots = allocate_european_spots(
            ranking, carabao_winner, pl_teams,
            ucl_res.winner, uel_res.winner, uecl_res.winner,
            has_eps, fa_cup_winner)

        if has_eps and len(ranking) > 4:
            fifth = ranking[4]
            if fifth in spots["UCL"]:
                fifth_place_ucl += 1

        ucl_n = len(spots["UCL"])
        uel_n = len(spots["UEL"])
        uecl_n = len(spots["UECL"])
        total_n = ucl_n + uel_n + uecl_n
        pl_ucl_spots.append(ucl_n)
        pl_uel_spots.append(uel_n)
        pl_uecl_spots.append(uecl_n)
        pl_total_spots.append(total_n)
        pl_ucl_min = min(pl_ucl_min, ucl_n); pl_ucl_max = max(pl_ucl_max, ucl_n)
        pl_uel_min = min(pl_uel_min, uel_n); pl_uel_max = max(pl_uel_max, uel_n)
        pl_uecl_min = min(pl_uecl_min, uecl_n); pl_uecl_max = max(pl_uecl_max, uecl_n)
        pl_total_min = min(pl_total_min, total_n); pl_total_max = max(pl_total_max, total_n)

        for t in spots["UCL"]:
            ucl_qual_counts[t] += 1
        for t in spots["UEL"]:
            uel_qual_counts[t] += 1
        for t in spots["UECL"]:
            uecl_qual_counts[t] += 1

        for pos, team in enumerate(ranking):
            points_dist[team].append(points[team])
            position_counts[team][pos + 1] += 1
            if pos == 0:
                title_counts[team] += 1
            if pos >= 17:
                relegation_counts[team] += 1

        for comp, w in (("UCL", ucl_res.winner), ("UEL", uel_res.winner), ("UECL", uecl_res.winner)):
            if w and w in pl_teams:
                euro_win_counts[comp][w] += 1
        if ucl_res.winner and uel_res.winner and uecl_res.winner:
            if (ucl_res.winner in pl_teams and uel_res.winner in pl_teams
                    and uecl_res.winner in pl_teams):
                english_three_comp += 1

        carabao_wins[carabao_winner] += 1
        fa_cup_wins[fa_cup_winner] += 1

    sys.stderr.write("\r" + render_progress(NUM_PL_SIMS, NUM_PL_SIMS, start) + "  \n")

    total = NUM_PL_SIMS
    print("\nElapsed {:.1f}s".format(time.time() - start))

    games_played = games_played_all
    played_frac = games_played / TOTAL_GAMES_ALL_COMPS
    pull = PL_ELO_MAX_PULL * (1.0 - played_frac)
    print("\nElo regression (all comps): {}/{} games -> pull toward mean = {:.3f}, preset retained = {:.3f}"
          .format(games_played, TOTAL_GAMES_ALL_COMPS, pull, 1.0 - pull))

    # Top-2 probabilities
    print("\n" + "=" * 80)
    print("EPS (EXTRA PERFORMANCE SPOT) — 2027/28 UCL")
    print("=" * 80)
    if england_coeff_accum:
        mean_eng = sum(england_coeff_accum) / len(england_coeff_accum)
        print("England avg coefficient: {:.3f}".format(mean_eng))
    print("P(England Top 2 -> EPS 5th PL team in UCL): {:.2f}%".format(eps_earned / total * 100.0))
    print("P(5th place actually takes UCL spot): {:.2f}%".format(fifth_place_ucl / total * 100.0))

    top2_sorted = sorted(assoc_top2_count.items(), key=lambda x: -x[1])
    print("\nTop-2 finish probability by association:")
    for assoc, count in top2_sorted:
        vals = assoc_coeff_accum.get(assoc, [])
        avg = sum(vals) / len(vals) if vals else 0.0
        print("  {:<20} {:>6.2f}%   (avg coeff {:.3f})".format(assoc, count / total * 100.0, avg))

    # Average spots
    print("\n" + "=" * 80)
    print("AVERAGE PREMIER LEAGUE EUROPEAN SPOTS")
    print("=" * 80)
    print("UCL:  {:.2f} (min {}, max {})".format(sum(pl_ucl_spots) / total, pl_ucl_min, pl_ucl_max))
    print("UEL:  {:.2f} (min {}, max {})".format(sum(pl_uel_spots) / total, pl_uel_min, pl_uel_max))
    print("UECL: {:.2f} (min {}, max {})".format(sum(pl_uecl_spots) / total, pl_uecl_min, pl_uecl_max))
    print("Total: {:.2f} (min {}, max {})".format(sum(pl_total_spots) / total, pl_total_min, pl_total_max))

    ucl_dist = spot_pct_map(pl_ucl_spots)
    uel_dist = spot_pct_map(pl_uel_spots)
    uecl_dist = spot_pct_map(pl_uecl_spots)
    total_dist = spot_pct_map(pl_total_spots)

    d_min = min(pl_ucl_min, pl_uel_min, pl_uecl_min, pl_total_min)
    d_max = max(pl_ucl_max, pl_uel_max, pl_uecl_max, pl_total_max)

    print("\n" + "-" * 64)
    print("SPOT COUNT DISTRIBUTION (% chance per simulation)")
    print("  Spots |     UCL |     UEL |    UECL |    Total")
    print("--------+---------+---------+---------+---------")

    def fmt(m, s):
        v = m.get(s)
        return "{:>7.2f}%".format(v) if v is not None and v > 0.0 else "{:>8}".format("-")

    for s in range(d_min, d_max + 1):
        print("{:>6} |{}|{}|{}|{}".format(s, fmt(ucl_dist, s), fmt(uel_dist, s),
                                          fmt(uecl_dist, s), fmt(total_dist, s)))

    # Final PL table
    print("\n" + "=" * 135)
    print("FINAL PREMIER LEAGUE PROJECTIONS")
    print("=" * 135)
    print("{:<4}{:<22}{:<8}{:<8}{:<9}{:<9}{:<9}{:<10}{:<8}".format(
        "Rk", "Team", "Pts", "Title%", "UCLAny%", "UELAny%", "UECLAny%", "EuroAny%", "Releg%"))
    print("-" * 135)

    avg_pts_map = {t: sum(points_dist[t]) / len(points_dist[t]) if points_dist[t] else 0.0
                   for t in pl_teams}
    teams_sorted = sorted(pl_teams, key=avg_pts_map.__getitem__, reverse=True)

    for rank, t in enumerate(teams_sorted):
        title_pct = title_counts.get(t, 0) / total * 100.0
        ucl_pct = ucl_qual_counts.get(t, 0) / total * 100.0
        uel_pct = uel_qual_counts.get(t, 0) / total * 100.0
        uecl_pct = uecl_qual_counts.get(t, 0) / total * 100.0
        euro_pct = ucl_pct + uel_pct + uecl_pct
        rel_pct = relegation_counts.get(t, 0) / total * 100.0
        print("{:<4}{:<22}{:<8.2f}{:<8.2f}{:<9.2f}{:<9.2f}{:<9.2f}{:<10.2f}{:<8.2f}".format(
            rank + 1, t, avg_pts_map[t], title_pct, ucl_pct, uel_pct, uecl_pct, euro_pct, rel_pct))

    # Most-likely final table via assignment
    n_teams = len(teams_sorted)
    prob = [[0.0] * n_teams for _ in range(n_teams)]
    for i, t in enumerate(teams_sorted):
        counts = position_counts[t]
        for pos in range(1, n_teams + 1):
            prob[i][pos - 1] = counts.get(pos, 0) / total
    cost = [[1.0 - p for p in row] for row in prob]
    assignment = hungarian(cost)

    assigned = []
    solved_sum = 0.0
    for i in range(n_teams):
        j = assignment[i]
        p = prob[i][j]
        solved_sum += p
        assigned.append((j + 1, i, p * 100.0))
    assigned.sort(key=lambda x: x[0])
    avg_solved = solved_sum / n_teams * 100.0

    print("\n" + "=" * 80)
    print("MOST LIKELY FINAL TABLE (optimal assignment — unique rank per team)")
    print("=" * 80)
    print("{:<4}{:<22}{:<12}{:<12}".format("Rk", "Team", "Pos Prob%", "Cumulative"))
    print("-" * 50)
    cum = 0.0
    for pos, team_idx, prob_pct in assigned:
        cum += prob_pct
        print("{:<4}{:<22}{:<12.2f}{:<12.2f}".format(pos, teams_sorted[team_idx], prob_pct, cum))
    print("\nLeague 'solved' percentage (avg assigned position prob): {:.2f}%".format(avg_solved))

    # Euro win probabilities
    print("\n" + "=" * 80)
    print("CHANCE A PREMIER LEAGUE TEAM WINS EACH EUROPEAN COMPETITION")
    print("=" * 80)
    for comp in ("UCL", "UEL", "UECL"):
        total_wins = sum(euro_win_counts[comp].values())
        pct = total_wins / total * 100.0
        label = {"UCL": "UCL  (Champions League)",
                 "UEL": "UEL  (Europa League)",
                 "UECL": "UECL (Conference League)"}[comp]
        print("  {}: {:.2f}%".format(label, pct))
    print("  English teams win all 3: {:.2f}%".format(english_three_comp / total * 100.0))

    # Euro league tables
    for comp_name in ("UCL", "UEL", "UECL"):
        print("\n" + "=" * 80)
        print("{} PREDICTED TABLE (league phase)".format(comp_name))
        print("=" * 80)
        print("{:<24}{:<8}{:<8}{:<10}{:<10}".format("Team", "Pts", "Top8%", "Pos9-24%", "Pos25+%"))
        print("-" * 60)

        pos_map = euro_positions[comp_name]
        pts_map = euro_points[comp_name]

        def team_avg_pts(t):
            v = pts_map.get(t, [])
            return sum(v) / len(v) if v else 0.0

        teams = sorted(pos_map.keys(), key=lambda t: -team_avg_pts(t))
        for team in teams:
            counts = pos_map[team]
            top8 = sum(counts.get(p, 0) for p in range(1, 9))
            mid = sum(counts.get(p, 0) for p in range(9, 25))
            low = sum(counts.get(p, 0) for p in range(25, 41))
            print("{:<24}{:<8.2f}{:<8.2f}{:<10.2f}{:<10.2f}".format(
                team, team_avg_pts(team),
                top8 / total * 100.0, mid / total * 100.0, low / total * 100.0))

    # Carabao Cup
    print("\n" + "=" * 80)
    print("CARABAO CUP WIN PROBABILITY")
    print("=" * 80)
    r4_teams = {
        "Bradford City", "Peterborough United", "Fleetwood Town", "Arsenal",
        "Manchester City", "Brighton & Hove Albion", "Bournemouth", "Aston Villa",
        "Fulham", "Crystal Palace", "Sunderland", "Brentford",
        "Liverpool", "Chelsea", "Everton", "Newcastle United",
    }
    carabao_sorted = sorted(r4_teams, key=lambda t: -carabao_wins.get(t, 0))
    for team in carabao_sorted:
        count = carabao_wins.get(team, 0)
        print("  {:<22} {:>6.2f}%".format(team, count / total * 100.0))

    # FA Cup
    print("\n" + "=" * 80)
    print("FA CUP WIN PROBABILITY (from outright odds)")
    print("=" * 80)
    fa_names, fa_weights = fa_cup_data()
    fa_idx = sorted(range(len(fa_names)), key=lambda i: -fa_weights[i])
    for i in fa_idx:
        team = fa_names[i]
        implied = fa_weights[i] * 100.0
        sim_pct = fa_cup_wins.get(team, 0) / total * 100.0
        print("  {:<22} {:>6.2f}%  (sim: {:.2f}%)".format(team, implied, sim_pct))

    pl_fa_total = sum(v for t, v in fa_cup_wins.items() if t in pl_teams)
    print("\n  P(a PL team wins the FA Cup): {:.2f}%".format(pl_fa_total / total * 100.0))

    # Man United streak summary
    if manutd_streaks:
        avg = sum(manutd_streaks) / len(manutd_streaks)
        print("\n" + "=" * 80)
        print("MAN UNITED 5-GAME WINNING STREAK (PL + UCL)")
        print("=" * 80)
        print("  Average longest W streak:   {:.2f}".format(avg))
        print("  P(≥5 consecutive wins):     {:.2f}%".format(manutd_5plus / total * 100.0))
        print("  Max streak across all sims: {}".format(manutd_streak_max))


if __name__ == "__main__":
    main()