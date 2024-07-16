from typing import Dict

from fastf1.plotting._constants.base import (
    CompoundsConst,
    TeamColorsConst,
    TeamConst
)


# NOTE: the team constants are copied when loading the driver-team-mapping
# and values may be modified there, it the used API provides different values


Teams: Dict[str, TeamConst] = {
    'alfa romeo': TeamConst(
        ShortName='Alfa Romeo',
        TeamColor=TeamColorsConst(
            Official='#C92D4B',
            FastF1='#900000'
        )
    ),
    'alphatauri': TeamConst(
        ShortName='AlphaTauri',
        TeamColor=TeamColorsConst(
            Official='#5E8FAA',
            FastF1='#2b4562'
        )
    ),
    'alpine': TeamConst(
        ShortName='Alpine',
        TeamColor=TeamColorsConst(
            Official='#2293D1',
            FastF1='#fe86bc'
        )
    ),
    'aston martin': TeamConst(
        ShortName='Aston Martin',
        TeamColor=TeamColorsConst(
            Official='#358C75',
            FastF1='#00665e'
        )
    ),
    'ferrari': TeamConst(
        ShortName='Ferrari',
        TeamColor=TeamColorsConst(
            Official='#F91536',
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
            Official='#F58020',
            FastF1='#ff8000'
        )
    ),
    'mercedes': TeamConst(
        ShortName='Mercedes',
        TeamColor=TeamColorsConst(
            Official='#6CD3BF',
            FastF1='#00f5d0'
        )
    ),
    'red bull': TeamConst(
        ShortName='Red Bull',
        TeamColor=TeamColorsConst(
            Official='#3671C6',
            FastF1='#0600ef'
        )
    ),
    'williams': TeamConst(
        ShortName='Williams',
        TeamColor=TeamColorsConst(
            Official='#37BEDD',
            FastF1='#00a0dd'
        )
    )
}

CompoundColors: Dict[CompoundsConst, str] = {
    CompoundsConst.Soft: "#da291c",
    CompoundsConst.Medium: "#ffd12e",
    CompoundsConst.Hard: "#f0f0ec",
    CompoundsConst.Intermediate: "#43b02a",
    CompoundsConst.Wet: "#0067ad",
    CompoundsConst.Unknown: "#00ffff",
    CompoundsConst.TestUnknown: "#434649"
}
