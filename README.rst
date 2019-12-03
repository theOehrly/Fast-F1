=======
Fast F1
=======

A python package for accessible F1 historical data and telemetry. 

Installation
============

You can install this package using pip
::
    pip install git+https://github.com/Ax6/fast-f1.git

Usage
=====

Full documentation can be found
`here <https://ax6.github.io/Fast-F1/fast-f1.html>`_.

Setting up an experiment is easy, especially if you are already familiar
with pandas and numpy.

Suppose that we want to analyse the race pace of Leclerc compared to 
Hamilton from the Bahrain GP (weekend number 2) of 2019.

.. code:: python

    import fastf1 as f1
    from fastf1 import plots
    from matplotlib import pyplot as plt

    race = f1.get_session(2019, 2, 'R').init()

    lec = race.summary[race.summary['Driver'] == 'LEC']
    ham = race.summary[race.summary['Driver'] == 'HAM']

Once the session is loaded, and drivers are selected, you can plot the
information

.. code:: python

    fig, ax = plt.subplots()
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

Library is fully compatible with 2018 and 2019 season.
While previous seasons are still accessible and it is possible to obtain
general weekend information (basically what you can get from
`Ergast web api <http://ergast.com/mrd/>`_) live timing and telemetry
data is only available starting from 2018.
