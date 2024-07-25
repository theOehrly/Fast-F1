
from fastf1.plotting._constants.base import (
    CompoundsConst,
    TeamColorsConst,
    TeamConst
)


# NOTE: the team constants are copied when loading the driver-team-mapping
# and values may be modified there, if the used API provides different values


Teams: dict[str, TeamConst] = {
    'alpine': TeamConst(
        ShortName='Alpine',
        TeamColor=TeamColorsConst(
            Official='#0093cc',
            FastF1='#ff87bc'
        )
    ),
    'aston martin': TeamConst(
        ShortName='Aston Martin',
        TeamColor=TeamColorsConst(
            Official='#229971',
            FastF1='#00665f'
        )
    ),
    'ferrari': TeamConst(
        ShortName='Ferrari',
        TeamColor=TeamColorsConst(
            Official='#e8002d',
            FastF1='#e8002d'
        )
    ),
    'haas': TeamConst(
        ShortName='Haas',
        TeamColor=TeamColorsConst(
            Official='#b6babd',
            FastF1='#b6babd'
        )
    ),
    'mclaren': TeamConst(
        ShortName='McLaren',
        TeamColor=TeamColorsConst(
            Official='#ff8000',
            FastF1='#ff8000'
        )
    ),
    'mercedes': TeamConst(
        ShortName='Mercedes',
        TeamColor=TeamColorsConst(
            Official='#27f4d2',
            FastF1='#27f4d2'
        )
    ),
    'rb': TeamConst(
        ShortName='RB',
        TeamColor=TeamColorsConst(
            Official='#6692ff',
            FastF1='#364aa9'
        )
    ),
    'red bull': TeamConst(
        ShortName='Red Bull',
        TeamColor=TeamColorsConst(
            Official='#3671c6',
            FastF1='#0600ef'
        )
    ),
    'kick sauber': TeamConst(
        ShortName='Sauber',
        TeamColor=TeamColorsConst(
            Official='#52e252',
            FastF1='#00e700'
        )
    ),
    'williams': TeamConst(
        ShortName='Williams',
        TeamColor=TeamColorsConst(
            Official='#64c4ff',
            FastF1='#00a0dd'
        )
    )
}

CompoundColors: dict[CompoundsConst, str] = {
    CompoundsConst.Soft: "#da291c",
    CompoundsConst.Medium: "#ffd12e",
    CompoundsConst.Hard: "#f0f0ec",
    CompoundsConst.Intermediate: "#43b02a",
    CompoundsConst.Wet: "#0067ad",
    CompoundsConst.Unknown: "#00ffff",
    CompoundsConst.TestUnknown: "#434649"
}
