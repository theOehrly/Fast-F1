Known bugs and caveats
======================

- Unexpected car numbers being parsed from :func:`fastf1.api.car_data`:

    There are some cases like 2019 Germany Q where the returned structure of
    :func:`fastf1.api.car_data` contains also telemetry data from inexistent
    drivers like driver number 1, 6 and so on. Telemetry is empty so this might
    just be a mishandled single entry. Currently an attempt to bypass is
    referring to timing_data drivers. For winter test we have driver number
    65535 and it is not bypassed.

- Day 3 and 6 of winter testing 2020

    Usually times obtained from the `timing_app_data` and `timing_data`
    requests are synchronised and because of this, the two data sources are
    merged on the time index. For some reason and only for Vettel on 21/02/2020
    and Bottas on 28/02/2020, time doesn't match. A manually patched file is
    included with the code. A more sofisticated solution is needed.

- Inlap and outlap handling in :func:`fastf1.track.Track.resync_lap_times`:

    Inlaps and outlaps may not be resynced correctly because of the addtional time
    in pit. Whether there is actually a bug is not sure yet though. Further analysis
    of the data is necessary. Only inlaps and outlaps seem to be concerned.

- Missing telemetry

    It may happen that telemetry data is missing for a specific car for some
    period of time. This problem is on the source (F1 timing) so there isn't
    much the library can do. An example is Bottas on day 3 of winter testing.
    In this case, channels are stuck towards the end of the morning session.