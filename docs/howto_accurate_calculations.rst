======================================
How to perform calculations accurately
======================================

This is intended to be a writeup of my experiences. I discovered all of this when trying to implement new functionality
or when trying to improve existing calculations. The data that can be received from the F1 API has a very limited
sample rate of about 4-5 Hz. Furthermore, the data is somewhat jittery. That said, one can still perform accurate
calculations based on this data. But doing validation and accuracy checks is a must.


Validating results
------------------

It is extremely important to never assume that something is correct just because it looks right on the first glance.
Often it is possible to validate the data "against itself" or just validate it logically. This may not always give
absolute certainty that the results are accurate. But it can show when there are errors in the calculations. Or maybe
the data is simply not accurate enough for what one is trying to do.

Here are two examples for (partially) validating calculated data:

    - Use a known accurate value as a comparison. Let's assume we calculate the start time of each lap. As a result of
        the calculations we get a timestamp per lap which marks the beginning of this lap. We can now subtract the
        beginnings of two subsequent laps which will give us a measure for how long the first lap was, i.e. the lap
        time. Lap timing is of course also measured separately and known to be accurate to one millisecond. And it
        should be the same as our calculated values. This way we can validate the integrity of the calculated
        timestamps, excluding any random errors or general inaccuracy. Of course, a fixed offset which is equal for all
        timestamps would not show up as an error when using this validation.

    - Check that the data makes sense. Again, assume we are trying to find the start of a lap. If have calculated the
        timestamps for that, we can also calculated the position of the car at this time. Every time a lap starts, the
        car should be crossing over the finish line. And the finish line cannot physically move. So the position of the
        car should be the same every time a new lap starts. If it isn't there has to be an error somewhere.



Working with the available data
-------------------------------

A few straight forward guidelines can be set.

    - Do not work with interpolated values. Interpolation does always introduce some inaccuracy and in my experience
        this is rarely offset by more data points or by the fact that a timestamp matches better.

        The API provides car data and position data separately and with two different time bases. If somehow possible,
        you should use the data with the existing time base. That means, you cannot merge the datasets for use in
        calculations as this requires interpolation. If you need a combined end result and/or a different time base,
        do only merge and resample the result of your calculations. Do not resample the input data.

    - Do not perform calculations based on values that have been calculated by means of integration. The low sample rate
        of the source data and the existing inaccuracies mean that integration will always be error prone. Errors can
        stack up and single outliers will influence all further results of the integration.

Clearly, this rules can not always be followed. They sometimes need to be broken as there may be no other way around it.
But, by keeping these rules in mind, potential error sources can be reduced.



Slicing data by lap for use in further calculations
----------------------------------------------------

If you simply wish to visualize existing data, slicing laps is rather straight forward.

.. code-block:: python

    session = ff1.get_session(2020, 4, 'Q')
    laps = session.load_laps(with_telemetry=True)
    fastest_lap = laps.pick_fastest()
    tel = fastest_lap.telemetry

This will give you the merged telemetry with a first and last value being interpolated additionally so as to exactly
match the start and end of the lap.
This data is not suitable for further calculations though.

If you want to perform your own calculations with the data, you should use the raw data.
To stay away from interpolation before doing any calculations, the following could be done:

.. code-block:: python

    session = ff1.get_session(2020, 4, 'Q')
    laps = session.load_laps(with_telemetry=True)
    fastest_lap = laps.pick_fastest()
    drv_n = fastest_lap['DriverNumber']

    # use padding so that there are values outside of the desired range for accurate interpolation later
    car_data = session.slice_by_lap(session.car_data[drv_n], fastest_lap, pad=1, pad_side='both')
    pos_data = session.slice_by_lap(session.pos_data[drv_n], fastest_lap, pad=1, pad_side='both')

    # do calculations here
    # ...
    # ...

    merged_data = session.merge_channels(car_data, pos_data)

    # slice again to remove the padding and interpolate the exact first and last value
    merged_data = session.slice_by_lap(merged_data, fastest_lap, interpolate_edges=True)



Disclaimer
----------

The information here is what I have discovered to be most effective. This is probably not perfect. There are just too
many (time consuming) things that can be tried out. If you have some better ideas or want to discuss accuracy and
possibilities, feel free to open an issue about it.
