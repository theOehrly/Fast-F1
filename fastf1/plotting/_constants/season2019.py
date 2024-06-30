from typing import Dict

from fastf1.plotting._constants.base import (
    Compounds,
    Team,
    TeamColors
)


Teams: Dict[str, Team] = {
    'alfa romeo': Team(
        ShortName='Alfa Romeo',
        TeamColor=TeamColors(
            Official='#9b0000',
            FastF1='#900000'
        )
    ),
    'haas': Team(
        ShortName='Haas',
        TeamColor=TeamColors(
            Official='#bd9e57',
            FastF1='#bd9e57'
        )
    ),
    'ferrari': Team(
        ShortName='Ferrari',
        TeamColor=TeamColors(
            Official='#dc0000',
            FastF1='#da291c'
        )
    ),
    'mclaren': Team(
        ShortName='McLaren',
        TeamColor=TeamColors(
            Official='#ff8700',
            FastF1='#ff8000'
        )
    ),
    'mercedes': Team(
        ShortName='Mercedes',
        TeamColor=TeamColors(
            Official='#00d2be',
            FastF1='#00d2be'
        )
    ),
    'racing point': Team(
        ShortName='Racing Point',
        TeamColor=TeamColors(
            Official='#f596c8',
            FastF1='#ff87bc'
        )
    ),
    'red bull': Team(
        ShortName='Red Bull',
        TeamColor=TeamColors(
            Official='#1e41ff',
            FastF1='#1e41ff'
        )
    ),
    'renault': Team(
        ShortName='Renault',
        TeamColor=TeamColors(
            Official='#fff500',
            FastF1='#fff500'
        )
    ),
    'toro rosso': Team(
        ShortName='Toro Rosso',
        TeamColor=TeamColors(
            Official='#469bff',
            FastF1='#2b4562'
        )
    ),
    'williams': Team(
        ShortName='Williams',
        TeamColor=TeamColors(
            Official='#ffffff',
            FastF1='#00a0dd'
        )
    )
}

CompoundColors: Dict[Compounds, str] = {
    Compounds.Soft: "#da291c",
    Compounds.Medium: "#ffd12e",
    Compounds.Hard: "#f0f0ec",
    Compounds.Intermediate: "#43b02a",
    Compounds.Wet: "#0067ad",
    Compounds.Unknown: "#00ffff",
    Compounds.TestUnknown: "#434649"
}
