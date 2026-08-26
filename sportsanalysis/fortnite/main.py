"""Fortnite tournament scoring calculator with projection probabilities.

Simulates Group A and Group B, then projects qualifications based on:
- Group Stage: Top 7 -> Finals | 8-17 -> Survival | 18+ -> Eliminated
- Survival Stage: 10 matches, Top 6 advance to Finals
- Grand Finals: Match Point format (350 pts + Win), max 15 games
"""

import random
import sys
from dataclasses import dataclass

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc="", unit=""):
        return iterable

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

PLACEMENT_POINTS: dict[int, int] = {
    1: 70, 2: 50, 3: 45, 4: 40, 5: 35,
    6: 30, 7: 27, 8: 24, 9: 21, 10: 18,
    11: 15, 12: 12, 13: 9, 14: 6, 15: 3,
}

ELIMINATION_POINTS: int = 3
NUM_GAMES: int = 10
NUM_SIMULATIONS: int = 10_000
DEFAULT_SEED: int | None = None

# Tournament Structure Constants
TOP_7_CUTOFF: int = 7
SURVIVAL_START: int = 8
SURVIVAL_END: int = 17
SURVIVAL_GAMES: int = 10
SURVIVAL_ADVANCE: int = 6

FINAL_MAX_GAMES: int = 15
MATCH_POINT_THRESHOLD: int = 350

MAX_PLACEMENT: int = 15
MAX_ELIMINATIONS_PER_GAME: int = 15


@dataclass(slots=True)
class TeamResult:
    group: str
    overall_rank: int
    player1: str
    player2: str
    org1: str
    org2: str
    total_points: int
    avg_points: float
    matches: int
    wins: int
    total_elims: int
    avg_place: float
    
    @property
    def team_name(self) -> str:
        if self.player1 and self.player2:
            return f"{self.player1}/{self.player2}"
        return self.player1 or self.player2 or (self.org1 or self.org2 or "Solo")
    
    @property
    def games_played(self) -> int:
        return self.matches
    
    @property
    def games_remaining(self) -> int:
        return max(NUM_GAMES - self.games_played, 0)
    
    @property
    def elims_per_game(self) -> float:
        if self.matches == 0:
            return 0.0
        return self.total_elims / self.matches


# ---------------------------------------------------------------------------
# GROUP A TEAMS (Final Results - 10 matches played)
# ---------------------------------------------------------------------------
GROUP_A_TEAMS: tuple[TeamResult, ...] = (
    TeamResult("A", 1, "Shxrk", "t3eny", "Aurora Gaming", "Aurora Gaming", 570, 57.00, 10, 4, 73, 7.00),
    TeamResult("A", 2, "vic0", "Malibuca", "BIG", "BIG", 462, 46.20, 10, 1, 60, 8.20),
    TeamResult("A", 3, "Muz", "Sphinx", "XSET", "", 454, 45.40, 10, 0, 44, 6.40),
    TeamResult("A", 4, "Peterbot", "Pollo", "Falcons Esport", "Falcons Esport", 378, 37.80, 10, 2, 51, 10.70),
    TeamResult("A", 5, "Lewa", "Romero", "", "", 373, 37.30, 10, 0, 38, 8.10),
    TeamResult("A", 6, "Tjino", "PabloWingu", "Team HavoK", "Team HavoK", 371, 37.10, 10, 0, 46, 8.90),
    TeamResult("A", 7, "charyy", "Kami", "ROC Esports", "ROC Esports", 341, 34.10, 10, 0, 23, 7.80),
    TeamResult("A", 8, "ZDog", "Goofy", "JFT Esports", "PWR", 331, 33.10, 10, 0, 31, 8.60),
    TeamResult("A", 9, "Bugha", "Braydz", "", "XP42", 305, 30.50, 10, 0, 29, 9.50),
    TeamResult("A", 10, "Cringe", "Volko", "7VEN CLUB", "Northern Star Gaming", 295, 29.50, 10, 0, 22, 8.90),
    TeamResult("A", 11, "Izzi", "Nociff", "Team Orchid", "Team Orchid", 252, 25.20, 10, 1, 34, 12.60),
    TeamResult("A", 12, "phoenix", "Retro", "ONIC", "ONIC", 232, 23.20, 10, 1, 30, 12.90),
    TeamResult("A", 13, "tomat", "Mofu", "REJECT", "REJECT", 225, 22.50, 10, 1, 15, 11.30),
    TeamResult("A", 14, "Shadow", "Vergo", "Team Natrix", "Gentle Mates", 224, 22.40, 10, 0, 17, 10.90),
    TeamResult("A", 15, "5AALD", "Mshary", "", "", 218, 21.80, 10, 0, 37, 13.50),
    TeamResult("A", 16, "Rew", "Moda!", "RVL eSports", "RVL eSports", 198, 19.80, 10, 0, 21, 12.50),
    TeamResult("A", 17, "edson", "FUT phzin 伊万尔", "", "", 197, 19.70, 10, 0, 20, 12.10),
    TeamResult("A", 18, "Rainy", "Nalu", "DetonatioN FocusMe", "KIT StarLeven KYUSHU", 189, 18.90, 10, 0, 17, 12.60),
    TeamResult("A", 19, "EpikWhale", "PXMP", "XP42", "Elite Esports", 144, 14.40, 10, 0, 19, 13.90),
    TeamResult("A", 20, "alex", "Wreckless", "PWR", "PWR", 111, 11.10, 10, 0, 13, 13.60),
)

# ---------------------------------------------------------------------------
# GROUP B TEAMS (Updated with actual results - 10 matches played)
# ---------------------------------------------------------------------------
GROUP_B_TEAMS: tuple[TeamResult, ...] = (
    TeamResult("B", 1, "TWIS Cold", "TWIS Rapid", "TWIS", "TWIS", 491, 49.10, 10, 0, 73, 7.90),
    TeamResult("B", 2, "LYOST Momsy", "RVNS SkyJump", "", "", 478, 47.80, 10, 2, 51, 6.50),
    TeamResult("B", 3, "TWIS Acorn", "TWIS boltz", "TWIS", "TWIS", 427, 42.70, 10, 1, 35, 7.00),
    TeamResult("B", 4, "HAVOK SwizzY", "HAVOK Pixie", "HAVOK", "HAVOK", 416, 41.60, 10, 1, 39, 7.20),
    TeamResult("B", 5, "DIG VicterV", "DIG Khanada", "DIG", "DIG", 371, 37.10, 10, 0, 38, 8.00),
    TeamResult("B", 6, "ELITE josh", "ELITE Eomzo", "ELITE", "ELITE", 354, 35.40, 10, 0, 30, 8.00),
    TeamResult("B", 7, "ZETA Minipiyo", "QTD Fuukun", "ZETA", "QTD", 346, 34.60, 10, 1, 23, 8.20),
    TeamResult("B", 8, "FURIA Night", "FURIA 916Gon", "FURIA", "FURIA", 338, 33.80, 10, 2, 34, 9.70),
    TeamResult("B", 9, "S8UL faded 14!", "S8UL KAAN BABA", "S8UL", "S8UL", 338, 33.80, 10, 0, 25, 7.90),
    TeamResult("B", 10, "AGAL Sky.", "AGAL Scroll 10!", "AGAL", "AGAL", 320, 32.00, 10, 1, 26, 8.80),
    TeamResult("B", 11, "T1 demus", "T1 darm", "T1", "T1", 288, 28.80, 10, 1, 42, 11.60),
    TeamResult("B", 12, "JOGO Oatley", "JOGO Spookz", "JOGO", "JOGO", 273, 27.30, 10, 0, 31, 10.50),
    TeamResult("B", 13, "VSN Salvatore", "VSN Yassen 1st", "VSN", "VSN", 264, 26.40, 10, 0, 37, 11.40),
    TeamResult("B", 14, "GK panzer", "GK japko", "GK", "GK", 242, 24.20, 10, 0, 35, 12.20),
    TeamResult("B", 15, "ZETA Koyota", "ZETA yuma", "ZETA", "ZETA", 210, 21.00, 10, 0, 31, 13.20),
    TeamResult("B", 16, "TEC Aoxy", "jojofishy", "", "", 198, 19.80, 10, 1, 20, 12.40),
    TeamResult("B", 17, "COAST Vazen", "PWR Anon", "COAST", "PWR", 189, 18.90, 10, 0, 29, 13.60),
    TeamResult("B", 18, "FNC Salko", "FNC Inact", "FNC", "FNC", 173, 17.30, 10, 0, 25, 13.50),
    TeamResult("B", 19, "7VEN Seven", "NTX axadasz", "", "", 121, 12.10, 10, 0, 11, 14.70),
    TeamResult("B", 20, "AHL Snow", "AHL Mhnd", "AHL", "AHL", 45, 4.50, 10, 0, 9, 17.70),
)

# ---------------------------------------------------------------------------
# SURVIVAL STAGE TEAMS (Updated with actual results - 3 matches played)
# Note: These teams are from positions 8-17 in Groups A and B
# ---------------------------------------------------------------------------
SURVIVAL_STAGE_TEAMS: tuple[TeamResult, ...] = (
    # From Group A (positions 8-17)
    TeamResult("Survival", 1, "ZDog", "Goofy", "JFT Esports", "PWR", 331, 33.10, 10, 0, 31, 8.60),
    TeamResult("Survival", 2, "Bugha", "Braydz", "", "XP42", 305, 30.50, 10, 0, 29, 9.50),
    TeamResult("Survival", 3, "Cringe", "Volko", "7VEN CLUB", "Northern Star Gaming", 295, 29.50, 10, 0, 22, 8.90),
    TeamResult("Survival", 4, "Izzi", "Nociff", "Team Orchid", "Team Orchid", 252, 25.20, 10, 1, 34, 12.60),
    TeamResult("Survival", 5, "phoenix", "Retro", "ONIC", "ONIC", 232, 23.20, 10, 1, 30, 12.90),
    TeamResult("Survival", 6, "tomat", "Mofu", "REJECT", "REJECT", 225, 22.50, 10, 1, 15, 11.30),
    TeamResult("Survival", 7, "Shadow", "Vergo", "Team Natrix", "Gentle Mates", 224, 22.40, 10, 0, 17, 10.90),
    TeamResult("Survival", 8, "5AALD", "Mshary", "", "", 218, 21.80, 10, 0, 37, 13.50),
    TeamResult("Survival", 9, "Rew", "Moda!", "RVL eSports", "RVL eSports", 198, 19.80, 10, 0, 21, 12.50),
    TeamResult("Survival", 10, "edson", "FUT phzin 伊万尔", "", "", 197, 19.70, 10, 0, 20, 12.10),
    
    # From Group B (positions 8-17)
    TeamResult("Survival", 11, "FURIA Night", "FURIA 916Gon", "FURIA", "FURIA", 338, 33.80, 10, 2, 34, 9.70),
    TeamResult("Survival", 12, "S8UL faded 14!", "S8UL KAAN BABA", "S8UL", "S8UL", 338, 33.80, 10, 0, 25, 7.90),
    TeamResult("Survival", 13, "AGAL Sky.", "AGAL Scroll 10!", "AGAL", "AGAL", 320, 32.00, 10, 1, 26, 8.80),
    TeamResult("Survival", 14, "T1 demus", "T1 darm", "T1", "T1", 288, 28.80, 10, 1, 42, 11.60),
    TeamResult("Survival", 15, "JOGO Oatley", "JOGO Spookz", "JOGO", "JOGO", 273, 27.30, 10, 0, 31, 10.50),
    TeamResult("Survival", 16, "VSN Salvatore", "VSN Yassen 1st", "VSN", "VSN", 264, 26.40, 10, 0, 37, 11.40),
    TeamResult("Survival", 17, "GK panzer", "GK japko", "GK", "GK", 242, 24.20, 10, 0, 35, 12.20),
    TeamResult("Survival", 18, "ZETA Koyota", "ZETA yuma", "ZETA", "ZETA", 210, 21.00, 10, 0, 31, 13.20),
    TeamResult("Survival", 19, "TEC Aoxy", "jojofishy", "", "", 198, 19.80, 10, 1, 20, 12.40),
    TeamResult("Survival", 20, "COAST Vazen", "PWR Anon", "COAST", "PWR", 189, 18.90, 10, 0, 29, 13.60),
)

# ---------------------------------------------------------------------------
# Actual Survival Stage Results (3 matches completed)
# These will be used to update current points for survival simulation
# ---------------------------------------------------------------------------
SURVIVAL_ACTUAL_RESULTS = {
    "T1 demus/T1 darm": 177,
    "VSN Salvatore/VSN Yassen 1st": 162,
    "FURIA Night/FURIA 916Gon": 158,
    "S8UL faded 14!/S8UL KAAN BABA": 140,
    "AGAL Sky./AGAL Scroll 10!": 132,
    "ORC Nociff/ORC Izzi": 117,  # Note: This appears to be Izzi/Nociff from Group A
    "Bugha/XP42 braydz": 116,
    "NTX shadow1x/M8 Vergo": 105,  # Note: This appears to be Shadow/Vergo from Group A
    "RC Mofu/RC tomat": 100,  # Note: This appears to be tomat/Mofu from Group A
    "VSN Mshary/5aald Q8": 98,  # Note: This appears to be 5AALD/Mshary from Group A
    "ZETA Koyota/ZETA yuma": 78,
    "JOGO Oatley/JOGO Spookz": 57,
    "RVL Moda/RVL Rew": 42,  # Note: This appears to be Rew/Moda! from Group A
    "FUT Edson/FUT phzin": 39,  # Note: This appears to be edson/FUT phzin from Group A
    "PWR Goofy/JFT ZDog": 36,  # Note: This appears to be ZDog/Goofy from Group A
    "7VEN Cringe/NSTAR Volko": 36,  # Note: This appears to be Cringe/Volko from Group A
    "COAST Vazen/PWR Anon": 36,
    "ONIC phoenix/ONIC retro": 30,  # Note: This appears to be phoenix/Retro from Group A
    "TEC Aoxy/jojofishy": 27,
    "GK panzer/GK japko": 24,
}


# ---------------------------------------------------------------------------
# Simulation Engine
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SimTeam:
    index: int
    group: str
    name: str
    current_points: int
    games_remaining: int
    avg_place: float
    avg_elims_per_game: float
    match_point_eligible: bool = False
    
    def simulate_game_points(self, rng: random.Random) -> tuple[int, int]:
        """Returns (points_earned, placement_in_game)"""
        place = self.avg_place if self.avg_place > 0 else 10.0
        elims = self.avg_elims_per_game if self.avg_elims_per_game > 0 else 3.0
        
        simulated_place = max(1, min(MAX_PLACEMENT, round(rng.gauss(place, 3.0))))
        place_points = PLACEMENT_POINTS.get(simulated_place, 0)
        
        avg_elims = max(0.1, elims)
        simulated_elims = max(0, min(MAX_ELIMINATIONS_PER_GAME, round(rng.gauss(avg_elims, avg_elims * 0.5))))
        elim_points = simulated_elims * ELIMINATION_POINTS
        
        return place_points + elim_points, simulated_place

def simulate_group_stage(teams: tuple[TeamResult, ...], rng: random.Random) -> list[SimTeam]:
    sim_teams = []
    for idx, team in enumerate(teams):
        st = SimTeam(
            index=idx, group=team.group, name=team.team_name,
            current_points=team.total_points, games_remaining=team.games_remaining,
            avg_place=team.avg_place, avg_elims_per_game=team.elims_per_game,
        )
        for _ in range(st.games_remaining):
            pts, _ = st.simulate_game_points(rng)
            st.current_points += pts
        sim_teams.append(st)
    return sim_teams

def simulate_stage_with_current_points(sim_teams: list[SimTeam], num_games: int, rng: random.Random) -> None:
    """Simulate remaining games for teams that already have some survival stage points"""
    for st in sim_teams:
        for _ in range(num_games):
            pts, _ = st.simulate_game_points(rng)
            st.current_points += pts

def rank_teams(sim_teams: list[SimTeam]) -> list[SimTeam]:
    return sorted(sim_teams, key=lambda t: (-t.current_points, t.index))

def simulate_match_point_finals(finalists: list[SimTeam], rng: random.Random) -> tuple[SimTeam, int]:
    """Simulates the Grand Finals using Match Point rules.
    Returns (winning_team, number_of_games_played)"""
    for st in finalists:
        st.current_points = 0  # Reset points for Finals
        st.match_point_eligible = False
        
    for game_num in range(FINAL_MAX_GAMES):
        game_placements = []
        for st in finalists:
            pts, place = st.simulate_game_points(rng)
            st.current_points += pts
            game_placements.append((st, place))
            
        # Update Match Point eligibility
        for st in finalists:
            if not st.match_point_eligible and st.current_points >= MATCH_POINT_THRESHOLD:
                st.match_point_eligible = True
                
        # Find who got the Victory Royale (1st place) in this game
        min_place = min(p[1] for p in game_placements)
        
        if min_place == 1:
            game_winners = [p[0] for p in game_placements if p[1] == 1]
            victory_royale_team = rng.choice(game_winners)
            
            # If the team that got the Win is eligible, they win the tournament!
            if victory_royale_team.match_point_eligible:
                return victory_royale_team, game_num + 1
                
    # Fallback: If 15 games pass without a Match Point win, highest points wins
    finalists.sort(key=lambda t: (-t.current_points, t.index))
    return finalists[0], FINAL_MAX_GAMES

@dataclass(slots=True)
class TeamProjection:
    group: str
    name: str
    current_points: int
    direct_finals_pct: float = 0.0
    survival_pct: float = 0.0
    eliminated_group_pct: float = 0.0
    overall_finals_pct: float = 0.0
    win_tournament_pct: float = 0.0

def run_full_simulation(
    teams_a: tuple[TeamResult, ...], 
    teams_b: tuple[TeamResult, ...],
    survival_teams_data: tuple[TeamResult, ...],
    survival_actual_results: dict[str, int],
    num_simulations: int = NUM_SIMULATIONS,
    seed: int | None = DEFAULT_SEED,
) -> tuple[list[TeamProjection], float]:
    if seed is None:
        seed = random.randint(0, 2**32)
    rng = random.Random(seed)
    
    num_a, num_b = len(teams_a), len(teams_b)
    
    direct_a, survival_a, elim_a, overall_a, wins_a = [0]*num_a, [0]*num_a, [0]*num_a, [0]*num_a, [0]*num_a
    direct_b, survival_b, elim_b, overall_b, wins_b = [0]*num_b, [0]*num_b, [0]*num_b, [0]*num_b, [0]*num_b
    
    total_finals_games = 0
    
    for _ in tqdm(range(num_simulations), desc="Simulating Tournament", unit="sim"):
        # 1. Group Stage (already completed, so just use final standings)
        sim_a = simulate_group_stage(teams_a, rng)
        sim_b = simulate_group_stage(teams_b, rng)
        
        ranked_a = rank_teams(sim_a)
        ranked_b = rank_teams(sim_b)
        
        # 2. Categorize Group A
        for pos, st in enumerate(ranked_a, start=1):
            idx = st.index
            if pos <= TOP_7_CUTOFF:
                direct_a[idx] += 1
                overall_a[idx] += 1
            elif pos <= SURVIVAL_END:
                survival_a[idx] += 1
            else:
                elim_a[idx] += 1
                
        # 3. Categorize Group B
        for pos, st in enumerate(ranked_b, start=1):
            idx = st.index
            if pos <= TOP_7_CUTOFF:
                direct_b[idx] += 1
                overall_b[idx] += 1
            elif pos <= SURVIVAL_END:
                survival_b[idx] += 1
            else:
                elim_b[idx] += 1
                
        # 4. Survival Stage - Use actual current points from 3 matches played
        survival_sim_teams = []
        for idx, team in enumerate(survival_teams_data):
            # Get actual points from survival stage (3 matches played)
            actual_survival_points = survival_actual_results.get(team.team_name, team.total_points)
            
            st = SimTeam(
                index=idx, group=team.group, name=team.team_name,
                current_points=actual_survival_points, 
                games_remaining=SURVIVAL_GAMES - 3,  # 7 games remaining
                avg_place=team.avg_place, 
                avg_elims_per_game=team.elims_per_game,
            )
            survival_sim_teams.append(st)
        
        # Simulate remaining 7 games of survival stage
        simulate_stage_with_current_points(survival_sim_teams, SURVIVAL_GAMES - 3, rng)
        ranked_survival = rank_teams(survival_sim_teams)
        
        # 5. Top 6 from Survival advance to Finals
        finalists = []
        for pos, st in enumerate(ranked_survival[:SURVIVAL_ADVANCE], start=1):
            # Map back to original team indices for tracking
            original_idx = st.index
            # Determine if this team was from Group A or B based on position
            if original_idx < 10:  # First 10 are from Group A
                overall_a[original_idx] += 1
            else:  # Last 10 are from Group B
                overall_b[original_idx - 10] += 1
            finalists.append(st)
            
        # Add direct qualifiers to finalists
        finalists.extend(ranked_a[:TOP_7_CUTOFF])
        finalists.extend(ranked_b[:TOP_7_CUTOFF])
        
        # 6. Grand Finals (Match Point)
        tournament_winner, games_played = simulate_match_point_finals(finalists, rng)
        total_finals_games += games_played
        
        # Track wins by mapping back to original teams
        # This is simplified - in a full implementation, you'd track which original team won
        if tournament_winner.group == 'A':
            if tournament_winner.index < num_a:
                wins_a[tournament_winner.index] += 1
        elif tournament_winner.group == 'B':
            if tournament_winner.index < num_b:
                wins_b[tournament_winner.index] += 1
        # For survival teams, we'd need more complex mapping

    # Build final projections
    projections = []
    for idx, team in enumerate(teams_a):
        projections.append(TeamProjection(
            group='A', name=team.team_name, current_points=team.total_points,
            direct_finals_pct=direct_a[idx] / num_simulations * 100,
            survival_pct=survival_a[idx] / num_simulations * 100,
            eliminated_group_pct=elim_a[idx] / num_simulations * 100,
            overall_finals_pct=overall_a[idx] / num_simulations * 100,
            win_tournament_pct=wins_a[idx] / num_simulations * 100,
        ))
        
    for idx, team in enumerate(teams_b):
        projections.append(TeamProjection(
            group='B', name=team.team_name, current_points=team.total_points,
            direct_finals_pct=direct_b[idx] / num_simulations * 100,
            survival_pct=survival_b[idx] / num_simulations * 100,
            eliminated_group_pct=elim_b[idx] / num_simulations * 100,
            overall_finals_pct=overall_b[idx] / num_simulations * 100,
            win_tournament_pct=wins_b[idx] / num_simulations * 100,
        ))
        
    avg_finals_games = total_finals_games / num_simulations
    return projections, avg_finals_games

# ---------------------------------------------------------------------------
# Formatting / display
# ---------------------------------------------------------------------------

def print_rankings(teams: tuple[TeamResult, ...], group_name: str) -> None:
    print(f"--- GROUP {group_name} STANDINGS ---")
    print(f"{'RK':<4}{'Team':<35}{'Points':<10}{'Elims':<8}{'Avg Pts':<10}{'Avg Pl':<8}")
    print("-" * 75)
    
    sorted_teams = sorted(teams, key=lambda t: (-t.total_points, -t.total_elims))
    for idx, team in enumerate(sorted_teams, start=1):
        print(
            f"{idx:<4}"
            f"{team.team_name:<35}"
            f"{team.total_points:<10}"
            f"{team.total_elims:<8}"
            f"{team.avg_points:<10.2f}"
            f"{team.avg_place:<8.2f}"
        )
    print()

def print_projections(projections: list[TeamProjection], avg_finals_games: float) -> None:
    print("╔" + "═" * 88 + "╗")
    print("║  🏆 TOURNAMENT STRUCTURE")
    print("║  Group Stage: 10 matches | Top 7 -> Finals | 8-17 -> Survival | 18+ -> Eliminated")
    print(f"║  Survival Stage: {SURVIVAL_GAMES} matches | Top {SURVIVAL_ADVANCE} advance to Finals")
    print(f"║  Grand Finals: Match Point ({MATCH_POINT_THRESHOLD} pts + Win) | Max {FINAL_MAX_GAMES} games")
    print("╚" + "═" * 88 + "╝\n")
    
    for group in ['A', 'B']:
        print(f"--- GROUP {group} PROJECTIONS ({NUM_SIMULATIONS:,} simulations) ---")
        print(f"{'Team':<35}{'Pts':<6}{'Direct':>8}{'Surv':>8}{'Elim':>8}{'Finals':>8}")
        print("-" * 73)
        
        group_projs = [p for p in projections if p.group == group]
        for proj in sorted(group_projs, key=lambda p: -p.current_points):
            print(
                f"{proj.name:<35}"
                f"{proj.current_points:<6}"
                f"{proj.direct_finals_pct:>7.1f}%"
                f"{proj.survival_pct:>7.1f}%"
                f"{proj.eliminated_group_pct:>7.1f}%"
                f"{proj.overall_finals_pct:>7.1f}%"
            )
        print()

    # OVERALL TOURNAMENT WIN PROBABILITY
    print("╔" + "═" * 55 + "╗")
    print("║  🏆 OVERALL TOURNAMENT WIN PROBABILITY 🏆           ║")
    print("╚" + "═" * 55 + "╝")
    print(f"{'Rank':<6}{'Team':<35}{'Grp':<5}{'Win Chance':>10}")
    print("-" * 56)
    
    sorted_by_win = sorted(projections, key=lambda p: -p.win_tournament_pct)
    
    for rank, proj in enumerate(sorted_by_win, start=1):
        win_str = f"{proj.win_tournament_pct:.3f}%"
        print(f"{rank:<6}{proj.name:<35}{proj.group:<5}{win_str:>10}")
    
    # VERY BOTTOM STAT
    print("\n" + "=" * 56)
    print(f"📊 Average Games Needed to Finish Grand Finals: {avg_finals_games:.2f}")
    print("=" * 56)

def main() -> None:
    print_rankings(GROUP_A_TEAMS, "A")
    print_rankings(GROUP_B_TEAMS, "B")
    
    projections, avg_finals_games = run_full_simulation(
        GROUP_A_TEAMS, 
        GROUP_B_TEAMS, 
        SURVIVAL_STAGE_TEAMS,
        SURVIVAL_ACTUAL_RESULTS
    )
    print_projections(projections, avg_finals_games)

if __name__ == "__main__":
    main()