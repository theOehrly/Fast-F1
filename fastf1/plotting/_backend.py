import json
from importlib.resources import files

import fastf1._api
from fastf1.plotting._base import (
    Driver,
    SeasonConstants,
    Team,
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

    if year in Constants.keys():
        teams = {}
        for team_key, team_consts in Constants[year].teams.items():
            teams[team_key] = Team(
                normalized_name=team_key,
                short_name=team_consts.short_name,
                # copy required so that each team gets a separate copy of the
                # data per session, since data can be overwritten per session
                colors=team_consts.colors.model_copy()
            )

    else:
        # generate teams from API response, initialize empty for now
        teams = {}

    # Sorting by driver number here will directly guarantee that drivers
    # are sorted by driver number within each team. This has two advantages:
    # - the driver index in a team is consistent as long as the drivers don't
    #   change/reserver drivers are used/...
    # - the reigning champion (number 1) always has index 0, i.e. gets the
    #   primary style
    for num in sorted(driver_info.keys()):
        driver_entry = driver_info[num]
        team_name = driver_entry.get('TeamName')

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
        for team_key, team in teams.items():
            if team_key in normalized_full_team_name:
                team.name = team_name
                team.colors.official \
                    = f"#{driver_entry.get('TeamColour').lower()}"
                break
        else:
            # TODO improve
            # TODO maybe generate teams here?
            raise RuntimeError("Found no matching team.")

        driver = Driver(
            team=team,
            abbreviation=abbreviation,
            name=name,
            normalized_name=_normalize_string(name).lower(),
        )
        team.add_driver(driver)

    # return all teams that have drivers in this session
    return [team for team in teams.values() if team.drivers]
