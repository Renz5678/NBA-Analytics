import time
from ingest_games import ingest_season
from transform_games import run_transform


def season_string(start_year):
    return f"{start_year}-{str(start_year + 1)[-2:]}"


SEASONS_TO_BACKFILL = [season_string(y) for y in range(2015, 2024)]  # 2015-16 ... 2023-24

if __name__ == "__main__":
    for season in SEASONS_TO_BACKFILL:
        print(f"--- Backfilling {season} ---")
        ingest_season(season)
        run_transform()
        time.sleep(3)  # extra courtesy delay between full seasons
    print("Backfill complete.")