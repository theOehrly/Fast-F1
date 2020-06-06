from fastf1 import core, api
from fastf1.track import Track
from fastf1.experimental.syncsolver import AdvancedSyncSolver
from fastf1.experimental.conditions import AllSectorBordersCondition
from matplotlib import pyplot as plt
import pickle
import time
import IPython


def advanced_sync():
    start_time = time.time()

    GP = 9

    session = core.get_session(2019, GP, 'R')
    pos = api.position(session.api_path)
    tel = api.car_data(session.api_path)
    laps_data, stream_data = api.timing_data(session.api_path)

    # session = pickle.load(open("var_dumps/session", "rb"))
    # pos = pickle.load(open("var_dumps/pos", "rb"))
    # tel = pickle.load(open("var_dumps/tel", "rb"))
    # laps_data = pickle.load(open("var_dumps/laps_data", "rb"))
    # track = pickle.load(open("var_dumps/track_map", "rb"))

    track = Track(pos)
    track.generate_track(visualization_frequency=250)

    pickle.dump(track, open("tracks/gp{}".format(GP), "wb"))

    solver = AdvancedSyncSolver(track, tel, pos, laps_data, processes=5)
    solver.setup()

    solver.add_condition(AllSectorBordersCondition)
    solver.solve()
    # solver.solve_one_condition_single_process()

    end_time = time.time()
    print("Took: ", end_time - start_time)

    pickle.dump(solver.results, open("solver_results/gp{}".format(GP), "wb"))

    plt.plot(solver.results['AllSectors']['mad_x1'])
    plt.plot(solver.results['AllSectors']['mad_x2'])
    plt.plot(solver.results['AllSectors']['mad_x3'])
    plt.show()

    IPython.embed()


if __name__ == '__main__':
    advanced_sync()
