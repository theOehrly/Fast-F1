"""
Season Summary Visualization
==================================

This example demonstrates how to summarize the season by visualizing
race results, points progression, and other key statistics.

.. codeauthor:: Vandana
"""

import logging

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.io import show
from plotly.subplots import make_subplots

import fastf1


logging.basicConfig(filename="debug.log", level=logging.WARNING)
fastf1.logger.set_log_level(logging.WARNING)

# Enable FastF1 cache
fastf1.Cache.enable_cache("../cache")

# Define sprint points allocation
SPRINT_POINTS = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}

# Load the event schedule and filter out testing events
schedules = fastf1.get_event_schedule(2022)
races = schedules[schedules["EventName"].str.contains("Grand Prix", na=False)]

# Prepare standings data
standings = []

for _, race in races.iterrows():  # Iterate over the filtered races
    race_name = race["OfficialEventName"]
    round_number = race["RoundNumber"]

    # Fetch the race session
    session = fastf1.get_session(2022, round_number, "R")  # Race session
    session.load()

    # Check for a sprint session (if exists)
    sprint_session = None

    try:
        sprint_session = fastf1.get_session(2022, round_number, "Sprint")
        sprint_session.load()
    except Exception:
        pass

    # Fetch race data
    race_results = session.results
    for driver in race_results["Abbreviation"]:
        driver_result = race_results[race_results["Abbreviation"] == driver]
        points = driver_result["Points"].iloc[0]  # Race points
        position = driver_result["Position"].iloc[0]

        # Add sprint race points if applicable
        if sprint_session is not None:
            sprint_results = sprint_session.results
            if driver in sprint_results["Abbreviation"].values:
                sprint_position = sprint_results[
                    sprint_results["Abbreviation"] == driver
                ]["Position"].iloc[0]
                sprint_points = SPRINT_POINTS.get(sprint_position, 0)
            else:
                sprint_points = 0
        else:
            sprint_points = 0

        standings.append(
            {
                "Race": race_name,
                "RoundNumber": round_number,
                "Driver": driver,
                "Points": points + sprint_points,  # Ignore fastest lap points
                "Position": position,
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
race_name_mapping = dict(zip(schedules["RoundNumber"], schedules["EventName"]))

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
fig.write_image(
    "../docs/_build/html/gen_modules/examples_gallery/temp-plot.png"
)
