import os
import pickle
import matplotlib.pyplot as plt

from fastf1 import utils
from scripts.visualization import plot_lap_time_integrity, plot_lap_position_integrity

from scripts.tools import load_from_working_dir


utils.enable_cache('*path/to/cache*')


if __name__ == '__main__':
    GP = 9
    YEAR = 2019
    SESSION = 'R'
    WORKING_DIR = '*path/to/working/directory*'
    UID = 'sync 2'
    NAME = 'Austria 2019'

    NEW_X = 1334
    NEW_Y = -1120

    UNAME = NAME + ' ' + UID
    OUT_DIR = os.path.join(WORKING_DIR, UID)

    session, pos, tel, laps_data, track = load_from_working_dir(YEAR, GP, SESSION, WORKING_DIR)

    print(session.weekend.name)

    track.set_finish_line(NEW_X, NEW_Y)
    new_laps_data = track.resync_lap_times(laps_data)

    plot_lap_position_integrity(laps_data, track, suffix='prelim')
    plot_lap_time_integrity(laps_data, suffix='prelim')

    plot_lap_position_integrity(new_laps_data, track, suffix='new x{} y{}'.format(NEW_X, NEW_Y))
    plot_lap_time_integrity(new_laps_data, suffix='new x{} y{}'.format(NEW_X, NEW_Y))

    outfile_name = os.path.join(OUT_DIR, 'new_laps_data')
    pickle.dump(new_laps_data, open(outfile_name, 'wb'))

    plt.show()
