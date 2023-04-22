"""
.. warning::
    :mod:`fastf1.api` will be considered private in future releases and
    potentially be removed or changed. Please do not use functionality from
    :mod:`fastf1.api`. If you currently require functionality from there,
    please open an issue on Github with details about what you require and why.

A collection of functions to interface with the F1 web api.

.. autosummary::
   :nosignatures:

   timing_data
   timing_app_data
   car_data
   position_data
   track_status_data
   session_status_data
   race_control_messages
   lap_count
   driver_info
   weather_data
   fetch_page
   parse

"""
import warnings

from fastf1._api import *  # noqa


warnings.warn("`fastf1.api` will be considered private in future releases and "
              "potentially be removed or changed!", UserWarning)
