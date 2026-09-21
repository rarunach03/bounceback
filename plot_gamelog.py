import plotly.express as px

from injury_split import get_before_after_gamelog

df = get_before_after_gamelog(
    player_name="Derrick Rose",
    before_season="2011-12",
    after_season="2013-14",
    injury_date="2012-04-28",
)

# plotly.express (imported as px) is a high-level charting library: instead
# of manually placing dots and lines ourselves, we just tell it which
# columns to use for which role, and it builds the whole chart for us.
fig = px.line(
    df,
    x="GAMES_FROM_RETURN",  # game number relative to the injury, not a real date
    y="PTS",                # what goes along the vertical axis
    color="PERIOD",         # draw a separate-colored line for each PERIOD value
    markers=True,           # show a dot at each actual game, not just a smooth line
    title="Derrick Rose — Points Per Game, Before vs. After ACL Injury",
)

# fig.show() opens the chart in a new browser tab. It's interactive: you can
# hover over points to see exact values, zoom, and pan.
fig.show()
