
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
            Official='#900000',
            FastF1='#900000'
        )
    ),
    'alphatauri': TeamConst(
        ShortName='AlphaTauri',
        TeamColor=TeamColorsConst(
            Official='#2b4562',
            FastF1='#2b4562'
        )
    ),
    'alpine': TeamConst(
        ShortName='Alpine',
        TeamColor=TeamColorsConst(
            Official='#0090ff',
            FastF1='#0755ab'
        )
    ),
    'aston martin': TeamConst(
        ShortName='Aston Martin',
        TeamColor=TeamColorsConst(
            Official='#006f62',
            FastF1='#00665e'
        )
    ),
    'ferrari': TeamConst(
        ShortName='Ferrari',
        TeamColor=TeamColorsConst(
            Official='#dc0004',
            FastF1='#dc0004'
        )
    ),
    'haas': TeamConst(
        ShortName='Haas',
        TeamColor=TeamColorsConst(
            Official='#ffffff',
            FastF1='#b6babd'
        )
    ),
    'mclaren': TeamConst(
        ShortName='McLaren',
        TeamColor=TeamColorsConst(
            Official='#ff9800',
            FastF1='#ff8000'
        )
    ),
    'mercedes': TeamConst(
        ShortName='Mercedes',
        TeamColor=TeamColorsConst(
            Official='#00d2be',
            FastF1='#00f5d0'
        )
    ),
    'red bull': TeamConst(
        ShortName='Red Bull',
        TeamColor=TeamColorsConst(
            Official='#0600ef',
            FastF1='#0600ef'
        )
    ),
    'williams': TeamConst(
        ShortName='Williams',
        TeamColor=TeamColorsConst(
            Official='#005aff',
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
