from fastf1.plotting._constants import (  # noqa: F401, unused import used through globals()
    season2018,
    season2019,
    season2020,
    season2021,
    season2022,
    season2023,
    season2024,
    season2025
)
from fastf1.plotting._constants.base import BaseSeasonConst


Constants: dict[str, BaseSeasonConst] = dict()

for year in range(2018, 2026):
    season = globals()[f"season{year}"]
    Constants[str(year)] = BaseSeasonConst(
        CompoundColors=season.CompoundColors,
        Teams=season.Teams
    )
