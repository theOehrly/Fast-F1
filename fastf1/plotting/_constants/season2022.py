
from fastf1.plotting._constants.base import (
    CompoundsConst,
    TeamColorsConst,
    TeamConst
)


# NOTE: the team constants are copied when loading the driver-team-mapping
# and values may be modified there, it the used API provides different values


Teams: dict[str, TeamConst] = {
    'alfa romeo': TeamConst(
        ShortName='Alfa Romeo',
        TeamColor=TeamColorsConst(
            Official='#b12039',
            FastF1='#900000'
        )
    ),
    'alphatauri': TeamConst(
        ShortName='AlphaTauri',
        TeamColor=TeamColorsConst(
            Official='#4e7c9b',
            FastF1='#2b4562'
        )
    ),
    'alpine': TeamConst(
        ShortName='Alpine',
        TeamColor=TeamColorsConst(
            Official='#2293d1',
            FastF1='#fe86bc'
        )
    ),
    'aston martin': TeamConst(
        ShortName='Aston Martin',
        TeamColor=TeamColorsConst(
            Official='#2d826d',
            FastF1='#00665e'
        )
    ),
    'ferrari': TeamConst(
        ShortName='Ferrari',
        TeamColor=TeamColorsConst(
            Official='#ed1c24',
            FastF1='#da291c'
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
            Official='#f58020',
            FastF1='#ff8000'
        )
    ),
    'mercedes': TeamConst(
        ShortName='Mercedes',
        TeamColor=TeamColorsConst(
            Official='#6cd3bf',
            FastF1='#00f5d0'
        )
    ),
    'red bull': TeamConst(
        ShortName='Red Bull',
        TeamColor=TeamColorsConst(
            Official='#1e5bc6',
            FastF1='#0600ef'
        )
    ),
    'williams': TeamConst(
        ShortName='Williams',
        TeamColor=TeamColorsConst(
            Official='#37bedd',
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
