import unicodedata

from fastf1.logger import get_logger
from fastf1.plotting._constants.base import TeamConst


_logger = get_logger(__package__)


class _Driver:
    value: str = ''
    normalized_value: str = ''
    abbreviation: str = ''
    team: "_Team"


class _Team:
    value: str = ''
    normalized_value: str = ''
    constants: TeamConst = None

    def __init__(self):
        super().__init__()
        self.drivers: list[_Driver] = list()


class _DriverTeamMapping:
    def __init__(
            self,
            year: str,
            teams: list[_Team],
    ):
        self.year = year
        self.teams = teams

        self.drivers_by_normalized: dict[str, _Driver] = dict()
        self.drivers_by_abbreviation: dict[str, _Driver] = dict()
        self.teams_by_normalized: dict[str, _Team] = dict()

        for team in teams:
            for driver in team.drivers:
                self.drivers_by_normalized[driver.normalized_value] = driver
                self.drivers_by_abbreviation[driver.abbreviation] = driver
            self.teams_by_normalized[team.normalized_value] = team


def _normalize_string(name: str) -> str:
    # removes accents from a string and returns the closest possible
    # ascii representation (https://stackoverflow.com/a/518232)
    stripped = ''.join(c for c in unicodedata.normalize('NFD', name)
                       if unicodedata.category(c) != 'Mn')
    return stripped
