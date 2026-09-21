import plotly.graph_objects as go
import streamlit as st

from build_dataset import build_all_players_dataset, compute_benchmark_curve

st.title("ReturnCurve")

# Streamlit apps work differently than a normal script: every time you
# interact with a widget (like the dropdown below), Streamlit reruns this
# *entire file* from top to bottom. Without help, that would mean redoing
# all 10 live nba_api calls from scratch on every single click, which is
# slow and unnecessary since the underlying data hasn't actually changed.
# @st.cache_data tells Streamlit: "run this function once, remember what
# it returned, and just hand back that saved result on future reruns"
# (it'll only actually re-run if the function's code or arguments change).
@st.cache_data
def load_data():
    return build_all_players_dataset()


all_data_df = load_data()

# st.selectbox() renders an actual dropdown widget in the browser.
# The second argument is the list of choices — here, every unique value
# in the PLAYER column. Whatever the user picks gets returned and stored
# in selected_player.
player_list = all_data_df["PLAYER"].unique()
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
# the average "typical" recovery trend across all 5 players, regardless of
# who's currently selected. Since GAMES_FROM_RETURN already sits Before
# (negative) then After (positive) in order, we don't need to split this
# into two traces — one continuous line reads just as clearly and is one
# less legend entry to parse.
fig.add_trace(go.Scatter(
    x=benchmark_df["GAMES_FROM_RETURN"],
    y=benchmark_df[rolling_col],
    mode="lines",
    name="All-player average",
    line=dict(color="gray", dash="dash", width=2),
))

# A vertical line at x=0 marks the injury/return point itself — the one
# spot that matters most on this chart — so "before" and "after" are
# obvious without needing extra colors or legend entries to explain it.
fig.add_vline(x=0, line_dash="dot", line_color="gray", opacity=0.6)
fig.add_annotation(x=0, y=1, yref="paper", text="Return", showarrow=False, yshift=10)

fig.update_layout(
    title=f"{selected_player} — {selected_stat_label} Per Game (5-Game Rolling Average)",
    xaxis_title="Games From Return (negative = before injury)",
    yaxis_title=selected_stat_label,
)

# st.plotly_chart() is Streamlit's way of embedding a plotly figure
# directly into the page, instead of plotly opening its own browser tab.
st.plotly_chart(fig)
