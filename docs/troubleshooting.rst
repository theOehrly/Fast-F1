=======================
Troubleshooting
=======================


Something doesn't work
=======================

1. Have you updated to the newest version of fastf1?

2. Clear the cache or run your script without cache enabled first if you don't want to clear it just for a test.
    If everything works when running without cache enabled, clear the cache and enable it again.
    After updating it can be necessary to clear the cache.

3. Does the log produce any warnings that sound like they might be related? Maybe the data you are looking for
   is not available or can not be processed correctly.

4. Open an issue on github.



What does this error message mean?
==================================

Short explanation of some error messages


module `api`
------------

- `Car data/position data for driver x is incomplete.`
    Usually data for all drivers is available for the whole duration of a session. Even if the driver did not drive for
    most parts of the session. All values for each sample will simply be zero (or whatever is equivalent to zero) then.
    But in some cases samples are simply missing.
    In this case data will be filled in with zero values. This is to make sure that all data streams for each driver
    have the same length because some calculations will else fail.
    This has the side effect that 'DistanceToDriverAhead' and 'DriverAhead' information may be (but not necessarily)
    wrong for other drivers too. Simply because there might have been another car on track but we don't know the
    position.

    If you get this message for nonexistent drivers:
    Sometimes the api sends empty/zero-valued samples for drivers that don't exist. When this happens, it usually
    only happens for a short part of the session. Because there is only data for a part of the session, this warning is
    triggered. If this is the case this warning means nothing at all. The nonexistent drivers will be filtered out
    later.


module `core`
--------------

- `Ergast api not supported for testing`
    Ergast does not have data for testing session.
    This means that some data (for example driver data) is simply not available.

- `Ergast lookup failed`
    Session information on Ergast is usually only available after a race weekend.
    If you want to analyze a session during the race weekend, there will likely be no data on Ergast yet.

- `Could not find position/telemetry data for driver x`
    For some unknown reason the data does not exist.

- `Empty telemetry slice from lap y of driver x`
    There is a timed lap of which we know beginning and end but for some unknown reason there is no telemetry for it.