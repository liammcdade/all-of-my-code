import pandas as pd
import math
from collections import defaultdict
from tqdm import tqdm
import json
import os

# =========================
# GLICKO-2 CONSTANTS
# =========================
TAU = 0.5
SCALE = 173.7178
INIT_RATING = 1500
INIT_RD = 300
INIT_SIGMA = 0.06
RATING_PERIOD_DAYS = 30  # Increase uncertainty every 30 days of inactivity

# =========================
# GLICKO-2 FUNCTIONS
# =========================
def g(phi):
    return 1 / math.sqrt(1 + 3 * phi**2 / math.pi**2)

def E(mu, mu_j, phi_j):
    return 1 / (1 + math.exp(-g(phi_j) * (mu - mu_j)))

def r_to_mu(r):
    return (r - 1500) / SCALE

def rd_to_phi(rd):
    return rd / SCALE

def mu_to_r(mu):
    return mu * SCALE + 1500

def phi_to_rd(phi):
    return phi * SCALE

def goal_weight(gd):
    return math.log(gd + 1) + 1

# =========================
# PLAYER UPDATE
# =========================
def update(player, opp, result, gd):
    mu = r_to_mu(player["r"])
    phi = rd_to_phi(player["rd"])
    sigma = player["sigma"]

    mu_j = r_to_mu(opp["r"])
    phi_j = rd_to_phi(opp["rd"])

    w = goal_weight(gd)
    E_ = E(mu, mu_j, phi_j)
    g_ = g(phi_j)

    v = 1 / (w * g_**2 * E_ * (1 - E_))
    delta = v * w * g_ * (result - E_)

    # ---------- VOLATILITY UPDATE (SAFE) ----------
    a = math.log(sigma**2)
    tau = TAU
    eps = 1e-6

    def f(x):
        ex = math.exp(x)
        return (
            ex * (delta**2 - phi**2 - v - ex)
            / (2 * (phi**2 + v + ex)**2)
            - (x - a) / (tau**2)
        )

    A = a
    if delta**2 > phi**2 + v:
        B = math.log(delta**2 - phi**2 - v)
    else:
        B = a - tau

    fA = f(A)
    fB = f(B)

    # HARD ITERATION CAP (prevents freezing)
    for _ in range(50):
        C = A + (A - B) * fA / (fB - fA)
        fC = f(C)

        if abs(C - A) < eps:
            break

        if fC * fB < 0:
            A, fA = B, fB
        else:
            fA /= 2

        B, fB = C, fC

    sigma_p = math.exp(A / 2)

    # ---------- RATING UPDATE ----------
    phi_star = math.sqrt(phi**2 + sigma_p**2)
    phi_p = 1 / math.sqrt(1 / phi_star**2 + 1 / v)
    mu_p = mu + phi_p**2 * w * g_ * (result - E_)

    return {
        "r": mu_to_r(mu_p),
        "rd": phi_to_rd(phi_p),
        "sigma": sigma_p
    }

def apply_inactivity(player, current_date, rating_period_days):
    if player["last_match_date"] is None:
        player["last_match_date"] = current_date
        return

    days_passed = (current_date - player["last_match_date"]).days
    periods = days_passed // rating_period_days

    if periods > 0:
        phi = rd_to_phi(player["rd"])
        sigma = player["sigma"]
        # Apply phi' = sqrt(phi^2 + sigma^2) for each period
        for _ in range(periods):
            phi = math.sqrt(phi**2 + sigma**2)
        
        player["rd"] = phi_to_rd(phi)
        # RD should not exceed INIT_RD
        if player["rd"] > INIT_RD:
            player["rd"] = INIT_RD
            
        player["last_match_date"] += pd.Timedelta(days=periods * rating_period_days)

# =========================
# LOAD DATA
# =========================
df = pd.read_csv(r"C:\Users\liam\Documents\GitHub\All-code-in-one\sportsanalysis\worldcup26\Glicko2ratingversion\results.csv")
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

# =========================
# APPLY FORMER NAMES MAPPING
# =========================
former_names_path = r"C:\Users\liam\Documents\GitHub\All-code-in-one\sportsanalysis\worldcup26\former_names.csv"
if os.path.exists(former_names_path):
    fn_df = pd.read_csv(former_names_path)
    fn_df["start_date"] = pd.to_datetime(fn_df["start_date"])
    fn_df["end_date"] = pd.to_datetime(fn_df["end_date"])
    
    for _, mapping in fn_df.iterrows():
        # Map home teams
        mask_h = (df["home_team"] == mapping["former"]) & \
                 (df["date"] >= mapping["start_date"]) & \
                 (df["date"] <= mapping["end_date"])
        df.loc[mask_h, "home_team"] = mapping["current"]
        
        # Map away teams
        mask_a = (df["away_team"] == mapping["former"]) & \
                 (df["date"] >= mapping["start_date"]) & \
                 (df["date"] <= mapping["end_date"])
        df.loc[mask_a, "away_team"] = mapping["current"]

    print(f"Applied mappings from {former_names_path}")

# =========================
# INITIALISE TEAMS
# =========================
teams = defaultdict(lambda: {
    "r": INIT_RATING,
    "rd": INIT_RD,
    "sigma": INIT_SIGMA,
    "last_match_date": None
})

# PROCESS MATCHES
# =========================
for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing matches"):
    home = row["home_team"]
    away = row["away_team"]
    hs = row["home_score"]
    as_ = row["away_score"]

    gd = abs(hs - as_)

    if hs > as_:
        res_h, res_a = 1, 0
    elif hs < as_:
        res_h, res_a = 0, 1
    else:
        res_h = res_a = 0.5

    h_old = teams[home].copy()
    a_old = teams[away].copy()

    # Apply inactivity decay before the match
    apply_inactivity(teams[home], row["date"], RATING_PERIOD_DAYS)
    apply_inactivity(teams[away], row["date"], RATING_PERIOD_DAYS)

    teams[home].update(update(teams[home], teams[away], res_h, gd))
    teams[away].update(update(teams[away], teams[home], res_a, gd))
    
    # Update last match date after the match update
    teams[home]["last_match_date"] = row["date"]
    teams[away]["last_match_date"] = row["date"]

# Apply final inactivity update to the latest date in the dataset
last_date = df["date"].max()
for team_name in teams:
    apply_inactivity(teams[team_name], last_date, RATING_PERIOD_DAYS)

# =========================
# OUTPUT FINAL RATINGS
# =========================
ratings = (
    pd.DataFrame([
        [team, v["r"], v["rd"], v["sigma"]]
        for team, v in teams.items()
    ],
    columns=["team", "glicko_rating", "rd", "sigma"])
    .sort_values("glicko_rating", ascending=False)
)

print(ratings.head(20))

# =========================
# EXPORT RATINGS
# =========================
glicko_dict = dict(zip(ratings["team"], ratings["glicko_rating"]))
output_path = os.path.join(os.path.dirname(__file__), "glicko_ratings.json")
with open(output_path, "w") as f:
    json.dump(glicko_dict, f, indent=4)

print(f"\nRatings exported to {output_path}")
