"""Animated ghost lap comparison
==============================

Animate the fastest qualifying laps of two drivers on the track map, as if
they were driving against each other. This makes it easy to see where on
the lap one driver gains or loses time.
"""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from timple.timedelta import strftimedelta

import fastf1
import fastf1.plotting


# Enable Matplotlib patches for plotting timedelta values and load
# FastF1's dark color scheme
fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme="fastf1")


##############################################################################
# Load the session and pick the fastest lap of each driver.
# At the 2023 Hungarian Grand Prix, Hamilton took pole position by just
# 0.003 seconds ahead of Verstappen.
session = fastf1.get_session(2023, "Hungary", "Q")
session.load(weather=False, messages=False)

drivers = ("HAM", "VER")
laps = {drv: session.laps.pick_drivers(drv).pick_fastest()
        for drv in drivers}

circuit_info = session.get_circuit_info()


##############################################################################
# Define a helper function for rotating points around the origin of the
# coordinate system, so that the track map is oriented correctly.
# (See also the example "Draw a track map with numbered corners".)
def rotate(xy, *, angle):
    rot_mat = np.array([[np.cos(angle), np.sin(angle)],
                        [-np.sin(angle), np.cos(angle)]])
    return np.matmul(xy, rot_mat)


track_angle = circuit_info.rotation / 180 * np.pi


##############################################################################
# The position samples of the two laps are not recorded at the same moments.
# To animate both cars together, we interpolate their positions onto a
# common time axis. Each animation frame then shows where each car was at
# the same point in time since the start of its lap.
#
# We also keep the distance driven, so we can show how far apart the two
# cars are on track.
frame_step = 0.25  # seconds of lap time per animation frame

lap_times = {drv: lap["LapTime"].total_seconds()
             for drv, lap in laps.items()}
frame_times = np.arange(0, max(lap_times.values()) + frame_step, frame_step)

positions = {}
distances = {}
for drv, lap in laps.items():
    tel = lap.get_telemetry()
    t = tel["Time"].dt.total_seconds().to_numpy()
    xy = rotate(tel.loc[:, ("X", "Y")].to_numpy(), angle=track_angle)

    # np.interp holds the last value after the end of the lap,
    # so a car that has already finished waits at the finish line
    positions[drv] = np.column_stack([
        np.interp(frame_times, t, xy[:, 0]),
        np.interp(frame_times, t, xy[:, 1]),
    ])
    distances[drv] = np.interp(frame_times, t, tel["Distance"].to_numpy())


##############################################################################
# Draw the static parts of the plot: the track outline and the legend.
# The car markers and the info text are created empty and are updated in
# every frame of the animation.
fig, ax = plt.subplots(figsize=(8, 6))
# leave room for the title and info text above and the legend below the map
fig.subplots_adjust(top=0.82, bottom=0.08)

track_tel = laps[drivers[0]].get_pos_data()
track = rotate(track_tel.loc[:, ("X", "Y")].to_numpy(), angle=track_angle)
# close the loop, so that there is no gap at the start/finish line
track = np.vstack([track, track[:1]])
ax.plot(track[:, 0], track[:, 1], color="grey", linewidth=6, alpha=0.5,
        zorder=0)

# The cars are often only a few metres apart, so the markers overlap.
# The driver who is ahead is drawn 20% larger and below the other marker,
# so that both stay visible and overtakes are easy to spot.
marker_size = 12
leader_size = marker_size * 1.2

markers = {}
for drv in drivers:
    color = fastf1.plotting.get_driver_color(drv, session=session)
    lap_time_str = strftimedelta(laps[drv]["LapTime"], "%m:%s.%ms")
    markers[drv], = ax.plot([], [], "o", markersize=marker_size, color=color,
                            markeredgecolor="white",
                            label=f"{drv}  {lap_time_str}")

ax.set_title(f"{session.event['EventName']} {session.event.year} "
             f"- Qualifying\nFastest laps: {drivers[0]} vs {drivers[1]}",
             pad=30)

# The info text is placed between the title and the track map, so that it
# never covers the track.
info_text = ax.text(0.5, 1.01, "", transform=ax.transAxes, ha="center",
                    va="bottom", fontsize=12, family="monospace")

# place the legend below the track map, so that it does not cover the track
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 0), ncol=2,
          frameon=False)
ax.set_aspect("equal")
ax.set_xticks([])
ax.set_yticks([])


##############################################################################
# The update function is called once per frame. It moves both car markers to
# their interpolated position, enlarges the marker of the driver who is
# ahead and shows the lap time and the gap on track between the two cars.
def update(frame):
    gap = distances[drivers[0]][frame] - distances[drivers[1]][frame]
    leader = drivers[0] if gap >= 0 else drivers[1]

    for drv in drivers:
        markers[drv].set_data([positions[drv][frame, 0]],
                              [positions[drv][frame, 1]])
        if drv == leader:
            markers[drv].set_markersize(leader_size)
            markers[drv].set_zorder(2)
        else:
            markers[drv].set_markersize(marker_size)
            markers[drv].set_zorder(3)

    info_text.set_text(f"Lap time: {frame_times[frame]:5.1f} s   |   "
                       f"{leader} ahead by {abs(gap):3.0f} m")
    return (*markers.values(), info_text)


##############################################################################
# Finally, create the animation. The interval sets the delay between frames
# in milliseconds. With 0.25 s of lap time per frame and an interval of
# 50 ms, the laps play back at five times real speed.
ani = FuncAnimation(fig, update, frames=len(frame_times), interval=50)
plt.show()