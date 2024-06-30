from dataclasses import dataclass
from typing import Dict


class CompoundsConst:
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


@dataclass(frozen=True)
class TeamColorsConst:
    Official: str
    FastF1: str


@dataclass(frozen=True)
class TeamConst:
    ShortName: str
    TeamColor: TeamColorsConst


@dataclass(frozen=True)
class BaseSeasonConst:
    CompoundColors: Dict[str, str]
    Teams: Dict[str, TeamConst]
