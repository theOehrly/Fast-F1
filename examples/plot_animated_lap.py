"""Animated lap plot
=======================

Plotting an animated speed, brake, rpm and throttle
"""
##############################################################################
# Import FastF1 and load the data
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation

import fastf1
import fastf1.plotting

# Load the session
session = fastf1.get_session(2023, 'Miami', 'Q')
session.load()

# Get laps for all drivers
laps = session.laps
fastest = laps.pick_fastest()
tel = fastest.get_telemetry()

# convert index to start from 0 instead of 2
tel.index = tel.index - 2

##############################################################################
# plot ratios are for how big each plot is
plot_ratios = [3, 1, 1, 1, 1]
plot_size = [15, 15]
# create 5 plots
fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(
    5,
    gridspec_kw={'height_ratios': plot_ratios})
plt.rcParams['figure.figsize'] = plot_size

##############################################################################
# initialize the plots with the first data point
x, y = [tel['X'][0]], [tel['Y'][0]]
line, = ax1.plot(
    x,
    y,
    color='red',
    linestyle='-', marker='o', linewidth=2, markersize=1)

speed, dist = [tel['Speed'][0]], [tel['Distance'][0]]
line1, = ax2.plot(
    dist, speed,
    color='blue',
    linestyle='-', marker='o', linewidth=2, markersize=1)

break_p, dist2 = [tel['Brake'][0]], [tel['Distance'][0]]
line2, = ax3.plot(
    dist, break_p,
    color='green',
    linestyle='-', marker='o', linewidth=2, markersize=1)

rpm, dist3 = [tel['RPM'][0]], [tel['Distance'][0]]
line3, = ax4.plot(
    dist, rpm,
    color='orange',
    linestyle='-', marker='o', linewidth=2, markersize=1)

throttle, dist4 = [tel['Throttle'][0]], [tel['Distance'][0]]
line4, = ax5.plot(
    dist, throttle,
    color='purple',
    linestyle='-', marker='o', linewidth=2, markersize=1)

##############################################################################
# set axis limits to fit data and hide labels
ax1.set_xlim(min(tel['X']) - 1000, max(tel['X']) + 1000)
ax1.set_ylim(min(tel['Y']) - 1000, max(tel['Y']) + 1000)
ax1.axes.xaxis.set_visible(False)
ax1.axes.yaxis.set_visible(False)

ax2.set_xlim(min(tel['Distance']) - 100, max(tel['Distance']) + 100)
ax2.set_ylim(min(tel['Speed']) - 100, max(tel['Speed']) + 100)
ax2.axes.xaxis.set_visible(False)
ax2.set_ylabel('Speed (km/h)')

ax4.set_xlim(min(tel['Distance']) - 100, max(tel['Distance']) + 100)
ax4.set_ylim(min(tel['RPM']) - 1000, max(tel['RPM']) + 1000)
ax4.axes.xaxis.set_visible(False)
ax4.tick_params(labelleft=True, left=False)
ax4.set_yticklabels([])
ax4.set_ylabel('RPM')

ax3.set_xlim(min(tel['Distance']) - 100, max(tel['Distance']) + 100)
ax3.set_ylim(min(tel['Brake']) - 0.5, max(tel['Brake']) + 1)
ax3.axes.xaxis.set_visible(False)
ax3.tick_params(labelleft=True, left=False)
ax3.set_yticklabels([])
ax3.set_ylabel('Brake')

ax5.set_xlim(min(tel['Distance']) - 100, max(tel['Distance']) + 100)
ax5.set_ylim(min(tel['Throttle']) - 5, max(tel['Throttle']) + 10)
ax5.axes.xaxis.set_visible(False)
ax5.tick_params(labelleft=True, left=False)
ax5.set_yticklabels([])
ax5.set_ylabel('Throttle')

##############################################################################


# update function for the animation
def update(num):
    if num == tel['Time'][0]:
        x.clear()
        y.clear()
        line.set_data(x, y)

    # plot the data for the current time
    x.append(tel[tel['Time'] == num]['X'])
    y.append(tel[tel['Time'] == num]['Y'])
    line.set_data(x, y)

    # convert numpy.timedelta64 to normal time
    time = pd.to_timedelta(num, unit='ms')
    # remove the days from the time
    time = str(time)[7:]

    # add a title to the plot
    ax1.set_title('Time: {}'.format(time))

    return line


def updateSpeed(num):
    if num == tel['Time'][0]:
        dist.clear()
        speed.clear()
        line.set_data(x, y)

    # plot the data for the current time
    speed.append(tel[tel['Time'] == num]['Speed'])
    dist.append(tel[tel['Time'] == num]['Distance'])
    line1.set_data(dist, speed)

    return line1


def updateBreak(num):
    # time is 0 then clear the data
    if num == tel['Time'][0]:
        break_p.clear()
        dist2.clear()
        line.set_data(x, y)

    # plot the data for the current time
    break_p.append(tel[tel['Time'] == num]['Brake'])
    dist2.append(tel[tel['Time'] == num]['Distance'])
    line2.set_data(dist2, break_p)

    return line2


def updateRPM(num):
    # time is 0 then clear the data
    if num == tel['Time'][0]:
        rpm.clear()
        dist3.clear()
        line.set_data(x, y)

    # plot the data for the current time
    rpm.append(tel[tel['Time'] == num]['RPM'])
    dist3.append(tel[tel['Time'] == num]['Distance'])
    line3.set_data(dist3, rpm)

    return line3


def updateThrottle(num):
    # time is 0 then clear the data
    if num == tel['Time'][0]:
        throttle.clear()
        dist4.clear()
        line.set_data(x, y)

    # plot the data for the current time
    throttle.append(tel[tel['Time'] == num]['Throttle'])
    dist4.append(tel[tel['Time'] == num]['Distance'])
    line4.set_data(dist4, throttle)

    return line4


##############################################################################
# create animation object
ani = animation.FuncAnimation(
    fig, update, frames=tel['Time'].unique(), interval=100)
ani1 = animation.FuncAnimation(
    fig, updateSpeed, frames=tel['Time'].unique(), interval=100)
ani2 = animation.FuncAnimation(
    fig, updateBreak, frames=tel['Time'].unique(), interval=100)
ani3 = animation.FuncAnimation(
    fig, updateRPM, frames=tel['Time'].unique(), interval=100)
ani4 = animation.FuncAnimation(
    fig, updateThrottle, frames=tel['Time'].unique(), interval=100)

##############################################################################
# show the plot
plt.show()

##############################################################################
# calculate avg speed
avg_speed = tel['Speed'].mean()
print('Average speed: ', avg_speed)
# top speed
top_speed = tel['Speed'].max()
print('Top speed: ', top_speed)
