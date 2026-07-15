import time
import json
from nba_api.stats.endpoints import leaguegamefinder
from db import get_connection


def fetch_games(season, season_types=("Regular Season", "Playoffs")):
    all_payloads = []
    for season_type in season_types:
        time.sleep(0.75)
        try:
            finder = leaguegamefinder.LeagueGameFinder(
                season_nullable=season,
                league_id_nullable="00",
                season_type_nullable=season_type,
            )
            payload = finder.get_dict()
            all_payloads.append((season_type, payload))
        except Exception as e:
            print(f"nba_api request failed for season={season}, type={season_type}: {e}")
            raise
    return all_payloads


def stage_raw(cur, conn, payload, source, season_type):
    cur.execute(
        "INSERT INTO staging_games_raw (raw_payload, source) VALUES (%s, %s)",
        (json.dumps({"season_type": season_type, "data": payload}), source),
    )
    conn.commit()


def ingest_season(season):
    conn = get_connection()
    if conn is None:
        raise SystemExit(f"Could not connect to database — aborting ingestion for {season}.")
    cur = conn.cursor()

    results = fetch_games(season)
    for season_type, payload in results:
        stage_raw(cur, conn, payload, source=f"nba_api_leaguegamefinder_{season_type}", season_type=season_type)
        print(f"Staged {len(payload['resultSets'][0]['rowSet'])} rows for {season} {season_type}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    ingest_season("2024-25")