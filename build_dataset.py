import os
import time

import pandas as pd

from injury_split import get_before_after_gamelog


def build_all_players_dataset(csv_path="injuries.csv"):
    """Fetch and combine before/after game logs for every player listed in
    the injuries CSV, returning one big DataFrame tagged with PLAYER."""

    # pd.read_csv() reads a CSV file straight into a DataFrame — one row per
    # line in the file, one column per comma-separated field, using the
    # first line as the column headers automatically.
    injuries_df = pd.read_csv(csv_path)

    # We'll collect one combined_df per player in this list, then stack
    # them all together at the very end — same idea as pd.concat() before,
    # just with more than two tables this time.
    all_players_dfs = []

    # .iterrows() lets us loop over a DataFrame one row at a time. For each
    # row, it gives us the row's position (which we don't need here, hence
    # the underscore _ as a "throwaway" variable name) and the row's data
    # itself, which we can access like a dictionary (row["player_name"]).
    for _, row in injuries_df.iterrows():
        print(f"Fetching {row['player_name']}...")

        # A short pause between players: firing dozens of requests back to
        # back is what got us throttled by stats.nba.com in the first place.
        time.sleep(1.5)

        player_df = get_before_after_gamelog(
            player_name=row["player_name"],
            before_season=row["before_season"],
            after_season=row["after_season"],
            injury_date=row["injury_date"],
        )

        # Tag each player's rows with their name, since once we stack
        # everyone together into one big table, we'll need a way to tell
        # whose game is whose.
        player_df["PLAYER"] = row["player_name"]

        # The same idea for organizing by season and team: tag every row
        # with the season the injury happened in (straight from the CSV) and
        # the team the player was on when it happened. MATCHUP looks like
        # "GSW vs. TOR" or "GSW @ TOR" — the player's own team is always the
        # first word, so .split(" ")[0] pulls it out. We read it from the
        # last "Before" game (.iloc[-1]) because that's the closest game to
        # the injury, and players can change teams between seasons.
        before_games = player_df[player_df["PERIOD"] == "Before"]
        player_df["TEAM"] = before_games["MATCHUP"].iloc[-1].split(" ")[0]
        player_df["INJURY_SEASON"] = row["before_season"]

        # And the same again for what kind of injury it was, straight from
        # the CSV, so the app can filter by injury type.
        player_df["INJURY_TYPE"] = row["injury_type"]

        all_players_dfs.append(player_df)

    # Stack every player's table into one big combined dataset.
    return pd.concat(all_players_dfs, ignore_index=True)


def read_cached_dataset(cache_path="all_players_cache.csv"):
    """Read the saved dataset from disk, or return None if it hasn't been
    built yet. This never touches the network, so the app can call it on
    every load without ever hanging."""

    if not os.path.exists(cache_path):
        return None

    # parse_dates turns these two columns back into real dates when
    # reading — a CSV only stores plain text, so without it they'd come
    # back as strings.
    return pd.read_csv(cache_path, parse_dates=["GAME_DATE", "INJURY_DATE"])


def save_dataset(csv_path="injuries.csv", cache_path="all_players_cache.csv"):
    """Fetch everything from the NBA API and save it to the cache file.
    This is the slow, network-dependent step, so it runs on its own from
    the command line (python build_dataset.py) instead of inside the app —
    the data for past seasons never changes, so you only need to re-run it
    when you add players to injuries.csv."""

    all_data_df = build_all_players_dataset(csv_path)
    all_data_df.to_csv(cache_path, index=False)
    return all_data_df


def compute_benchmark_curve(all_data_df, stat_column="PTS_ROLLING_AVG"):
    """Average every player's smoothed stat at each GAMES_FROM_RETURN value,
    producing one 'typical recovery' line across the whole dataset. Defaults
    to points, but stat_column can be any of the "<STAT>_ROLLING_AVG"
    columns injury_split.py computes (e.g. "REB_ROLLING_AVG")."""

    # groupby() with a LIST of two columns groups rows by every unique
    # combination of the two — here, every (PERIOD, GAMES_FROM_RETURN) pair.
    # For example, one group is all rows where PERIOD="After" AND
    # GAMES_FROM_RETURN=3 — i.e. every player's 3rd game back from injury.
    # Taking .mean() of stat_column within each group gives the average
    # "how well players were typically doing" at that exact point in their
    # recovery timeline, across everyone in the dataset.
    benchmark_df = (
        all_data_df.groupby(["PERIOD", "GAMES_FROM_RETURN"])[stat_column]
        .mean()
        .reset_index()
    )

    # groupby().mean() leaves PERIOD and GAMES_FROM_RETURN as a special
    # kind of row-label (called an index) instead of regular columns.
    # .reset_index() turns them back into normal columns, which is the
    # shape plotly expects to plot from.
    return benchmark_df


if __name__ == "__main__":
    all_data_df = save_dataset()
    print(f"\nSaved to all_players_cache.csv")
    print(f"Total games across all players: {len(all_data_df)}")
    print(all_data_df.groupby("PLAYER").size())
