"""Interactive graph for laptimes
=================================

Plot an interactive graph showing laptimes for each driver lap by lap.
"""

import fastf1
import fastf1.plotting
import plotly.graph_objects as go

# load a session
race = fastf1.get_session(2023, 'Abu Dhabi', 'R')
race.load(weather=False, telemetry=False)

# Get the list of drivers
driver_list = list(fastf1.plotting.DRIVER_TRANSLATE.keys())

# Set the colors for the graph: for drivers, we use the combination of both
# DRIVER_TRANSLATE and DRIVER_COLORS to associate colors with driver's initials
driver_colors = {
    key:fastf1.plotting.DRIVER_COLORS[value] 
    for key, value in fastf1.plotting.DRIVER_TRANSLATE.items()
    }

# Set the colors of each tyre
compound_colors = fastf1.plotting.COMPOUND_COLORS

# Set titles and labels of the graph
title = "2023 Abu Dhabi Grand Prix Laptime Evolution"
xaxis_title = "Lap Number"
yaxis_title = "Lap Time (s)"
legend_title = "Driver"

# Define the limits of the graph:
# As we are going to show a representation of the whole race, there are
# some laps that are considerably slower than the average. We want to keep them
# in the graph but we don't need to see them, so we're focusing our view in the
# relevant ones. For this reason, we're picking the fastest lap and the
# slowest lap of the quick laps and we're defining a margin of 0'5 for the
# limits of the graph.
quicklaps = race.laps.pick_quicklaps()
quicklaps['LapTime(s)'] = quicklaps['LapTime'].dt.total_seconds()

fastest_lap = quicklaps['LapTime(s)'].min()
min_range_y = fastest_lap - 0.5

slowest_quicklap = quicklaps['LapTime(s)'].max()
max_range_y = slowest_quicklap + 0.5

# Also, we have to define the number of laps for getting a nice x axis.
# We're picking 0 for start and last lap number plus 1
howmany_laps = race.laps['LapNumber'].max()
max_range_x = howmany_laps + 1

# Here we're defining a nice template to show the graph:
custom_template = go.layout.Template({
    'layout': {
        'width': 1200,
        'height': 600,
        'title': {
            'font': {
                'family': 'Arial Bold, sans-serif',
                'color': '#ffffff',
                'size': 24
            }
        },
        'hovermode': 'x',
        'font': {
            'family': 'Arial Bold, sans-serif',
            'color': '#ffffff'
        },
        'paper_bgcolor': '#222222',
        'plot_bgcolor': '#222222',
        'xaxis': {
            'title': {
                'font': {
                    'family': 'Arial Bold, sans-serif',
                    'color': '#ffffff',
                    'size': 18
                }
            },
            'gridcolor': None,
            'range': [1, 59],
        },
        'yaxis': {
            'title': {
                'font': {
                    'family': 'Arial Bold, sans-serif',
                    'color': '#ffffff',
                    'size': 18
                }
            },
            'gridcolor': 'grey',
            'gridwidth': 1,
            'dtick': 1,
            'griddash': 'dot',
            'range': [86.5, 94],
        },
        'legend': {
            'title': {
                'font': {
                    'family': 'Arial Bold, sans-serif',
                    'color': '#ffffff',
                    'size': 14
                }
            },
            'x': 1,
            'y': 1,
            'traceorder': 'normal',
            'orientation': 'v'
        }
    }
})


# PLOT THE GRAPH #
fig = go.Figure()

# As we're plotting every driver laptime, is better to use a dynamic method to plot
# each graph. We use the driver list we got before.
for driver in driver_list:
    driver_laps = race.laps.pick_drivers(driver) # pick all laps
    driver_laps = driver_laps.reset_index() # clean index from race.laps
    driver_laps['LapTime(s)'] = driver_laps['LapTime'].dt.total_seconds() # convert to number each laptime
    scatter = go.Scatter(
        x=driver_laps['LapNumber'], 
        y=driver_laps['LapTime(s)'],
        mode='lines+markers', # use lines and scatters for each driver
        name=driver,
        marker=dict(color=driver_laps['Compound'].map(compound_colors)), # use compound colors for scatters
        line=dict(color=driver_colors[driver]), # use driver assigned colors
    )
    fig.add_trace(scatter) # show the trace

# After building the graph, apply the template and titles to the graph
fig.update_layout(template=custom_template)
fig.update_layout(dict(
    title=title,
    xaxis_title=xaxis_title,
    yaxis_title=yaxis_title,
    legend_title=legend_title
    ))

# Fit the graph to a nice view
fig.update_yaxes(range=[min_range_y, max_range_y])
fig.update_xaxes(range=[0, max_range_x])

fig.show()