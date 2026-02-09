import re
import unicodedata
from enum import Enum
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    model_validator
)

from fastf1.logger import get_logger


_logger = get_logger(__package__)


class CompoundTypes(Enum):
    HyperSoft = "HYPERSOFT"
    UltraSoft = "ULTRASOFT"
    SuperSoft = "SUPERSOFT"
    Soft = "SOFT"
    Medium = "MEDIUM"
    Hard = "HARD"
    SuperHard = "SUPERHARD"
    Intermediate = "INTERMEDIATE"
    Wet = "WET"
    Unknown = "UNKNOWN"
    TestUnknown = "TEST-UNKNOWN"


HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-f]{6}|[0-9a-f]{8})$")

def hex_color_validator(s: str):
    # ensure that a string is a lower case hex color, alpha is optional
    if not HEX_COLOR_PATTERN.match(s):
        raise ValueError(f"Invalid hex color: {s} "
                         f"(must be lowercase, six or eight digits)")
    return s

def color_dict_validator(d: dict):
    # ensure that a dictionary only contains lower case hex color values,
    # with an optional alpha channel
    for v in d.values():
        if not HEX_COLOR_PATTERN.match(v):
            raise ValueError(f"Invalid hex color: {v} "
                             f"(must be lowercase, six or eight digits)")
    return d

def team_key_validator(d: dict[str, "TeamConstants"]):
    # ensure that team keys only contain lower case letters and spaces
    for k, v in d.items():
        if not k.replace(" ", "").isalpha():
            raise ValueError(
                f"Invalid team key: {k} (only letters and spaces allowed)"
            )
        if not k.islower():
            raise ValueError(f"Invalid team key: {k} (must be lower case)")
    return d


# ### models for built-in constants
# The constants values are deserialized from constants.json using pydantic

class TeamColorConstants(BaseModel):
    official: Annotated[
        str,
        AfterValidator(hex_color_validator)
    ]
    fastf1: Annotated[
        str,
        AfterValidator(hex_color_validator)
    ]


class TeamConstants(BaseModel):
    short_name: str
    colors: TeamColorConstants


class SeasonConstants(BaseModel):
    compound_colors: Annotated[
        dict[CompoundTypes, str],
        AfterValidator(color_dict_validator)
    ]
    teams: Annotated[
        dict[str, TeamConstants],
        AfterValidator(team_key_validator)
    ]


# ### models for full driver and team data
# These models are partially filled from constants and partially from API data

class Team(TeamConstants):
    name: str = ''
    normalized_name: str = ''
    drivers: list["Driver"] = []

    def add_driver(self, driver: "Driver"):
        if driver in self.drivers:
            raise ValueError(f"Driver {driver} already exists")
        self.drivers.append(driver)


class Driver(BaseModel):
    team: Team
    abbreviation: str = ''
    name: str = ''
    normalized_name: str = ''

    @model_validator(mode="after")
    def ensure_unique(self):
        for driver in self.team.drivers:
            if driver.abbreviation == self.abbreviation:
                raise ValueError(f"Duplicate driver: {driver.abbreviation}")
        return self


class DriverTeamMapping(BaseModel):
    year: str
    teams: list[Team]

    drivers_by_normalized: dict[str, Driver] = dict()
    drivers_by_abbreviation: dict[str, Driver] = dict()
    teams_by_normalized: dict[str, Team] = dict()

    def model_post_init(self, *args):
        super().model_post_init(*args)

        for team in self.teams:
            for driver in team.drivers:
                self.drivers_by_normalized[driver.normalized_name] = driver
                self.drivers_by_abbreviation[driver.abbreviation] = driver
            self.teams_by_normalized[team.normalized_name] = team


def _normalize_string(name: str) -> str:
    # removes accents from a string and returns the closest possible
    # ascii representation (https://stackoverflow.com/a/518232)
    stripped = ''.join(c for c in unicodedata.normalize('NFD', name)
                       if unicodedata.category(c) != 'Mn')
    return stripped
