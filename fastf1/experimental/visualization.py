import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import pickle
from experimental import TrackPoint, Track  # necessary for pickle


def show_deviation_minima_on_track(res, track):
    mad_x_stats = res['mad_x1']
    mad_y_stats = res['mad_y1']
    mean_x_stats = res['mean_x1']
    mean_y_stats = res['mean_y1']

    mean_x_stats = np.array(mean_x_stats)
    mean_y_stats = np.array(mean_y_stats)
    mad_x_stats = np.array(mad_x_stats)
    mad_y_stats = np.array(mad_y_stats)

    x_minima = np.r_[True, mad_x_stats[1:] < mad_x_stats[:-1]] & np.r_[mad_x_stats[:-1] < mad_x_stats[1:], True]
    y_minima = np.r_[True, mad_y_stats[1:] < mad_y_stats[:-1]] & np.r_[mad_y_stats[:-1] < mad_y_stats[1:], True]

    print(x_minima)
    print(y_minima)

    ax_main = plt.subplot(label='Track Map')
    plt.plot(track.sorted_x, track.sorted_y)
    ax_main.set_aspect('equal')
    ax_main.set_xlabel('X')
    ax_main.set_ylabel('Y')
    ax_main.yaxis.set_tick_params(labelleft=False, labelright=True)
    ax_main.yaxis.set_label_position("right")

    # x deviation minima
    for x_min in mean_x_stats[x_minima]:
        ax_main.axvline(x_min, color='r')

    # y deviation minima
    for y_min in mean_y_stats[y_minima]:
        ax_main.axhline(y_min, color='r')

    divider = make_axes_locatable(ax_main)
    ax_mad_x = divider.append_axes("top", 1.2, pad=0.1, sharex=ax_main)
    ax_mad_y = divider.append_axes("left", 1.2, pad=0.1, sharey=ax_main)

    ax_mad_x.plot(mean_x_stats, mad_x_stats)
    ax_mad_x.set_ylabel('Y MAD')
    ax_mad_x.xaxis.set_tick_params(labelbottom=False)

    ax_mad_y.plot(mad_y_stats, mean_y_stats)
    ax_mad_y.invert_xaxis()
    ax_mad_y.set_xlabel('X MAD')
    ax_mad_y.yaxis.set_tick_params(labelleft=False)


if __name__ == '__main__':
    GP = 9

    solver_res = pickle.load(open("solver_results/gp{}".format(GP), "rb"))
    r = solver_res['AllSectors']
    track = pickle.load(open("tracks/gp{}".format(GP), "rb"))

    plt.figure()
    plt.plot(r['mad_x1'], label="mad_x1")
    plt.plot(r['mad_x2'], label="mad_x2")
    plt.plot(r['mad_x3'], label="mad_x3")
    plt.legend()

    plt.figure()
    plt.plot(r['mad_y1'], label="mad_y1")
    plt.plot(r['mad_y2'], label="mad_y2")
    plt.plot(r['mad_y3'], label="mad_y3")
    plt.legend()

    plt.figure()
    show_deviation_minima_on_track(r, track)

    dx = list()
    for test, tres in zip(r['tx'], r['mean_x1']):
        dx.append(test-tres)

    dy = list()
    for test, tres in zip(r['ty'], r['mean_y1']):
        dy.append(test-tres)

    plt.figure()
    plt.plot(dx, label='dx')
    plt.plot(dy, label='dy')
    plt.legend()

    plt.show()
