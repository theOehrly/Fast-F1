from enum import Enum
from typing import (
    Dict,
    Sequence
)

from fastf1.plotting._constants.base import (
    BaseSeason,
    Colormaps,
    Compounds
)


class Teams(Enum):
    Mercedes = 'mercedes'
    Ferrari = 'ferrari'
    RedBull = 'red bull'
    McLaren = 'mclaren'
    Alpine = 'alpine'
    AstonMartin = 'aston martin'
    AlfaRomeo = 'alfa romeo'
    AlphaTauri = 'alphatauri'
    Haas = 'haas'
    Williams = 'williams'


ShortTeamNames: Dict[Teams, str] = {
    Teams.Mercedes: 'Mercedes',
    Teams.Ferrari: 'Ferrari',
    Teams.RedBull: 'Red Bull',
    Teams.McLaren: 'McLaren',
    Teams.Alpine: 'Alpine',
    Teams.AstonMartin: 'Aston',
    Teams.AlfaRomeo: 'Alfa Romeo',
    Teams.AlphaTauri: 'AlphaTauri',
    Teams.Haas: 'Haas',
    Teams.Williams: 'Williams'
}


TeamColormaps: Dict[Colormaps, Dict[Teams, Sequence[str]]] = {
    Colormaps.Classic: {
        Teams.Mercedes: ['#00d2be', ],
        Teams.Ferrari: ['#dc0000', ],
        Teams.RedBull: ['#0600ef', ],
        Teams.McLaren: ['#ff8700', ],
        Teams.Alpine: ['#0090ff', ],
        Teams.AstonMartin: ['#006f62', ],
        Teams.AlfaRomeo: ['#900000', ],
        Teams.AlphaTauri: ['#2b4562', ],
        Teams.Haas: ['#ffffff', ],
        Teams.Williams: ['#005aff', ]
    },
    Colormaps.Official: {
        Teams.Mercedes: ['#6CD3BF', ],
        Teams.Ferrari: ['#F91536', ],
        Teams.RedBull: ['#3671C6', ],
        Teams.McLaren: ['#F58020', ],
        Teams.Alpine: ['#2293D1', ],
        Teams.AstonMartin: ['#358C75', ],
        Teams.AlfaRomeo: ['#900000', ],
        Teams.AlphaTauri: ['#5E8FAA', ],
        Teams.Haas: ['#B6BABD', ],
        Teams.Williams: ['#37BEDD', ]
    },
    Colormaps.Default: {
        Teams.Mercedes: ['#00f5d0', '#a8fff2'],
        Teams.Ferrari: ['#da291c', '#e84d40'],
        Teams.RedBull: ['#fcd700', '#ffec7b'],
        Teams.McLaren: ['#ff8000', '#9d4d00'],
        Teams.Alpine: ['#fe86bc', '#ff117c'],
        Teams.AstonMartin: ['#00665e', '#00413b'],
        Teams.AlfaRomeo: ['#900000', '#5f0000'],
        Teams.AlphaTauri: ['#2b4562', '#406991'],
        Teams.Haas: ['#ffffff', '#a7a7a7'],
        Teams.Williams: ['#00a0dd', '#8cc8ff']
    }
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


class Season2023(BaseSeason):
    Colormaps = TeamColormaps
    CompoundColors = CompoundColors
    ShortTeamNames = ShortTeamNames
    Teams = Teams
