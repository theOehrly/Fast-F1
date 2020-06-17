Known bugs
==========

- Unexpected car numbers being parsed from :func:`fastf1.api.car_data`:

    There are some cases like 2019 Germany Q where the returned
    structure of car_data api function contains also telemetry data from
    inexistent drivers like driver number 1, 6 and so on. Telemetry is
    empty so this might just be a mishandled single entry. Currently 
    this is bypassed by referring to timing_data drivers.


- Inlap and outlap handling in :func:`fastf1.track.Track.resync_lap_times`:

    Inlaps and outlaps may not be resynced correctly because of the addtional time
    in pit. Whether there is actually a bug is not sure yet though. Further analysis
    of the data is necessary. Only inlaps and outlaps seem to be concerned.
