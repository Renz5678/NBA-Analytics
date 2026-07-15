from db import get_connection


def load_unprocessed_payloads(cur):
    cur.execute(
        "SELECT id, raw_payload FROM staging_games_raw WHERE processed = FALSE ORDER BY id;"
    )
    return cur.fetchall()


def parse_result_set(staged_json):
    """staged_json is {"season_type": ..., "data": <nba_api get_dict() output>}"""
    season_type = staged_json["season_type"]
    result_set = staged_json["data"]["resultSets"][0]
    headers = result_set["headers"]
    rows = result_set["rowSet"]
    records = [dict(zip(headers, row)) for row in rows]
    return records, season_type


def upsert_teams(cur, records):
    seen = set()
    for r in records:
        team_id = str(r["TEAM_ID"])
        if team_id in seen:
            continue
        seen.add(team_id)
        cur.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation)
            VALUES (%s, %s, %s)
            ON CONFLICT (team_id) DO NOTHING;
            """,
            (team_id, r["TEAM_NAME"], r["TEAM_ABBREVIATION"]),
        )


def determine_home_away(pair):
    """Derive home/away by matching TEAM_ABBREVIATION against the parsed
    MATCHUP string, rather than trusting each row's own MATCHUP field —
    some games (e.g. 0022401230) have both rows carrying the same
    'AWAY @ HOME' string instead of each team seeing its own perspective."""
    matchup = pair[0]["MATCHUP"]
    if "@" in matchup:
        away_abbr, home_abbr = [s.strip() for s in matchup.split("@")]
    elif "vs." in matchup:
        home_abbr, away_abbr = [s.strip() for s in matchup.split("vs.")]
    else:
        return None, None

    home = next((r for r in pair if r["TEAM_ABBREVIATION"] == home_abbr), None)
    away = next((r for r in pair if r["TEAM_ABBREVIATION"] == away_abbr), None)
    return home, away


def pair_and_upsert_games(cur, records, season_type):
    """Each GAME_ID appears twice (home + away perspective). Pair them up."""
    by_game_id = {}
    for r in records:
        by_game_id.setdefault(r["GAME_ID"], []).append(r)

    inserted = 0
    skipped = 0
    for game_id, pair in by_game_id.items():
        if len(pair) != 2:
            skipped += 1
            continue

        home, away = determine_home_away(pair)

        if home is None or away is None:
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO games (game_id, date, home_team_id, away_team_id, home_score, away_score, season, season_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (game_id) DO NOTHING;
            """,
            (
                game_id,
                home["GAME_DATE"],
                str(home["TEAM_ID"]),
                str(away["TEAM_ID"]),
                home["PTS"],
                away["PTS"],
                home["SEASON_ID"],
                season_type,
            ),
        )
        inserted += 1

    return inserted, skipped


def mark_processed(cur, staging_id):
    cur.execute(
        "UPDATE staging_games_raw SET processed = TRUE WHERE id = %s;", (staging_id,)
    )


def run_transform():
    conn = get_connection()
    if conn is None:
        raise SystemExit("Could not connect to database — aborting transform.")
    cur = conn.cursor()

    payloads = load_unprocessed_payloads(cur)
    print(f"Found {len(payloads)} unprocessed staging row(s).")

    for staging_id, staged_json in payloads:
        records, season_type = parse_result_set(staged_json)
        upsert_teams(cur, records)
        inserted, skipped = pair_and_upsert_games(cur, records, season_type)
        mark_processed(cur, staging_id)
        conn.commit()
        print(
            f"Staging row {staging_id} ({season_type}): {inserted} games inserted, {skipped} skipped."
        )

    cur.close()
    conn.close()


if __name__ == "__main__":
    run_transform()