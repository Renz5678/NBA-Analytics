CREATE TABLE IF NOT EXISTS staging_games_raw (
  id            SERIAL PRIMARY KEY,
  raw_payload   JSONB NOT NULL,
  source        VARCHAR NOT NULL DEFAULT 'nba_api',
  pulled_at     TIMESTAMP NOT NULL DEFAULT NOW(),
  processed     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS teams (
  team_id       VARCHAR PRIMARY KEY,
  name          VARCHAR NOT NULL,
  abbreviation  VARCHAR NOT NULL,
  conference    VARCHAR,
  division      VARCHAR
);

CREATE TABLE IF NOT EXISTS games (
  game_id       VARCHAR PRIMARY KEY,
  date          DATE NOT NULL,
  home_team_id  VARCHAR REFERENCES teams(team_id),
  away_team_id  VARCHAR REFERENCES teams(team_id),
  home_score    INTEGER,
  away_score    INTEGER,
  season        VARCHAR
);