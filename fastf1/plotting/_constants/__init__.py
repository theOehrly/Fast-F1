from fastf1.plotting._constants import (  # noqa: F401, unused import used through globals()
    season2018,
    season2019,
    season2020,
    season2021,
    season2022,
    season2023,
    season2024
)
from fastf1.plotting._constants.base import BaseSeasonConst


Constants: dict[str, BaseSeasonConst] = dict()

for year in range(2018, 2025):
    season = globals()[f"season{year}"]
    Constants[str(year)] = BaseSeasonConst(
        CompoundColors=season.CompoundColors,
        Teams=season.Teams
    )


# Deprecated, will be removed for 2025
LEGACY_TEAM_COLORS = {
    'mercedes': '#00d2be', 'ferrari': '#dc0000',
    'red bull': '#fcd700', 'mclaren': '#ff8700',
    'alpine': '#fe86bc', 'aston martin': '#006f62',
    'sauber': '#00e701', 'visa rb': '#1634cb',
    'haas': '#ffffff', 'williams': '#00a0dd'
}


LEGACY_TEAM_TRANSLATE: dict[str, str] = {
    'MER': 'mercedes',
    'FER': 'ferrari',
    'RBR': 'red bull',
    'MCL': 'mclaren',
    'APN': 'alpine',
    'AMR': 'aston martin',
    'SAU': 'sauber',
    'RB': 'rb',
    'HAA': 'haas',
    'WIL': 'williams'
}


LEGACY_DRIVER_COLORS: dict[str, str] = {
    "valtteri bottas": "#00e701",
    "zhou guanyu": "#008d01",
    "theo pourchaire": "#004601",

    "nyck de vries": "#1e3d61",
    "yuki tsunoda": "#356cac",
    "daniel ricciardo": "#2b4562",
    "liam lawson": "#2b4562",
    "isack hadjar": "#1e6176",
    "ayumu iwasa": "#1e6176",

    "pierre gasly": "#fe86bc",
    "esteban ocon": "#ff117c",
    "jack doohan": "#894667",

    "fernando alonso": "#006f62",
    "lance stroll": "#00413b",
    "felipe drugovich": "#2f9b90",

    "charles leclerc": "#dc0000",
    "carlos sainz": "#ff8181",
    "robert shwartzman": "#9c0000",
    "oliver bearman": "#c40000",

    "kevin magnussen": "#ffffff",
    "nico hulkenberg": "#cacaca",

    "oscar piastri": "#ff8700",
    "lando norris": "#eeb370",
    "pato oward": "#ee6d3a",

    "lewis hamilton": "#00d2be",
    "george russell": "#24ffff",
    "frederik vesti": "#00a6ff",

    "max verstappen": "#fcd700",
    "sergio perez": "#ffec7b",
    "jake dennis": "#907400",

    "alexander albon": "#005aff",
    "logan sargeant": "#012564",
    "zak osullivan": "#1b3d97",
    "franco colapinto": "#639aff"
}


LEGACY_DRIVER_TRANSLATE: dict[str, str] = {
    'LEC': 'charles leclerc', 'SAI': 'carlos sainz',
    'SHW': 'robert shwartzman',
    'VER': 'max verstappen', 'PER': 'sergio perez',
    'DEN': 'jake dennis',
    'PIA': 'oscar piastri', 'NOR': 'lando norris',
    'OWA': 'pato oward',
    'GAS': 'pierre gasly', 'OCO': 'esteban ocon',
    'DOO': 'jack doohan',
    'BOT': 'valtteri bottas', 'ZHO': 'zhou guanyu',
    'POU': 'theo pourchaire',
    'DEV': 'nyck de vries', 'TSU': 'yuki tsunoda',
    'RIC': 'daniel ricciardo', 'LAW': 'liam lawson',
    'HAD': 'isack hadjar', 'IWA': 'ayumu iwasa',
    'MAG': 'kevin magnussen', 'HUL': 'nico hulkenberg',
    'BEA': 'oliver bearman',
    'ALO': 'fernando alonso', 'STR': 'lance stroll',
    'DRU': 'felipe drugovich',
    'HAM': 'lewis hamilton', 'RUS': 'george russell',
    'VES': 'frederik vesti',
    'ALB': 'alexander albon', 'SAR': 'logan sargeant',
    'OSU': 'zak osullivan', 'COL': 'franco colapinto'}
