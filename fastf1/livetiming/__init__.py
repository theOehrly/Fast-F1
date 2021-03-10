"""
:mod:`fastf1.livetiming` - Live Timing Client
=====================================================

This module can be used to save live timing data during a session.

.. warning:: Receiving and saving the SignalR live timing data is
    experimental. This functionality is largely untested due to a distinct
    lack of testing opportunities.

.. note:: While data can be saved, it is not yet possible to actually use
    the saved data. An update which allows using the data will likely be
    available after the 2021 pre-season testing.


There are two ways to interact with this module.

    - From a python script by creating an instance of
      :class:`.SignalRClient`

    - From the command line by calling ``python -m fastf1.livetiming``


Live Timing Data Object
-----------------------

To be added in future release


Live Timing Client
------------------

.. automodule:: fastf1.livetiming.client
    :members:
    :undoc-members:
    :show-inheritance:

"""
