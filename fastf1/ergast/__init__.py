"""
Ergast API Interface - :mod:`fastf1.ergast`
===========================================

Introduction
------------

This module can be used to interface with Ergast F1 API
(https://ergast.com/mrd/). All Ergast endpoints are supported.

The class :class:`Ergast` provides access to all API Endpoints of Ergast.

Response Types
..............

Data can be returned in two different formats:

**Raw Response**

.. autosummary::
   :nosignatures:

   ~interface.ErgastRawResponse

This format is a JSON-like representation of the original JSON data (using
``json.load``).

**Flattened into Pandas DataFrames**

.. autosummary::
   :nosignatures:

   ~interface.ErgastSimpleResponse
   ~interface.ErgastMultiResponse

The complexity of the data that is returned by the API endpoint determines
the exact response type. The return type is documented for each endpoint.

An :class:`~fastf1.ergast.interface.ErgastSimpleResponse` wraps a Pandas
``DataFrame`` directly.

An :class:`~fastf1.ergast.interface.ErgastMultiResponse` consists of a
descriptive ``DataFrame``
(:attr:`~fastf1.ergast.interface.ErgastMultiResponse.description`)
and a list of ``DataFrames`` that contain the main content of the response
(:attr:`~fastf1.ergast.interface.ErgastMultiResponse.content`).


General Options
...............

The following arguments are available as default values on :class:`Ergast` or
individually for each endpoint method:

    - ``result_type`` ('raw' or 'pandas'): selects between raw response or
        Pandas DataFrame responses

    - ``auto_cast`` (`bool`): selects whether all values are automatically
        cast from their default string representation to the most appropriate
        data type



API Reference
-------------

Main Interface
..............


.. autoclass:: Ergast
    :members:


Response Objects
................

.. autoclass:: fastf1.ergast.interface.ErgastRawResponse
    :members:

.. autoclass:: fastf1.ergast.interface.ErgastSimpleResponse
    :members:

.. autoclass:: fastf1.ergast.interface.ErgastMultiResponse
    :members:
    :undoc-members:

.. autoclass:: fastf1.ergast.interface.ErgastResultFrame
    :members:

"""

import fastf1.ergast.interface

# imports for exposed names
from fastf1.ergast.interface import Ergast  # noqa: F401
from fastf1.ergast.legacy import \
    fetch_day, \
    fetch_weekend, \
    fetch_season, \
    fetch_results  # noqa: F401


@property
def base_url():
    # TODO warn
    return fastf1.ergast.interface.BASE_URL
