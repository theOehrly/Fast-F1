"""
Season Summary Visualization
==================================
This example demonstrates how to make an interactive season summarization
dashboard showing points scored by each driver at each round.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.io import show
from plotly.subplots import make_subplots

import fastf1 as ff1


##############################################################################
season = 2024
schedule = ff1.get_event_schedule(season, include_testing=False)

##############################################################################
# Get each driver's finishing positions and points total for each round.
standings = []
# Shorten the event names by trimming Grand Prix from the name.
# This will be used to label our graph.
short_event_names = []

for _, event in schedule.iterrows():
    event_name, round_number = event["EventName"], event["RoundNumber"]
    short_event_names.append(event_name.replace("Grand Prix", "").strip())

    # Only need to load the results data
    race = ff1.get_session(season, event_name, "R")
    race.load(laps=False, telemetry=False, weather=False, messages=False)

    # Add sprint race points if applicable
    sprint = None
    # F1 has used different names for the sprint race event format
    # From 2024 onwards, it has been "sprint_qualifying"
    # In 2023, you should match on "sprint_shootout"
    # In 2022 and 2021, you should match on "sprint"
    if event["EventFormat"] == "sprint_qualifying":
        sprint = ff1.get_session(season, event_name, "S")
        sprint.load(laps=False, telemetry=False, weather=False, messages=False)

    for _, driver_row in race.results.iterrows():
        abbreviation, race_points, race_position = (
            driver_row["Abbreviation"],
            driver_row["Points"],
            driver_row["Position"],
        )

        sprint_points = 0
        if sprint is not None:
            driver_row = sprint.results[
                sprint.results["Abbreviation"] == abbreviation
            ]
            if not driver_row.empty:
                # We need the values[0] accessor because driver_row is actually
                # returned as a dataframe with a single row
                sprint_points = driver_row["Points"].values[0]

        standings.append(
            {
                "EventName": event_name,
                "RoundNumber": round_number,
                "Driver": abbreviation,
                "Points": race_points + sprint_points,
                "Position": race_position,
            }
        )

##############################################################################
# Now we have a dataframe where each row can be seen as two parts.
# `["EventName", "RoundNumber", "Driver"]` which act like an index.
# `["Points", "Position"]` which contain the actual data we want to plot.
df = pd.DataFrame(standings)

##############################################################################
# We remake it into an easier to use format where the row indices are the
# drivers, and the columns are the races. This allows us to look up the points
# scored by a driver at a race more easily.
heatmap_data = df.pivot(
    index="Driver", columns="RoundNumber", values="Points"
).fillna(0)

# Save the final drivers standing and sort the data such that the lowest-
# scoring driver is towards the bottom
heatmap_data["total_points"] = heatmap_data.sum(axis=1)
heatmap_data = heatmap_data.sort_values(by="total_points", ascending=True)
total_points = heatmap_data["total_points"].values
heatmap_data = heatmap_data.drop(columns=["total_points"])

# Do the same for position.
position_data = df.pivot(
    index="Driver", columns="RoundNumber", values="Position"
).fillna("N/A")

##############################################################################
# Prepare the hover text
hover_info = [
    [
        {
            "position": position_data.at[driver, race],
        }
        for race in schedule["RoundNumber"]
    ]
    for driver in heatmap_data.index
]

##############################################################################
# Create the subplots for the two heatmaps
fig = make_subplots(
    rows=1,
    cols=2,
    column_widths=[0.85, 0.15],
    subplot_titles=("F1 2024 Season Summary", "Total Points"),
)
fig.update_layout(width=900, height=800)

# Per round summary heatmap
fig.add_trace(
    go.Heatmap(
        # Use the race names as x labels and the driver abbreviations
        # as the y labels
        x=short_event_names,
        y=heatmap_data.index,
        z=heatmap_data.values,
        # Use the points scored as overlay text
        text=heatmap_data.values,
        texttemplate="%{text}",
        textfont={"size": 12},
        customdata=hover_info,
        hovertemplate=(
            "Driver: %{y}<br>"
            "Race Name: %{x}<br>"
            "Points: %{z}<br>"
            "Position: %{customdata.position}<extra></extra>"
        ),
        colorscale="YlGnBu",
        showscale=False,
        zmin=0,
        # We need to set zmax for the two heatmaps separately as the
        # max value in the total points plot is significantly higher.
        zmax=heatmap_data.values.max(),
    ),
    row=1,
    col=1,
)

# Heatmap for total points
fig.add_trace(
    go.Heatmap(
        x=["Total Points"] * len(total_points),
        y=heatmap_data.index,
        z=total_points,
        text=total_points,
        texttemplate="%{text}",
        textfont={"size": 12},
        colorscale="YlGnBu",
        showscale=False,
        zmin=0,
        zmax=total_points.max(),
    ),
    row=1,
    col=2,
)

# Plot the updated heatmap
show(fig)
