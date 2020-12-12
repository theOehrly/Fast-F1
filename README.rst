=======
Fast F1
=======

A python package for accessible F1 historical data and telemetry.

IMPORTANT NOTE: Status of the project
=====================================

Currently this module is not usable which is the result of server issues with the F1 API.

See `this <https://twitter.com/F1Help/status/1335939396240093185>`_ Twitter post for some information.

Basically, it is no longer possible to download telemetry data after a session. Full telemetry data is currently
only available live during a session.

What will be done about this? For now, nothing. If, as hinted in the twitter post, this will work again next season,
then everything will be fine. In case this functionality will no longer ba available at all, a way to record a live
session will be implemented. This will lack the convenience of being able to load the data whenever desired so this is
only a worst case solution.

Interested in contributing? Read on...

Roadmap
=======

This is a rather loose roadmap with no fixed timeline whatsoever.

  - Release of version 2.1: This has been in development for multiple months, see the v2.1 branch. The main aim of this
    release is not to provide any new features. There are a lot of internal changes to the structure of the code. More
    of the available functionality is exposed so that more interaction and finer control is possible. Additionally,
    there are some speed and accuracy improvements as well as a better reimplemented cache.
    This release is "close" to be finished. It will not be usable for the same reasons as the current version until F1
    fixes their server issues. I will likely provide cached data for a few sessions, so that the new release can be
    tried out if somebody wants to do so.

After that in some yet to be determined order:

  - Improvements to the current plotting functionality
  - Some default plots to easily allow creating nice visualizations and interesting comparisons
  - General improvements and smaller additions to the current core functionality
  - Support for F1's own data api to get information about events, sessions, drivers and venues

And if necessary:

  - recording of live timing during a session


Contributing
============

Contributions are welcome of course. If you are interested in contributing, open an issue for the proposed feature
or issue you would like to work on. This way we can coordinate so that no unnecessary work is done.

Working directly on the core and api code will require some time to understand. Creating nice default plots on the
other hand does not required as deep of an understanding of the code and is therefore easier to accomplish. Pick
whatever you like to do.


Installation
============

You can install and update this package using the following command
::
    pip install git+https://github.com/theOehrly/Fast-F1.git

Note that Python 3.8 is required.

Usage
=====

Full documentation can be found
`here <https://theoehrly.github.io/Fast-F1/fastf1.html>`_.

Setting up an experiment is easy, especially if you are already familiar
with pandas and numpy.

Suppose that we want to analyse the race pace of Leclerc compared to 
Hamilton from the Bahrain GP (weekend number 2) of 2019.

.. code:: python

    import fastf1 as ff1
    from fastf1 import plotting
    from matplotlib import pyplot as plt

    ff1.utils.enable_cache('path/to/folder/for/cache')  # optional but recommended

    race = ff1.get_session(2019, 'Bahrain', 'R')
    laps = race.load_laps()

    lec = laps.pick_driver('LEC')
    ham = laps.pick_driver('HAM')

Once the session is loaded, and drivers are selected, you can plot the
information.

:code:`fastf1.plotting` provides some special axis formatting and data type conversion. This is required
for generating a correct plot.

It is not necessary to enable the usage of a cache but it is recommended. Simply provide
the path to some empty folder on your system.

.. code:: python

    fig, ax = plt.subplots()
    plotting.laptime_axis(ax)
    ax.plot(lec['LapNumber'], lec['LapTime'], color='red')
    ax.plot(ham['LapNumber'], ham['LapTime'], color='cyan')
    ax.set_title("LEC vs HAM")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")
    plt.show()

.. image:: docs/_static/readme.svg
    :target: docs/_static/readme.svg

Compatibility
=============

Starting with the Austrian GP 2020 the API provides the position data in a
somewhat different format. This currently breaks ALL functionality of the track class.
Maybe also other functionality.

The library is fully compatible with 2018 and 2019 season.  Older seasons are still
accessible and it is possible to obtain general weekend information (limited to
`Ergast web api <http://ergast.com/mrd/>`_). Live timing and telemetry is only
available starting from 2018.
