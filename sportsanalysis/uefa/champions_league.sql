-- UEFA Champions League 2025-26 Tournament Database Schema
-- SQLITE3 Compatible

-- =============================================================================
-- TEAMS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL UNIQUE,
    team_short_name TEXT,
    country TEXT,
    league TEXT,
    elo_rating INTEGER DEFAULT 1500,
    elo_rating_deviation INTEGER DEFAULT 350,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- VENUES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS venues (
    venue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_name TEXT NOT NULL,
    city TEXT,
    country TEXT,
    capacity INTEGER,
    is_neutral_venue BOOLEAN DEFAULT 0
);

-- =============================================================================
-- ROUNDS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS rounds (
    round_id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_name TEXT NOT NULL UNIQUE,
    round_order INTEGER NOT NULL,
    description TEXT
);

-- =============================================================================
-- MATCHES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL,
    match_number INTEGER NOT NULL,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    venue_id INTEGER,
    first_leg_date DATE,
    second_leg_date DATE,
    first_leg_home_goals INTEGER,
    first_leg_away_goals INTEGER,
    second_leg_home_goals INTEGER,
    second_leg_away_goals INTEGER,
    aggregate_home_goals INTEGER,
    aggregate_away_goals INTEGER,
    winner_team_id INTEGER,
    is_completed BOOLEAN DEFAULT 0,
    is_draw BOOLEAN DEFAULT 0,
    required_extra_time BOOLEAN DEFAULT 0,
    decided_on_penalties BOOLEAN DEFAULT 0,
    penalty_shootout_home_score INTEGER,
    penalty_shootout_away_score INTEGER,
    home_advantage_applied BOOLEAN DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (round_id) REFERENCES rounds(round_id),
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id),
    FOREIGN KEY (winner_team_id) REFERENCES teams(team_id)
);

-- =============================================================================
-- SIMULATIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS simulations (
    simulation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_name TEXT,
    num_simulations INTEGER DEFAULT 10000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- SIMULATION RESULTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS simulation_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    round_of_16_appearances INTEGER DEFAULT 0,
    quarterfinal_appearances INTEGER DEFAULT 0,
    semifinal_appearances INTEGER DEFAULT 0,
    final_appearances INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    win_probability REAL DEFAULT 0.0,
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- =============================================================================
-- SIMULATED MATCH SCORES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS simulated_match_scores (
    score_id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_id INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    home_goals INTEGER,
    away_goals INTEGER,
    probability REAL,
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id),
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

-- =============================================================================
-- ACTUAL RESULTS TABLE (for inputting real match results)
-- =============================================================================
CREATE TABLE IF NOT EXISTS actual_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL UNIQUE,
    actual_home_goals INTEGER,
    actual_away_goals INTEGER,
    actual_winner_id INTEGER,
    input_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified BOOLEAN DEFAULT 0,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (actual_winner_id) REFERENCES teams(team_id)
);

-- =============================================================================
-- PREDICTION COMPARISON TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS prediction_comparisons (
    comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    simulation_id INTEGER,
    predicted_winner_id INTEGER,
    predicted_home_goals REAL,
    predicted_away_goals REAL,
    predicted_margin REAL,
    actual_winner_id INTEGER,
    actual_home_goals INTEGER,
    actual_away_goals INTEGER,
    prediction_correct BOOLEAN,
    prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id),
    FOREIGN KEY (predicted_winner_id) REFERENCES teams(team_id),
    FOREIGN KEY (actual_winner_id) REFERENCES teams(team_id)
);

-- =============================================================================
-- ELO HISTORY TABLE (track ELO changes over time)
-- =============================================================================
CREATE TABLE IF NOT EXISTS elo_history (
    elo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    match_id INTEGER,
    old_elo INTEGER,
    new_elo INTEGER,
    elo_change INTEGER,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

-- =============================================================================
-- TOURNAMENT PROGRESS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS tournament_progress (
    progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
    current_round_id INTEGER,
    round_complete BOOLEAN DEFAULT 0,
    final_complete BOOLEAN DEFAULT 0,
    champion_team_id INTEGER,
    final_date DATE,
    final_venue_id INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_round_id) REFERENCES rounds(round_id),
    FOREIGN KEY (champion_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (final_venue_id) REFERENCES venues(venue_id)
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_matches_round ON matches(round_id);
CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team_id, away_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_completed ON matches(is_completed);
CREATE INDEX IF NOT EXISTS idx_simulation_results_team ON simulation_results(team_id);
CREATE INDEX IF NOT EXISTS idx_elo_history_team ON elo_history(team_id);
CREATE INDEX IF NOT EXISTS idx_actual_results_match ON actual_results(match_id);

-- =============================================================================
-- VIEW: MATCHES WITH TEAMS
-- =============================================================================
CREATE VIEW IF NOT EXISTS v_matches_with_teams AS
SELECT 
    m.match_id,
    r.round_name,
    m.match_number,
    ht.team_name AS home_team,
    at.team_name AS away_team,
    v.venue_name,
    m.first_leg_date,
    m.second_leg_date,
    m.first_leg_home_goals,
    m.first_leg_away_goals,
    m.second_leg_home_goals,
    m.second_leg_away_goals,
    m.aggregate_home_goals,
    m.aggregate_away_goals,
    CASE 
        WHEN m.is_draw = 1 THEN 'Draw'
        WHEN wt.team_name IS NOT NULL THEN wt.team_name
        ELSE 'TBD'
    END AS winner,
    m.is_completed
FROM matches m
JOIN rounds r ON m.round_id = r.round_id
JOIN teams ht ON m.home_team_id = ht.team_id
JOIN teams at ON m.away_team_id = at.team_id
LEFT JOIN venues v ON m.venue_id = v.venue_id
LEFT JOIN teams wt ON m.winner_team_id = wt.team_id
ORDER BY r.round_order, m.match_number;

-- =============================================================================
-- VIEW: TEAM PERFORMANCE SUMMARY
-- =============================================================================
CREATE VIEW IF NOT EXISTS v_team_performance AS
SELECT 
    t.team_name,
    t.elo_rating,
    COUNT(CASE WHEN m.winner_team_id = t.team_id AND m.is_completed = 1 THEN 1 END) AS wins,
    COUNT(CASE WHEN m.home_team_id = t.team_id AND m.is_completed = 1 THEN 1 END) +
    COUNT(CASE WHEN m.away_team_id = t.team_id AND m.is_completed = 1 THEN 1 END) AS matches_played,
    SUM(CASE WHEN m.home_team_id = t.team_id THEN COALESCE(m.first_leg_home_goals, 0) + COALESCE(m.second_leg_home_goals, 0)
             WHEN m.away_team_id = t.team_id THEN COALESCE(m.first_leg_away_goals, 0) + COALESCE(m.second_leg_away_goals, 0)
             ELSE 0
    END) AS goals_scored
FROM teams t
LEFT JOIN matches m ON t.team_id = m.home_team_id OR t.team_id = m.away_team_id
GROUP BY t.team_id;
