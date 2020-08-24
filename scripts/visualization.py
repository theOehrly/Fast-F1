import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import os


def show_deviation_minima_on_track(res, track, sector_number):
    mad_x_stats = res['mad_x{}'.format(sector_number)]
    mad_y_stats = res['mad_y{}'.format(sector_number)]
    mean_x_stats = res['mean_x{}'.format(sector_number)]
    mean_y_stats = res['mean_y{}'.format(sector_number)]

    mean_x_stats = np.array(mean_x_stats)
    mean_y_stats = np.array(mean_y_stats)
    mad_x_stats = np.array(mad_x_stats)
    mad_y_stats = np.array(mad_y_stats)

    x_minima = np.r_[True, mad_x_stats[1:] < mad_x_stats[:-1]] & np.r_[mad_x_stats[:-1] < mad_x_stats[1:], True]
    y_minima = np.r_[True, mad_y_stats[1:] < mad_y_stats[:-1]] & np.r_[mad_y_stats[:-1] < mad_y_stats[1:], True]

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
    ax_mad_x.grid(which='both')
    ax_mad_x.set_ylabel('Y MAD {}'.format(sector_number))
    ax_mad_x.xaxis.set_tick_params(labelbottom=False)

    ax_mad_y.plot(mad_y_stats, mean_y_stats)
    ax_mad_y.grid(which='both')
    ax_mad_y.invert_xaxis()
    ax_mad_y.set_xlabel('X MAD {}'.format(sector_number))
    ax_mad_y.yaxis.set_tick_params(labelleft=False)


def plot_lap_time_integrity(laps_data, suffix=''):
    drivers_series = laps_data.Driver
    drivers = list(drivers_series.drop_duplicates())

    deltas = list()
    ref = list()  # scatter plots need an x and y value therefore ref is created by counting up
    n = 0

    if 'Date' in laps_data.columns:
        for driver in drivers:
            i_max = len(laps_data[laps_data.Driver == driver])
            for i in range(1, i_max):
                delta = (laps_data.iloc[i].Date - laps_data.iloc[i].LapTime - laps_data.iloc[i-1].Date).total_seconds()
                deltas.append(delta)
                ref.append(n)
                n += 1
    else:
        for driver in drivers:
            i_max = len(laps_data[laps_data.Driver == driver])
            for i in range(1, i_max):
                delta = (laps_data.iloc[i].Time - laps_data.iloc[i].LapTime - laps_data.iloc[i-1].Time).total_seconds()
                deltas.append(delta)
                ref.append(n)
                n += 1

    fig1 = plt.figure()
    fig1.suptitle("Lap Time Scatter {}".format(suffix))
    plt.scatter(ref, deltas)

    fig2 = plt.figure()
    fig2.suptitle("Lap Time Histogram {}".format(suffix))
    plt.hist(deltas, bins=50)


def plot_lap_position_integrity(laps_data, track, suffix=''):
    x_vals = list()
    y_vals = list()

    if 'Date' in laps_data.columns:
        for _, lap in laps_data.iterrows():
            if type(lap.Driver) != str:
                continue
            p = track.interpolate_pos_from_time(lap.Driver, lap.Date)
            if not p:
                continue
            x_vals.append(p.x)
            y_vals.append(p.y)
    else:
        drivers = list(track._pos_data.keys())
        # calculate the start date of the session
        some_driver = drivers[0]  # TODO to be sure this should be done with multiple drivers
        session_start_date = track._pos_data[some_driver].head(1).Date.squeeze().round('min')
        for _, lap in laps_data.iterrows():
            if type(lap.Driver) != str:
                continue
            p = track.interpolate_pos_from_time(lap.Driver, session_start_date + lap.Time)
            if not p:
                continue

            x_vals.append(p.x)
            y_vals.append(p.y)

    fig1 = plt.figure()
    fig1.suptitle("Position Scatter {}".format(suffix))
    plt.scatter(x_vals, y_vals)

    fig2 = plt.figure()
    fig2 .suptitle("Position X Histogram {}".format(suffix))
    plt.hist(x_vals, bins=30)

    fig3 = plt.figure()
    fig3.suptitle("Position Y Histogram {}".format(suffix))
    plt.hist(y_vals, bins=30)


def all_sectors_result_plots(result, track, suffix, workdir=None):
    r = result

    # mean absolute deviation x
    plt.figure(figsize=(15, 8))
    plt.suptitle('MAD X | {}'.format(suffix))
    plt.plot(r['mad_x1'], label="mad_x1")
    plt.plot(r['mad_x2'], label="mad_x2")
    plt.plot(r['mad_x3'], label="mad_x3")
    plt.legend()
    plt.grid(which='both')
    if workdir:
        plt.savefig(os.path.join(workdir, 'mad x {}.png'.format(suffix)), dpi=300)

    # mean absolute deviation y
    plt.figure(figsize=(15, 8))
    plt.suptitle('MAD Y | {}'.format(suffix))
    plt.plot(r['mad_y1'], label="mad_y1")
    plt.plot(r['mad_y2'], label="mad_y2")
    plt.plot(r['mad_y3'], label="mad_y3")
    plt.legend()
    plt.grid(which='both')
    if workdir:
        plt.savefig(os.path.join(workdir, 'mad y {}.png'.format(suffix)), dpi=300)

    # track + mad plot one for each sector
    plt.figure(figsize=(15, 8))
    plt.suptitle('Track + MAD 1 | {}'.format(suffix))
    show_deviation_minima_on_track(r, track, 1)
    if workdir:
        plt.savefig(os.path.join(workdir, 'track plus mad 1 {}.png'.format(suffix)), dpi=300)

    plt.figure(figsize=(15, 8))
    plt.suptitle('Track + MAD 2 | {}'.format(suffix))
    show_deviation_minima_on_track(r, track, 2)
    if workdir:
        plt.savefig(os.path.join(workdir, 'track plus mad 2 {}.png'.format(suffix)), dpi=300)

    plt.figure(figsize=(15, 8))
    plt.suptitle('Track + MAD 3 | {}'.format(suffix))
    show_deviation_minima_on_track(r, track, 3)
    if workdir:
        plt.savefig(os.path.join(workdir, 'track plus mad 3 {}.png'.format(suffix)), dpi=300)

    # delta between test value and mean result
    dx = list()
    for test, tres in zip(r['tx'], r['mean_x1']):
        dx.append(test-tres)

    dy = list()
    for test, tres in zip(r['ty'], r['mean_y1']):
        dy.append(test-tres)

    plt.figure(figsize=(15, 8))
    plt.suptitle('Difference In - Out Coordinate | {}'.format(suffix))
    plt.plot(dx, label='dx')
    plt.plot(dy, label='dy')
    plt.legend()
    plt.grid(which='both')
    if workdir:
        plt.savefig(os.path.join(workdir, 'coord diff {}.png'.format(suffix)), dpi=300)

    plt.show()
