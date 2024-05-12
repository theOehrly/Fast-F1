import warnings
from typing import (
    Dict,
    List
)

import fastf1._api
from fastf1.plotting._base import (
    _Driver,
    _normalize_string,
    _Team
)
from fastf1.plotting._constants import Constants


def _load_drivers_from_f1_livetiming(
        *, api_path: str, year: str
) -> List[_Team]:
    # load the driver information for the determined session
    driver_info = fastf1._api.driver_info(api_path)

    # parse the data into the required format
    teams: Dict[str, _Team] = dict()

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
            for ref_team_name in Constants[year].Teams.keys():
                if ref_team_name in normalized_full_team_name:
                    team.normalized_value = ref_team_name
                    break
            else:
                warnings.warn(f"Encountered unknown team '{team_name}' while "
                              f"loading driver-team mapping.",
                              UserWarning)
                continue

            teams[team_name] = team

    return list(teams.values())
