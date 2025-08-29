.. _exceptions:

Exceptions
============

Generic Exceptions
------------------

.. autoclass:: fastf1.RateLimitExceededError


Data Loading Exceptions
-----------------------

.. autoclass:: fastf1.core.NoLapDataError

.. autoclass:: fastf1.core.InvalidSessionError

.. autoclass:: fastf1._api.SessionNotAvailableError


Jolpica-F1 (Ergast) Specific Exceptions
---------------------------------------

.. _jolpica-excpetions:

.. autoclass:: fastf1.ergast.interface.ErgastError

.. autoclass:: fastf1.ergast.interface.ErgastJsonError

.. autoclass:: fastf1.ergast.interface.ErgastInvalidRequestError
