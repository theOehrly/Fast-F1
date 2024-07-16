
from fastf1.plotting._constants.base import (
    CompoundsConst,
    TeamColorsConst,
    TeamConst
)


# NOTE: the team constants are copied when loading the driver-team-mapping
# and values may be modified there, it the used API provides different values


Teams: dict[str, TeamConst] = {
    'ferrari': TeamConst(
        ShortName='Ferrari',
        TeamColor=TeamColorsConst(
            Official='#dc0000',
            FastF1='#dc0000'
        )
    ),
    'force india': TeamConst(
        ShortName='Force India',
        TeamColor=TeamColorsConst(
            Official='#f596c8',
            FastF1='#ff87bc'
        )
    ),
    'haas': TeamConst(
        ShortName='Haas',
        TeamColor=TeamColorsConst(
            Official='#828282',
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
            Official='#00d2be',
            FastF1='#00f5d0'
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
    'sauber': TeamConst(
        ShortName='Sauber',
        TeamColor=TeamColorsConst(
            Official='#9b0000',
            FastF1='#900000'
        )
    ),
    'toro rosso': TeamConst(
        ShortName='Toro Rosso',
        TeamColor=TeamColorsConst(
            Official='#469bff',
            FastF1='#2b4562'
        )
    ),
    'williams': TeamConst(
        ShortName='Williams',
        TeamColor=TeamColorsConst(
            Official='#ffffff',
            FastF1='#00a0dd'
        )
    )
}

CompoundColors: dict[CompoundsConst, str] = {
    CompoundsConst.HyperSoft: "#feb1c1",
    CompoundsConst.UltraSoft: "#b24ba7",
    CompoundsConst.SuperSoft: "#fc2b2a",
    CompoundsConst.Soft: "#ffd318",
    CompoundsConst.Medium: "#f0f0f0",
    CompoundsConst.Hard: "#00a2f5",
    CompoundsConst.SuperHard: "#fd7d3c",
    CompoundsConst.Intermediate: "#43b02a",
    CompoundsConst.Wet: "#0067ad",
    CompoundsConst.Unknown: "#00ffff",
    CompoundsConst.TestUnknown: "#434649"
}
