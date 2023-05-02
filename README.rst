======
FastF1
======

FastF1 is a python package for accessing and analyzing Formula 1 results,
schedules, timing data and telemetry.

.. image:: docs/_static/readme.png
    :target: docs/_static/readme.png


Main Features
=============

- Access to F1 timing data, telemetry, sessions results and more
- Full support for `Ergast <http://ergast.com/mrd/>`_ to access current and
  historical F1 data
- All data is provided in the form of extended Pandas DataFrames to make
  working with the data easy while having powerful tools available
- Adds custom functions to the Pandas objects specifically to make working
  with F1 data quick and simple
- Integration with Matplotlib to facilitate data visualization
- Implements caching for all API requests to speed up your scripts


Installation
============

It is recommended to install FastF1 using `pip`:

.. code-block:: bash

   pip install fastf1

Note that Python 3.8 or higher is required.

Alternatively, a wheel or a source distribution can be downloaded from Pypi.

You can also install using `conda`:

.. code-block:: bash

  conda install -c conda-forge fastf1


Documentation
=============

The official documentation can be found here:
`https://theoehrly.github.io/Fast-F1/ <https://theoehrly.github.io/Fast-F1/>`_


Notice
======

FastF1 and this website are unofficial and are not associated in any way with
the Formula 1 companies. F1, FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD
CHAMPIONSHIP, GRAND PRIX and related marks are trade marks of Formula One
Licensing B.V.
