import plotly.graph_objects as go
import streamlit as st

from build_dataset import compute_benchmark_curve, read_cached_dataset

st.title("BounceBack")

# Streamlit apps work differently than a normal script: every time you
# interact with a widget (like the dropdown below), Streamlit reruns this
# *entire file* from top to bottom. That used to mean live nba_api calls
# on every cold start — and when stats.nba.com is slow or blocking us, the
# app just hung on a blank page. So the app no longer talks to the network
# at all: it only reads the saved all_players_cache.csv, which is a quick
# local file read (no @st.cache_data needed). The slow fetching happens
# separately, by running `python build_dataset.py`.
all_data_df = read_cached_dataset()

# If the data file hasn't been built yet, say so plainly instead of
# crashing. st.stop() ends this run of the script right here, so none of
# the code below (which needs the data) runs.
if all_data_df is None:
    st.error(
        "No data yet. Build it once with `python build_dataset.py` "
        "(this fetches from stats.nba.com), then refresh this page."
    )
    st.stop()

# The app only covers players who returned from a significant injury
# during the 2025-26 season, so there's no season dropdown — just a caption
# saying so. Injury type and team act as filters that narrow down the
# player dropdown below. Each gets an "All" choice up front so it can be
# left unused, and the team list is built from only the rows that survived
# the injury-type filter — that way you never see a team with no players
# for the chosen injury.
st.caption("Injury recoveries in the 2025-26 NBA season, by injury type and team")

injury_types = sorted(all_data_df["INJURY_TYPE"].unique())
selected_injury_type = st.selectbox("Injury type", ["All"] + injury_types)

injury_df = all_data_df
if selected_injury_type != "All":
    injury_df = injury_df[injury_df["INJURY_TYPE"] == selected_injury_type]

teams = sorted(injury_df["TEAM"].unique())
selected_team = st.selectbox("Team", ["All"] + teams)

team_df = injury_df
if selected_team != "All":
    team_df = team_df[team_df["TEAM"] == selected_team]

# st.selectbox() renders an actual dropdown widget in the browser.
# The second argument is the list of choices — here, every unique value
# in the PLAYER column of whatever's left after the filters above. Whatever
# the user picks gets returned and stored in selected_player.
player_list = team_df["PLAYER"].unique()
selected_player = st.selectbox("Choose a player", player_list)

# A dictionary mapping a friendly label (what the user sees in the
# dropdown) to the actual column prefix used in the data (what our code
# needs). st.selectbox shows the dictionary's keys as choices; once the
# user picks one, we look up its matching value ourselves.
stat_options = {
    "Points": "PTS",
    "Rebounds": "REB",
    "Assists": "AST",
    "Steals": "STL",
    "Blocks": "BLK",
    "Turnovers": "TOV",
}
selected_stat_label = st.selectbox("Choose a stat", list(stat_options.keys()))
selected_stat = stat_options[selected_stat_label]

# The rolling-average column for whichever stat is selected, e.g.
# "REB_ROLLING_AVG" — built the same way for every stat back in
# injury_split.py, so we can just plug the name together here.
rolling_col = f"{selected_stat}_ROLLING_AVG"

# Computed from every player in the dataset, for whichever stat is
# currently selected — it's cheap (just averaging already-loaded rows, no
# network calls), so we recompute it on the fly rather than caching it.
benchmark_df = compute_benchmark_curve(all_data_df, stat_column=rolling_col)

# Filter the big combined table down to just the rows for whichever player
# is currently selected in the dropdown.
filtered_df = all_data_df[all_data_df["PLAYER"] == selected_player]

# Every row for one player carries the same injury type, so grabbing the
# first row's value is enough — we use it in the chart title below.
player_injury_type = filtered_df["INJURY_TYPE"].iloc[0]

fig = go.Figure()

# One fixed color per period, reused everywhere that period shows up, so
# "Before" is always the same color no matter which line it's part of.
period_colors = {"Before": "#4C78A8", "After": "#E45756"}

# We dropped the raw, game-by-game dots from the chart — with 6 traces
# (raw + smoothed for 2 periods, plus 2 benchmark lines) all fighting for
# attention, the noisy dots were the least useful piece. Keeping just the
# two smoothed lines below cuts that down to 4 traces and makes the actual
# trend far easier to read at a glance.

# .groupby("PERIOD") splits filtered_df into its "Before" and "After"
# chunks. Looping over it gives us each period's name and its own
# mini-DataFrame, one at a time.
for period, period_df in filtered_df.groupby("PERIOD"):
    fig.add_trace(go.Scatter(
        x=period_df["GAMES_FROM_RETURN"],
        y=period_df[rolling_col],
        mode="lines",
        name=f"{selected_player} ({period})",
        line=dict(color=period_colors[period], width=3),
    ))

# The benchmark: a single gray, dashed line across both periods, showing
# the average "typical" recovery trend across every player in the dataset, regardless of
# who's currently selected. compute_benchmark_curve() sorts its rows by
# GAMES_FROM_RETURN (Before is negative, After is positive), so we don't
# need to split this into two traces — one continuous line reads just as clearly and is one
# less legend entry to parse.
fig.add_trace(go.Scatter(
    x=benchmark_df["GAMES_FROM_RETURN"],
    y=benchmark_df[rolling_col],
    mode="lines",
    name="All-player average (all injuries)",
    line=dict(color="gray", dash="dash", width=2),
))

# A vertical line at x=0 marks the injury/return point itself — the one
# spot that matters most on this chart — so "before" and "after" are
# obvious without needing extra colors or legend entries to explain it.
fig.add_vline(x=0, line_dash="dot", line_color="gray", opacity=0.6)
fig.add_annotation(x=0, y=1, yref="paper", text="Return", showarrow=False, yshift=10)

fig.update_layout(
    title=f"{selected_player} ({player_injury_type}) — {selected_stat_label} Per Game (5-Game Rolling Average)",
    xaxis_title="Games From Return (negative = before injury)",
    yaxis_title=selected_stat_label,
)

# st.plotly_chart() is Streamlit's way of embedding a plotly figure
# directly into the page, instead of plotly opening its own browser tab.
st.plotly_chart(fig)
