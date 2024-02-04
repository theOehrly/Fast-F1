from dataclasses import dataclass
from typing import Dict


class Compounds:
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
class TeamColors:
    Official: str
    Default: str


@dataclass(frozen=True)
class Team:
    ShortName: str
    TeamColor: TeamColors


@dataclass(frozen=True)
class BaseSeason:
    CompoundColors: Dict[str, str]
    Teams: Dict[str, Team]
