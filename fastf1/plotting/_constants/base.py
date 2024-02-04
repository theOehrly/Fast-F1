from enum import Enum
from typing import Dict


class Colormaps(Enum):
    Classic = 'classic'
    Default = 'default'
    Official = 'official'


class Compounds(Enum):
    Soft = "SOFT"
    Medium = "MEDIUM"
    Hard = "HARD"
    Intermediate = "INTERMEDIATE"
    Wet = "WET"
    Unknown = "UNKNOWN"
    TestUnknown = "TEST-UNKNOWN"


class BaseSeason:
    Colormaps: Dict[Colormaps, dict]
    CompoundColors: Dict[Compounds, str]
    ShortTeamNames: Dict[str, str]
    Teams: Enum
