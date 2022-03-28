Known bugs and caveats
======================

- Deleted Laps

    It is not possible to determine if a lap time was deleted
    (usually because track limits were violated).
    The official fastest lap of a driver is marked as personal best lap.
    If one or multiple laps of a driver are faster than their respective
    personal best lap, one can deduce that these faster laps must have
    been deleted. There may exist deleted laps that are slower than the
    personal best lap of any driver. These cannot be marked!
    :func:`Laps.pick_fastest <fastf1.core.Laps.pick_fastest>` will by
    default return the fastest personal best lap.


- Missing telemetry

    It may happen that telemetry data is missing for a specific car for some
    period of time. This problem is on the source (F1 timing) so there isn't
    much the library can do. An example is Bottas on day 3 of winter testing.
    In this case, channels are stuck towards the end of the morning session.