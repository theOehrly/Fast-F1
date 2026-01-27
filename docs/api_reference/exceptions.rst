.. _exceptions:

Exceptions
============

Generic Exceptions
------------------

.. autoclass:: fastf1.exceptions.FastF1CriticalError

.. autoclass:: fastf1.exceptions.RateLimitExceededError


Data Loading Exceptions
-----------------------

.. autoclass:: fastf1.exceptions.DataNotLoadedError

.. autoclass:: fastf1.exceptions.InvalidSessionError

.. autoclass:: fastf1.exceptions.NoLapDataError


Jolpica-F1 (Ergast) Specific Exceptions
---------------------------------------

.. _jolpica-excpetions:

.. autoclass:: fastf1.exceptions.ErgastError

.. autoclass:: fastf1.exceptions.ErgastJsonError

.. autoclass:: fastf1.exceptions.ErgastInvalidRequestError


Legacy Exceptions (deprecated)
------------------------------

.. autoclass:: fastf1._api.SessionNotAvailableError

