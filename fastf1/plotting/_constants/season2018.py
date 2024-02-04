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
            Default='#dc0000'
        )
    ),
    'force india': Team(
        ShortName='Force India',
        TeamColor=TeamColors(
            Official='#f596c8',
            Default='#ff87bc'
        )
    ),
    'haas': Team(
        ShortName='Haas',
        TeamColor=TeamColors(
            Official='#828282',
            Default='#b6babd'
        )
    ),
    'mclaren': Team(
        ShortName='McLaren',
        TeamColor=TeamColors(
            Official='#ff8000',
            Default='#ff8000'
        )
    ),
    'mercedes': Team(
        ShortName='Mercedes',
        TeamColor=TeamColors(
            Official='#00d2be',
            Default='#00f5d0'
        )
    ),
    'racing point': Team(
        ShortName='Racing Point',
        TeamColor=TeamColors(
            Official='#f596c8',
            Default='#ff87bc'
        )
    ),
    'red bull': Team(
        ShortName='Red Bull',
        TeamColor=TeamColors(
            Official='#1e41ff',
            Default='#1e41ff'
        )
    ),
    'renault': Team(
        ShortName='Renault',
        TeamColor=TeamColors(
            Official='#fff500',
            Default='#fff500'
        )
    ),
    'sauber': Team(
        ShortName='Sauber',
        TeamColor=TeamColors(
            Official='#9b0000',
            Default='#900000'
        )
    ),
    'toro rosso': Team(
        ShortName='Toro Rosso',
        TeamColor=TeamColors(
            Official='#469bff',
            Default='#2b4562'
        )
    ),
    'williams': Team(
        ShortName='Williams',
        TeamColor=TeamColors(
            Official='#ffffff',
            Default='#00a0dd'
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
