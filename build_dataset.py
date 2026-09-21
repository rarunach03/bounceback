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

        all_players_dfs.append(player_df)

    # Stack every player's table into one big combined dataset.
    return pd.concat(all_players_dfs, ignore_index=True)


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
    all_data_df = build_all_players_dataset()
    print(f"\nTotal games across all players: {len(all_data_df)}")
    print(all_data_df.groupby("PLAYER").size())
