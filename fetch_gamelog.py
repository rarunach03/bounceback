import pandas as pd
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog


def get_player_gamelog(player_name, season):
    """Fetch a clean, chronologically-sorted game log for one player/season."""

    # nba_api ships with a small built-in list of every player (past and
    # present). find_players_by_full_name() searches that list by name and
    # returns a list of matches (a list, because names aren't always unique).
    matches = players.find_players_by_full_name(player_name)

    # matches[0] grabs the first (and usually only) dictionary from the list.
    # ["id"] then grabs just the id value out of that dictionary.
    player_id = matches[0]["id"]

    # This is a *live* API call — it goes over the internet to NBA.com's
    # stats servers and asks for every game this player played that season.
    gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season)

    # The result comes back bundled as one or more pandas DataFrames (think:
    # spreadsheet-like tables). get_data_frames() returns a list of them,
    # and for this endpoint the game log itself is always the first one, [0].
    game_log_df = gamelog.get_data_frames()[0]

    # GAME_DATE comes back from the API as plain text, like "JAN 15, 2014".
    # pd.to_datetime() converts that text into a real datetime value, so
    # pandas understands it as an actual point in time rather than just a
    # string. This matters because sorting *text* would put dates in
    # alphabetical order (e.g. "APR" before "JAN"), not chronological order.
    game_log_df["GAME_DATE"] = pd.to_datetime(game_log_df["GAME_DATE"])

    # Out of the 27 columns the API gave us, these are the ones we actually
    # care about for tracking performance. Putting a list of column names
    # inside the [] selects just those columns, in this order.
    columns_to_keep = ["GAME_DATE", "MATCHUP", "WL", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV"]
    clean_df = game_log_df[columns_to_keep]

    # Sort by date, oldest first, since the API originally gives us newest first.
    clean_df = clean_df.sort_values("GAME_DATE")

    return clean_df


# This "if __name__ == '__main__'" block only runs when you execute this
# file directly (e.g. `python fetch_gamelog.py`). If some other file later
# imports get_player_gamelog() from this one, this block will NOT run —
# which is exactly what we want, since we don't want a print statement
# firing off every time we just want to reuse the function elsewhere.
if __name__ == "__main__":
    df = get_player_gamelog("Derrick Rose", "2013-14")

    # to_string(index=False) prints every row and column in full, without
    # pandas' usual truncation, and without the extra 0,1,2... index column
    # on the left (which isn't real data, just pandas' internal row numbering).
    print(df.to_string(index=False))
