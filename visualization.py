import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import pickle

from experimental import TrackMap, TrackPoint  # necessary for pickle


def show_deviation_minima_on_track():
    stream_data = pickle.load(open("var_dumps/stream_data", "rb"))
    mad_x_stats = pickle.load(open("var_dumps/mad_x_stats", "rb"))
    mad_y_stats = pickle.load(open("var_dumps/mad_y_stats", "rb"))
    mean_x_stats = pickle.load(open("var_dumps/mean_x_stats", "rb"))
    mean_y_stats = pickle.load(open("var_dumps/mean_y_stats", "rb"))
    track_map = pickle.load(open("var_dumps/track_map", "rb"))

    track_x, track_y = list(), list()
    for tp in track_map.sorted_points:
        track_x.append(tp.x)
        track_y.append(tp.y)

    mean_x_stats = np.array(mean_x_stats)
    mean_y_stats = np.array(mean_y_stats)
    mad_x_stats = np.array(mad_x_stats)
    mad_y_stats = np.array(mad_y_stats)

    x_minima = np.r_[True, mad_x_stats[1:] < mad_x_stats[:-1]] & np.r_[mad_x_stats[:-1] < mad_x_stats[1:], True]
    y_minima = np.r_[True, mad_y_stats[1:] < mad_y_stats[:-1]] & np.r_[mad_y_stats[:-1] < mad_y_stats[1:], True]

    x_minima[-1] = False  # first and last values can not be minima
    y_minima[-1] = False
    x_minima[0] = False
    y_minima[0] = False

    print(x_minima)
    print(y_minima)

    ax_main = plt.subplot(label='Track Map')
    plt.plot(track_x, track_y)
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

    plt.show()
