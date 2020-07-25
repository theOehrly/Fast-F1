=======
Fast F1
=======

A python package for accessible F1 historical data and telemetry. 

Installation
============

You can install and update this package using the following command
::
    pip install git+https://github.com/Ax6/fast-f1.git

Note that Python 3.8 is required.

Usage
=====

Full documentation can be found
`here <https://ax6.github.io/Fast-F1/fastf1.html>`_.

Setting up an experiment is easy, especially if you are already familiar with
pandas and numpy.

Suppose that we want to analyse the race pace of Leclerc compared to Hamilton
from the Bahrain GP of 2019.

.. code:: python

    import fastf1 as ff1
    from fastf1 import plotting
    from matplotlib import pyplot as plt

    race = ff1.get_session(2019, 'Bahrain', 'R')
    laps = race.load_laps()

    lec = laps.pick_driver('LEC')
    ham = laps.pick_driver('HAM')

Once the session is loaded, and drivers are selected, you can plot their
lap times.

.. code:: python

    fig, ax = plt.subplots()
    plotting.laptime_axis(ax)
    ax.plot(lec['LapNumber'], lec['LapTime'].dt.total_seconds(), color='red')
    ax.plot(ham['LapNumber'], ham['LapTime'].dt.total_seconds(), color='cyan')
    ax.set_title("LEC vs HAM")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")
    plt.show()

.. image:: docs/_static/readme.svg
    :target: docs/_static/readme.svg

Compatibility
=============

Library is fully compatible with 2018 and 2019 season.  Older seasons are still
accessible and it is possible to obtain general weekend information (limited to
`Ergast web api <http://ergast.com/mrd/>`_). Live timing and telemetry is only
available starting from 2018.

