from typing import Dict

from fastf1.plotting._constants.base import (
    Compounds,
    Team,
    TeamColors
)


Teams: Dict[str, Team] = {
    'ferrari': Team(
        ShortName='Ferrari',
        TeamColor=TeamColors(
            Official='#dc0000',
            FastF1='#dc0000'
        )
    ),
    'force india': Team(
        ShortName='Force India',
        TeamColor=TeamColors(
            Official='#f596c8',
            FastF1='#ff87bc'
        )
    ),
    'haas': Team(
        ShortName='Haas',
        TeamColor=TeamColors(
            Official='#828282',
            FastF1='#b6babd'
        )
    ),
    'mclaren': Team(
        ShortName='McLaren',
        TeamColor=TeamColors(
            Official='#ff8000',
            FastF1='#ff8000'
        )
    ),
    'mercedes': Team(
        ShortName='Mercedes',
        TeamColor=TeamColors(
            Official='#00d2be',
            FastF1='#00f5d0'
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
    'sauber': Team(
        ShortName='Sauber',
        TeamColor=TeamColors(
            Official='#9b0000',
            FastF1='#900000'
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
    Compounds.HyperSoft: "#feb1c1",
    Compounds.UltraSoft: "#b24ba7",
    Compounds.SuperSoft: "#fc2b2a",
    Compounds.Soft: "#ffd318",
    Compounds.Medium: "#f0f0f0",
    Compounds.Hard: "#00a2f5",
    Compounds.SuperHard: "#fd7d3c",
    Compounds.Intermediate: "#43b02a",
    Compounds.Wet: "#0067ad",
    Compounds.Unknown: "#00ffff",
    Compounds.TestUnknown: "#434649"
}
