"""Who can still win the drivers WDC?
======================================

Calculates which drivers still has chance to win the WDC.
Simplified since it doesn't compare positions if points are equal.

This example implements 3 functions that it then uses to calculate
it's result.
"""

import requests

import fastf1

fastf1.Cache.enable_cache("../doc_cache")  # replace with your cache directory


##############################################################################
# We need a function to get the current driver standings from
# Ergast and returns as list of drivers.
# Reference https://ergast.com/mrd/methods/standings/
def get_drivers_standings():
    url = "https://ergast.com/api/f1/current/driverStandings.json"
    response = requests.get(url)
    data = response.json()
    drivers_standings = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']  # noqa: E501
    return drivers_standings


##############################################################################
# We need a function to calculates the maximum amount of points possible if a
# driver wins everything left of the season.
# https://en.wikipedia.org/wiki/List_of_Formula_One_World_Championship_points_scoring_systems
def calculate_max_points_for_remaining_season():
    POINTS_FOR_SPRINT = 8 + 25 + 1  # Winning the sprint, race and fastest lap
    POINTS_FOR_CONVENTIONAL = 25 + 1  # Winning the race and fastest lap

    events = fastf1.events.get_events_remaining()
    # Count how many sprints and conventional races are left
    sprint_events = \
        len(events.loc[events["EventFormat"] == "sprint"])
    conventional_events = \
        len(events.loc[events["EventFormat"] == "conventional"])

    # Calculate points for each
    sprint_points = sprint_events * POINTS_FOR_SPRINT
    conventional_points = conventional_events * POINTS_FOR_CONVENTIONAL

    return sprint_points + conventional_points


##############################################################################
# For each driver we will see if there is a chance to get more points than
# the current leader. We assume the leader gets no more points and the
# driver gets the theoretical maximum amount of points.
#
# We currently don't consider the case of two drivers getting equal points
# since its more complicated and would require comparing positions.
def calculate_who_can_win(driver_standings, max_points):
    LEADER_POINTS = int(driver_standings[0]['points'])

    for _, driver in enumerate(driver_standings):
        driver_max_points = int(driver["points"]) + max_points
        can_win = 'No' if driver_max_points < LEADER_POINTS else 'Yes'

        print(f"{driver['position']}: \
{driver['Driver']['code']}, \
Current points: {driver['points']}, \
Theoretical max points: {driver_max_points}, \
Can win: {can_win}")


##############################################################################
# Now using the 3 functions above we can use them to calculate who
# can still win.

# Get the current drivers standings
driver_standings = get_drivers_standings()

# Get the maximum amount of points
points = calculate_max_points_for_remaining_season()

# Print which drivers can still win
calculate_who_can_win(driver_standings, points)
