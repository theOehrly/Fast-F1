from typing import (
    Dict,
    Type
)

from fastf1.plotting._constants.base import (
    BaseSeason,
    Colormaps
)
from fastf1.plotting._constants.season2023 import Season2023
from fastf1.plotting._constants.season2024 import Season2024


# Deprecated, will be removed for 2025
LEGACY_TEAM_TRANSLATE: Dict[str, str] = {
    'MER': 'mercedes',
    'FER': 'ferrari',
    'RBR': 'red bull',
    'MCL': 'mclaren',
    'APN': 'alpine',
    'AMR': 'aston martin',
    'SAU': 'sauber',
    'VIS': 'visa',  # TODO: update
    'HAA': 'haas',
    'WIL': 'williams'
}


Constants: Dict[str, Type[BaseSeason]] = {
    '2023': Season2023,
    '2024': Season2024
}

