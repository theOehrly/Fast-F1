from typing import Dict

from fastf1.plotting._constants.base import (
    Compounds,
    Team,
    TeamColors
)


Teams: Dict[str, Team] = {
    'alpine': Team(
        ShortName='Alpine',
        TeamColor=TeamColors(
            Official='#0093cc',
            Default='#ff87bc'
        )
    ),
    'aston martin': Team(
        ShortName='Aston Martin',
        TeamColor=TeamColors(
            Official='#229971',
            Default='#00665f'
        )
    ),
    'ferrari': Team(
        ShortName='Ferrari',
        TeamColor=TeamColors(
            Official='#e8002d',
            Default='#e8002d'
        )
    ),
    'haas': Team(
        ShortName='Haas',
        TeamColor=TeamColors(
            Official='#b6babd',
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
            Official='#27f4d2',
            Default='#27f4d2'
        )
    ),
    'rb': Team(
        ShortName='RB',
        TeamColor=TeamColors(
            Official='#6692ff',
            Default='#364aa9'
        )
    ),
    'red bull': Team(
        ShortName='Red Bull',
        TeamColor=TeamColors(
            Official='#3671c6',
            Default='#0600ef'
        )
    ),
    'sauber': Team(
        ShortName='Sauber',
        TeamColor=TeamColors(
            Official='#52e252',
            Default='#00e700'
        )
    ),
    'williams': Team(
        ShortName='Williams',
        TeamColor=TeamColors(
            Official='#64c4ff',
            Default='#00a0dd'
        )
    )
}

# TODO: future proofing?
CompoundColors: Dict[Compounds, str] = {
    Compounds.Soft: "#da291c",
    Compounds.Medium: "#ffd12e",
    Compounds.Hard: "#f0f0ec",
    Compounds.Intermediate: "#43b02a",
    Compounds.Wet: "#0067ad",
    Compounds.Unknown: "#00ffff",
    Compounds.TestUnknown: "#434649"
}
