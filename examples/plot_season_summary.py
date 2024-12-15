"""
Season Summary Visualization
==================================
This example demonstrates how to summarize the season by visualizing
race results, points progression, and other key statistics.
.. codeauthor:: Vandana
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.io import show
from plotly.subplots import make_subplots

from fastf1.ergast import Ergast


# Initialize Ergast API
ergast = Ergast()

# Fetch the event schedule
schedules = ergast.get_race_schedule(2022)
races = pd.DataFrame(schedules)

standings = []

for _, race in races.iterrows():
    race_name = race["raceName"]
    round_number = race["round"]

    # Fetch the race session
    session = ergast.get_race_results(2022, round_number)  # Race session

    sprint_session = None

    try:
        sprint_session = ergast.get_sprint_results(2022, round_number)
    except Exception:
        pass

    # Fetch race data
    race_results = session.content
    race_results = pd.DataFrame(race_results[0])
    for driver in race_results["driverCode"]:
        driver_result = race_results[race_results["driverCode"] == driver]
        points = driver_result["points"]
        position = driver_result["position"]

        # Add sprint race points if applicable
        if sprint_session.content:
            sprint_results = sprint_session.content
            sprint_results = pd.DataFrame(sprint_results[0])
            if driver in sprint_results["driverCode"].values:
                sprint_points = int(
                    sprint_results[sprint_results["driverCode"] == driver][
                        "points"
                    ].iloc[0]
                )
            else:
                sprint_points = 0
        else:
            sprint_points = 0

        standings.append(
            {
                "Race": race_name,
                "RoundNumber": round_number,
                "Driver": driver,
                "Points": int(points.iloc[0]) + sprint_points,
                "Position": int(position.iloc[0]),
            }
        )


df = pd.DataFrame(standings)

# Prepare heatmap data
heatmap_data = df.pivot(
    index="Driver", columns="RoundNumber", values="Points"
).fillna(0)
heatmap_data["Total Points"] = heatmap_data.sum(axis=1)
heatmap_data = heatmap_data.sort_values(by="Total Points", ascending=True)

# Prepare position data
position_data = df.pivot(
    index="Driver", columns="RoundNumber", values="Position"
).fillna("N/A")

# Map race names
race_name_mapping = dict(zip(races["round"], races["raceName"]))

# Simplify x-axis labels
heatmap_data_rounds = heatmap_data.iloc[:, :-1]
x_labels_rounds = [str(race) for race in heatmap_data.columns[:-1]]
x_labels_total = ["Total Points"]

# Custom colorscales
colorscale_rounds = [[0, "#aee2fb"], [0.433, "#69bce8"], [1, "#3085be"]]
colorscale_total = [[0, "#ffcccc"], [0.433, "#ff6666"], [1, "#cc0000"]]

# Prepare custom_data for hover information (only for rounds)
custom_data = np.array(
    [
        [
            {
                "position": position_data.at[driver, race]
                if race in position_data.columns
                else "N/A",
                "race_name": race_name_mapping.get(race, "Unknown"),
            }
            for race in heatmap_data.columns[:-1]
        ]
        for driver in heatmap_data.index
    ]
)

custom_data_rounds = custom_data[:, :-1]

# Get max values for normalization
max_points_rounds = heatmap_data_rounds.values.max()
max_points_total = heatmap_data.iloc[:, -1:].values.max()

# Create subplots for two heatmaps
fig = make_subplots(
    rows=1,
    cols=2,
    column_widths=[0.85, 0.15],
    horizontal_spacing=0.05,
    subplot_titles=("F1 2022 Season Rounds", "Total Points"),
)

# Heatmap for individual rounds
fig.add_trace(
    go.Heatmap(
        z=heatmap_data_rounds.values,
        x=x_labels_rounds,
        y=heatmap_data_rounds.index,
        customdata=custom_data,
        text=heatmap_data_rounds.values,
        texttemplate="%{text}",
        textfont={"size": 12},
        colorscale=colorscale_rounds,
        showscale=False,
        zmin=0,
        zmax=max_points_rounds,
        hovertemplate=(
            "Driver: %{y}<br>"
            "Round: %{x}<br>"
            "Race Name: %{customdata.race_name}<br>"
            "Points: %{z}<br>"
            "Position: %{customdata.position}<extra></extra>"
        ),
    ),
    row=1,
    col=1,
)

# Heatmap for total points
fig.add_trace(
    go.Heatmap(
        z=heatmap_data.iloc[:, -1:].values,
        x=x_labels_total,
        y=heatmap_data.index,
        text=heatmap_data.iloc[:, -1:].values,
        texttemplate="%{text}",
        textfont={"size": 12},
        colorscale=colorscale_total,
        showscale=False,
        hoverinfo="none",
        zmin=0,
        zmax=max_points_total,
    ),
    row=1,
    col=2,
)

# Update layout
fig.update_xaxes(title_text="Rounds", row=1, col=1)
fig.update_yaxes(title_text="Drivers", row=1, col=1)
fig.update_layout(title="F1 Results Tracker Heatmap")

# Plot the updated heatmap
show(fig)
