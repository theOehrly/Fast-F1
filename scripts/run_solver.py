import json
import os

from fastf1 import utils
from fastf1.experimental.syncsolver import AdvancedSyncSolver
from fastf1.experimental.conditions import AllSectorBordersCondition
from scripts.visualization import all_sectors_result_plots

from scripts.tools import get_range_manual, load_from_working_dir


utils.enable_cache('*path/to/cache*')


if __name__ == '__main__':
    GP = 9
    YEAR = 2019
    SESSION = 'R'
    STEP = 1
    WORKING_DIR = '*path/to/working/directory*'
    UID = 'sync 2'
    NAME = 'Austria 2019'

    UNAME = NAME + ' ' + UID
    OUT_DIR = os.path.join(WORKING_DIR, UID+'/')

    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)

    session, pos, tel, laps_data, track = load_from_working_dir(YEAR, GP, SESSION, WORKING_DIR)

    print(session.weekend.name)

    point_start, point_end = get_range_manual(track)

    solver = AdvancedSyncSolver(track, tel, pos, laps_data, processes=4)
    solver.setup()
    solver.manual_range(point_start, point_end)
    solver.add_condition(AllSectorBordersCondition)

    solver.solve(step_size=STEP)

    # dumps solver results as json
    json_file = open(os.path.join(OUT_DIR, 'results.json'), 'w')
    json.dump(solver.results, json_file)
    json_file.close()

    # visualize solver results
    all_sectors_result_plots(solver.results['AllSectors'], track, UNAME, workdir=OUT_DIR)
