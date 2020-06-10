import matplotlib.pyplot as plt
from fastf1.track import TrackPoint


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



