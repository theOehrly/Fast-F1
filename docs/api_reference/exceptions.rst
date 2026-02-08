.. _exceptions:

Exceptions
============

Generic Exceptions
------------------

.. autoclass:: fastf1.exceptions.FastF1CriticalError
    :show-inheritance:

.. autoclass:: fastf1.exceptions.RateLimitExceededError
    :show-inheritance:


Data Loading Exceptions
-----------------------

.. autoclass:: fastf1.exceptions.DataNotLoadedError
    :show-inheritance:

.. autoclass:: fastf1.exceptions.InvalidSessionError
    :show-inheritance:

.. autoclass:: fastf1.exceptions.NoLapDataError
    :show-inheritance:


Jolpica-F1 (Ergast) Specific Exceptions
---------------------------------------

.. _jolpica-excpetions:

.. autoclass:: fastf1.exceptions.ErgastError
    :show-inheritance:

.. autoclass:: fastf1.exceptions.ErgastJsonError
    :show-inheritance:

.. autoclass:: fastf1.exceptions.ErgastInvalidRequestError
    :show-inheritance:


Legacy Exceptions (deprecated)
------------------------------

.. autoclass:: fastf1._api.SessionNotAvailableError

