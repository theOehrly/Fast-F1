import dataclasses

import fastf1._api
from fastf1.plotting._base import (
    _Driver,
    _logger,
    _normalize_string,
    _Team
)
from fastf1.plotting._constants import Constants


def _load_drivers_from_f1_livetiming(
        *, api_path: str, year: str
) -> list[_Team]:
    # load the driver information for the determined session
    driver_info = fastf1._api.driver_info(api_path)

    # parse the data into the required format
    teams: dict[str, _Team] = dict()

    # Sorting by driver number here will directly guarantee that drivers
    # are sorted by driver number within each team. This has two advantages:
    # - the driver index in a team is consistent as long as the drivers don't
    #   change/reserver drivers are used/...
    # - the reigning champion (number 1) always has index 0, i.e. gets the
    #   primary style
    for num in sorted(driver_info.keys()):
        driver_entry = driver_info[num]
        team_name = driver_entry.get('TeamName')

        if team_name in teams:
            team = teams[team_name]
        else:
            team = _Team()
            team.value = team_name

        abbreviation = driver_entry.get('Tla')

        name = ' '.join((driver_entry.get('FirstName'),
                         driver_entry.get('LastName')))
        driver = _Driver()
        driver.value = name
        driver.normalized_value = _normalize_string(name).lower()
        driver.abbreviation = abbreviation
        driver.team = team

        team.drivers.append(driver)

        if team not in teams:
            normalized_full_team_name = _normalize_string(team_name).lower()
            for ref_team_name, team_consts in Constants[year].Teams.items():
                if ref_team_name in normalized_full_team_name:
                    team.normalized_value = ref_team_name

                    # copy team constants, update the official color if it
                    # is available from the API and add the constants to the
                    # team
                    if team_color := driver_entry.get('TeamColour'):
                        replacements = {'Official': f"#{team_color}"}
                    else:
                        replacements = {}
                    colors = dataclasses.replace(
                        team_consts.TeamColor, **replacements
                    )
                    team.constants = dataclasses.replace(
                        team_consts, TeamColor=colors
                    )

                    break
            else:
                _logger.warning(f"Encountered unknown team '{team_name}' "
                                f"while loading driver-team mapping.")
                continue

            teams[team_name] = team

    return list(teams.values())
