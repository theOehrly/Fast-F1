Known bugs and caveats
======================

- Deleted Laps

    It is currently not possible to determine if a lap time was deleted
    (usually because track limits were violated).
    :func:`Laps.pick_fastest <fastf1.core.Laps.pick_fastest>` may therefore
    return a lap that is not actually relevant for the final result of
    qualifying.


- Missing telemetry

    It may happen that telemetry data is missing for a specific car for some
    period of time. This problem is on the source (F1 timing) so there isn't
    much the library can do. An example is Bottas on day 3 of winter testing.
    In this case, channels are stuck towards the end of the morning session.