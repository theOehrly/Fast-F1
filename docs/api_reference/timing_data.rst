Timing Data
===========

.. currentmodule:: fastf1.core

Timing data is represented using the following objects. It can be accessed
through the :attr:`Session.laps` attribute. To load a session,
see :ref:`loading-data`.

.. autosummary::
    :toctree: api_autogen/
    :template: class_summary_noinherited.rst

    Laps
    Lap



Lap Timing Data
---------------

The following information is available per lap (one DataFrame column
for each):

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Name
     - Data Type
     - Description
   * - **Time**
     - ``pandas.Timedelta``
     - Session time when the lap time was set (end of lap)
   * - **Driver**
     - ``str``
     - Three letter driver identifier
   * - **DriverNumber**
     - ``str``
     - Driver number
   * - **LapTime**
     - ``pandas.Timedelta``
     - Recorded lap time. To see if a lap time was deleted, check the **Deleted** column.
   * - **LapNumber**
     - ``float``
     - Recorded lap number
   * - **Stint**
     - ``float``
     - Stint number
   * - **PitOutTime**
     - ``pandas.Timedelta``
     - Session time when car exited the pit
   * - **PitInTime**
     - ``pandas.Timedelta``
     - Session time when car entered the pit
   * - **Sector1Time**
     - ``pandas.Timedelta``
     - Sector 1 recorded time
   * - **Sector2Time**
     - ``pandas.Timedelta``
     - Sector 2 recorded time
   * - **Sector3Time**
     - ``pandas.Timedelta``
     - Sector 3 recorded time
   * - **Sector1SessionTime**
     - ``pandas.Timedelta``
     - Session time when the Sector 1 time was set
   * - **Sector2SessionTime**
     - ``pandas.Timedelta``
     - Session time when the Sector 2 time was set
   * - **Sector3SessionTime**
     - ``pandas.Timedelta``
     - Session time when the Sector 3 time was set
   * - **SpeedI1**
     - ``float``
     - Speedtrap sector 1 [km/h]
   * - **SpeedI2**
     - ``float``
     - Speedtrap sector 2 [km/h]
   * - **SpeedFL**
     - ``float``
     - Speedtrap at finish line [km/h]
   * - **SpeedST**
     - ``float``
     - Speedtrap on longest straight (Not sure) [km/h]
   * - **IsPersonalBest**
     - ``bool``
     - Flag that indicates whether this lap is the official personal best lap of a driver. If any lap of a driver is quicker than their respective personal best lap, this means that the quicker lap is invalid and not counted. For example, this can happen if the track limits were exceeded.
   * - **Compound**
     - ``str``
     - Tyres event specific compound name: SOFT, MEDIUM, HARD, INTERMEDIATE, WET, TEST_UNKNOWN, UNKNOWN. The actual underlying compounds C1 to C5 are not differentiated. TEST_UNKNOWN compounds can appear in the data during pre-season testing and in-season Pirelli tyre tests.
   * - **TyreLife**
     - ``float``
     - Laps driven on this tire (includes laps in other sessions for used sets of tires)
   * - **FreshTyre**
     - ``bool``
     - Tyre had TyreLife=0 at stint start, i.e. was a new tire
   * - **Team**
     - ``str``
     - Team name
   * - **LapStartTime**
     - ``pandas.Timedelta``
     - Session time at the start of the lap
   * - **LapStartDate**
     - ``pandas.Timestamp``
     - Timestamp at the start of the lap
   * - **TrackStatus**
     - ``str``
     - A string that contains track status numbers for all track status that occurred during this lap. The meaning of the track status numbers is explained in :func:`fastf1.api.track_status_data`. For filtering laps by track status, you may want to use :func:`Laps.pick_track_status`.
   * - **Position**
     - ``float``
     - Position of the driver at the end of each lap. This value is NaN for FP1, FP2, FP3, Sprint Shootout, and Qualifying as well as for crash laps.
   * - **Deleted**
     - ``Optional[bool]``
     - Indicates that a lap was deleted by the stewards, for example because of a track limits violation. This data is only available when race control messages are loaded.
   * - **DeletedReason**
     - ``str``
     - Gives the reason for a lap time deletion. This data is only available when race control messages are loaded.
   * - **FastF1Generated**
     - ``bool``
     - Indicates that this lap was added by FastF1. Such a lap will generally have very limited information available and information is partly interpolated or based on reasonable assumptions. Cases were this is used are, for example, when a partial last lap is added for drivers that retired on track.
   * - **IsAccurate**
     - ``bool``
     - Indicates that the lap start and end time are synced correctly with other laps. Do not confuse this with the accuracy of the lap time or sector times. They are always considered to be accurate if they exist! If this value is True, the lap has passed as basic accuracy check for timing data. This does not guarantee accuracy but laps marked as inaccurate need to be handled with caution. They might contain errors which can not be spotted easily. Laps need to satisfy the following criteria to be marked as accurate:

- not an inlap or outlap
- set under green or yellow flag (the api sometimes has issues
  with data from SC/VSC laps)
- is not the first lap after a safety car period
  (issues with SC/VSC might still appear on the first lap
  after it has ended)
- has a value for lap time and all sector times
- the sum of the sector times matches the lap time
  (If this were to ever occur, it would also be logged separately
  as a data integrity error. You usually don't need to worry about
  this.)