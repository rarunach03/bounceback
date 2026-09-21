import pandas as pd

from fetch_gamelog import get_player_gamelog


def get_before_after_gamelog(player_name, before_season, after_season, injury_date):
    """Combine a player's pre- and post-injury season game logs into one
    table, with a PERIOD column marking each game 'Before' or 'After'."""

    # pd.Timestamp is pandas' version of a single date/time value — the same
    # kind of object each GAME_DATE became after we ran pd.to_datetime() on
    # it back in fetch_gamelog.py. Converting the injury_date string here
    # (instead of requiring the caller to do it) means this function accepts
    # a plain date string like "2012-04-28", which is simpler to call with.
    injury_date = pd.Timestamp(injury_date)

    # Reuse the function we already built in fetch_gamelog.py — this is
    # exactly why we made it return a DataFrame instead of just printing one.
    before_df = get_player_gamelog(player_name, before_season)
    after_df = get_player_gamelog(player_name, after_season)

    # pd.concat() stacks two DataFrames on top of each other (like taping
    # two tables together, one after the other). ignore_index=True tells
    # pandas to renumber the rows 0, 1, 2... afterward, instead of keeping
    # each table's original row numbers (which would otherwise create
    # duplicates, e.g. two rows both labeled "0").
    combined_df = pd.concat([before_df, after_df], ignore_index=True)

    # We already unambiguously know which games are "before" and which are
    # "after": before_df's rows came first in the concatenation above, and
    # after_df's rows came second. So instead of comparing each GAME_DATE
    # to injury_date (which sounds right but has a subtle bug — a player's
    # very last game before injury sometimes falls exactly ON injury_date,
    # since that's often the game the injury happened during, and "date <
    # injury_date" wrongly excludes that day), we build the label directly
    # from which DataFrame each row came from.
    n_before = len(before_df)
    n_after = len(after_df)
    combined_df["PERIOD"] = ["Before"] * n_before + ["After"] * n_after

    # Real calendar dates leave a huge, meaningless gap between seasons (the
    # offseason plus recovery time). To make the two periods comparable, we
    # instead number games relative to the injury: the last game before it
    # is -1, the one before that is -2, ...; the first game back is +1, the
    # next is +2, and so on. Since before_df's rows come first in
    # combined_df and each was already sorted oldest-to-newest, we can build
    # this numbering as one plain list, in the same order as the rows
    # already sit in the table — same idea as the PERIOD column above.
    combined_df["GAMES_FROM_RETURN"] = list(range(-n_before, 0)) + list(range(1, n_after + 1))

    # We're no longer using injury_date to decide the split, but it's still
    # useful information to keep around on every row (e.g. for showing "days
    # since injury" later, or labeling a chart). Assigning a single value
    # like this broadcasts it to every row in the column automatically.
    combined_df["INJURY_DATE"] = injury_date

    # A single game's point total swings a lot from game to game, which
    # makes a raw line chart noisy and hard to read. A rolling average
    # smooths that out: for each game, it averages that game's stat with
    # the few before it, so the line shows the underlying trend instead of
    # every up-and-down.
    #
    # groupby("PERIOD") splits the data into "Before" and "After" groups
    # first, so the rolling average is calculated separately within each
    # period. This matters a lot: without it, the rolling average for the
    # very first game back after injury would get blended with his last
    # few games *before* the injury — two completely different situations
    # that just happen to sit next to each other as rows in this table.
    #
    # .transform(...) runs a calculation on each group separately, but
    # hands back a result that's the same length and in the same row order
    # as the original data — so it slots right back in as a new column.
    #
    # .rolling(window=5, min_periods=1).mean() looks at each game plus the
    # 4 before it (a "window" of 5) and averages them. min_periods=1 means
    # the first few games in each period (before there are 5 to average)
    # will still get a value, just averaged over however many are
    # available so far, instead of showing nothing.
    #
    # We want this for more than just points now (rebounds, assists, etc.),
    # so instead of hardcoding "PTS" once, we loop over a list of stat
    # columns and repeat the same calculation for each one, naming each
    # result "<stat>_ROLLING_AVG" (e.g. "REB_ROLLING_AVG").
    for stat in ["PTS", "REB", "AST", "STL", "BLK", "TOV"]:
        combined_df[f"{stat}_ROLLING_AVG"] = (
            combined_df.groupby("PERIOD")[stat]
            .transform(lambda values: values.rolling(window=5, min_periods=1).mean())
        )

    return combined_df


if __name__ == "__main__":
    df = get_before_after_gamelog(
        player_name="Derrick Rose",
        before_season="2011-12",
        after_season="2013-14",
        injury_date="2012-04-28",
    )
    print(df.to_string(index=False))
