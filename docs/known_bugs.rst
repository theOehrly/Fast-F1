Known bugs and caveats
======================


- This module does not work if the Ergast API is not available.

    If the Ergast server is down, this module does not work. Fixing this is high up on the ToDo list but
    not necessarily easy to accomplish.


- Unexpected car numbers being parsed from :func:`fastf1.api.car_data`:

    There are some cases like 2019 Germany Q where the returned structure of
    :func:`fastf1.api.car_data` contains also telemetry data from inexistent
    drivers like driver number 1, 6 and so on. Telemetry is empty so this might
    just be a mishandled single entry. Currently an attempt to bypass is
    referring to timing_data drivers. For winter test we have driver number
    65535 and it is not bypassed.


- Missing telemetry

    It may happen that telemetry data is missing for a specific car for some
    period of time. This problem is on the source (F1 timing) so there isn't
    much the library can do. An example is Bottas on day 3 of winter testing.
    In this case, channels are stuck towards the end of the morning session.