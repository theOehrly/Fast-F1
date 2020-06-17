import os
import pickle
import matplotlib.pyplot as plt

from fastf1 import core, api
from fastf1.track import TrackPoint, Track


def get_range_manual(track):
    """A short script for semi-interactively selecting a start and end point on a track map."""
    plt.ion()

    fig = plt.figure()
    ax = fig.add_subplot()
    ax.set_aspect('equal')

    plt.plot(track.sorted_x, track.sorted_y)
    plt.show()
    indic_line, = ax.plot([], [], 'red')

    start = None
    end = None

    def get_point():
        x = float(input('X:'))
        y = float(input('Y:'))
        return TrackPoint(x, y)

    while True:
        print('Set Start (S) / Set End (E) / Finish (F)')
        do = input('>').lower()

        if do == 's':
            start = get_point()
        elif do == 'e':
            end = get_point()
        elif do == 'f':
            plt.close()
            plt.ioff()
            plt.clf()
            return start, end

        if start and end:
            px = list()
            py = list()

            px.append(start.x)
            px.append(end.x)
            py.append(start.y)
            py.append(end.y)

            indic_line.set_data(px, py)


def load_from_working_dir(year, gp, session, working_dir):
    pickle_path = os.path.join(working_dir, 'pickle_{}_{}_{}/'.format(year, gp, session))
    if not os.path.exists(pickle_path):
        print('Data does not yet exist in working directory. Downloading...')
        os.makedirs(pickle_path)

        session = core.get_session(year, gp, session)
        pos = api.position(session.api_path)
        tel = api.car_data(session.api_path)
        laps_data, stream_data = api.timing_data(session.api_path)

        track = Track(pos)
        track.generate_track(visualization_frequency=250)

        pickle.dump(session, open(os.path.join(pickle_path, 'session'), 'wb'))
        pickle.dump(pos, open(os.path.join(pickle_path, 'pos'), 'wb'))
        pickle.dump(tel, open(os.path.join(pickle_path, 'tel'), 'wb'))
        pickle.dump(laps_data, open(os.path.join(pickle_path, 'laps_data'), 'wb'))
        pickle.dump(track, open(os.path.join(pickle_path, 'track'), 'wb'))

        print('Finished loading!')

        return session, pos, tel, laps_data, track

    else:
        print('Loading existing data from working directory...')
        session = pickle.load(open(os.path.join(pickle_path, 'session'), 'rb'))
        pos = pickle.load(open(os.path.join(pickle_path, 'pos'), 'rb'))
        tel = pickle.load(open(os.path.join(pickle_path, 'tel'), 'rb'))
        laps_data = pickle.load(open(os.path.join(pickle_path, 'laps_data'), 'rb'))
        track = pickle.load(open(os.path.join(pickle_path, 'track'), 'rb'))

        print('Finished loading!')

        return session, pos, tel, laps_data, track
