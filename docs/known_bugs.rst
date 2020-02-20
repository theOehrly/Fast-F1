Known bugs
==========

- Unexpected car numbers being parsed from :func:`fastf1.api.car_data`:

    There are some cases like 2019 Germany Q where the returned
    structure of car_data api function contains also telemetry data from
    inexistent drivers like driver number 1, 6 and so on. Telemetry is
    empty so this might just be a mishandled single entry. Currently 
    this is bypassed by referring to timing_data drivers.
