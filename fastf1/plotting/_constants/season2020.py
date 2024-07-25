
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
            Official='#9B0000',
            FastF1='#900000'
        )
    ),
    'alphatauri': TeamConst(
        ShortName='AlphaTauri',
        TeamColor=TeamColorsConst(
            Official='#ffffff',
            FastF1='#2b4562'
        )
    ),
    'ferrari': TeamConst(
        ShortName='Ferrari',
        TeamColor=TeamColorsConst(
            Official='#dc0000',
            FastF1='#dc0000'
        )
    ),
    'haas': TeamConst(
        ShortName='Haas',
        TeamColor=TeamColorsConst(
            Official='#787878',
            FastF1='#b6babd'
        )
    ),
    'mclaren': TeamConst(
        ShortName='McLaren',
        TeamColor=TeamColorsConst(
            Official='#ff8700',
            FastF1='#ff8000'
        )
    ),
    'mercedes': TeamConst(
        ShortName='Mercedes',
        TeamColor=TeamColorsConst(
            Official='#00d2be',
            FastF1='#00d2be'
        )
    ),
    'racing point': TeamConst(
        ShortName='Racing Point',
        TeamColor=TeamColorsConst(
            Official='#f596c8',
            FastF1='#ff87bc'
        )
    ),
    'red bull': TeamConst(
        ShortName='Red Bull',
        TeamColor=TeamColorsConst(
            Official='#1e41ff',
            FastF1='#1e41ff'
        )
    ),
    'renault': TeamConst(
        ShortName='Renault',
        TeamColor=TeamColorsConst(
            Official='#fff500',
            FastF1='#fff500'
        )
    ),
    'williams': TeamConst(
        ShortName='Williams',
        TeamColor=TeamColorsConst(
            Official='#0082fa',
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
