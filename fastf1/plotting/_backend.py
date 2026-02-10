import json
import warnings
from importlib.resources import files

import fastf1._api
from fastf1.plotting._base import (
    Driver,
    SeasonConstants,
    Team,
    TeamColorConstants,
    _logger,
    _normalize_string
)


Constants: dict[str, SeasonConstants] = dict()

json_path = files("fastf1.plotting").joinpath("constants.json")
content = json_path.read_text(encoding="utf-8")

for year, consts in json.loads(content).items():
    Constants[year] = SeasonConstants(**consts)


def _load_drivers_from_f1_livetiming(
        *,
        api_path: str,
        year: str
) -> list[Team]:

    # load the driver information for the determined session
    driver_info = fastf1._api.driver_info(api_path)

    teams = {}
    if year in Constants.keys():
        # pre-populate teams from constants if the year is supported
        for normalized_name, team_consts in Constants[year].teams.items():
            teams[normalized_name] = Team(
                normalized_name=normalized_name,
                short_name=team_consts.short_name,
                # copy required so that each team gets a separate copy of the
                # data per session, since data can be overwritten per session
                colors=team_consts.colors.model_copy()
            )
    else:
        warnings.warn(
            f"No built-in team name/color constants for {year}. "
            f"Update FastF1 for official values. "
            f"Using auto-generated names/colors (may be inaccurate). "
            f"All color schemes will follow the 'official' scheme."
        )

    # Sorting by driver number here will directly guarantee that drivers
    # are sorted by driver number within each team. This has two advantages:
    # - the driver index in a team is consistent as long as the drivers don't
    #   change/reserver drivers are used/...
    # - the reigning champion (number 1) always has index 0, i.e. gets the
    #   primary style
    for num in sorted(driver_info.keys()):
        driver_entry = driver_info[num]
        team_name = driver_entry.get('TeamName')
        team_color = f"#{driver_entry.get('TeamColour').lower()}"
        abbreviation = driver_entry.get('Tla', '')
        name = ' '.join((driver_entry.get('FirstName', ''),
                         driver_entry.get('LastName', '')))

        if not abbreviation.strip() or not name.strip():
            _logger.warning(
                "Skipping driver with incomplete data while generating "
                "driver-team mapping for plotting constants."
            )
            _logger.debug(f"Skipping driver entry: {driver_entry}")
            continue

        normalized_full_team_name = _normalize_string(team_name).lower()
        for normalized_name, team in teams.items():
            if normalized_name in normalized_full_team_name:
                team.name = team_name
                team.colors.official = team_color
                break
        else:
            team = _generate_team(team_name, team_color)

            _logger.warning(f"Auto-generating unknown team: {team.name}")

            teams[team.normalized_name] = team

        driver = Driver(
            team=team,
            abbreviation=abbreviation,
            name=name,
            normalized_name=_normalize_string(name).lower(),
        )
        team.add_driver(driver)

    # return all teams that have drivers in this session
    return [team for team in teams.values() if team.drivers]


def _generate_team(team_name: str, team_color: str) -> Team:
    # try to generate team and constants from available information
    # this may not be perfect

    short_team_name = (_normalize_string(team_name)
                       .replace('Team', '')
                       .replace('F1', '')
                       .replace('Scuderia', '')
                       )
    if not short_team_name.startswith("Racing"):
        # special case to keep "Racing Bulls" unmodified
        short_team_name = short_team_name.replace('Racing', '')

    # remove leading and trailing spaces
    short_team_name = short_team_name.strip().lstrip()

    # remove double space characters
    while "  " in short_team_name:
        short_team_name = short_team_name.replace("  ", " ")

    normalized_name = short_team_name.lower()

    team_colors = TeamColorConstants(
        official=team_color,
        fastf1=team_color,
    )
    team = Team(
        name=team_name,
        normalized_name=normalized_name,
        short_name=short_team_name,
        colors=team_colors
    )

    return team
