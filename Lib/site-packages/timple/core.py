"""
.. currentmodule:: timple.timple

Basic Usage
============

Timple provides locator and formatter classes for timedelta-like values.
These are similar to Matplotlib's native formatters and locators for date-like
values. They allow for nicer tick locations and labels than Matplotlib can
create natively.

Here is an example plot that shows a minimum working example for using Timple::

    import datetime
    import numpy as np
    import matplotlib.pyplot as plt
    import timple

    tmpl = timple.Timple()
    tmpl.enable()

    timedeltas = np.array([datetime.timedelta(minutes=(15 * i))
                           for i in range(100)])
    y = np.array([np.exp(-5*x/100) + np.random.random()/25
                  for x in range(0, 100)])

    plt.plot(timedeltas, y)
    plt.show()

.. image:: _static/intro_example.svg

In this example, Timple is enabled without any further customization.
Timple's :class:`AutoTimedeltaLocator` and :class:`AutoTimedeltaFormatter`
are used by default.
If you want to customize tick positions and labels, you can manually set
the locators and formatters. This allows for a more fine grained control
over the resulting plot.
See :mod:`timple.timedelta` for more information.

Timple furthermore provides the ability to optionally patch Matplotlib's date
functionality so that pandas' NaT datatype is treated like a NaN value. This
means that NaT values are then simply skipped when plotting.
"""

import numpy as np
import datetime
import matplotlib as mpl
from matplotlib import units as munits
from matplotlib import dates as mdates

from timple.timedelta import TimedeltaConverter, ConciseTimedeltaConverter
from timple import patches


class Timple:
    """
    The :class:`Timple` class is the most important part of this module.
    It will always be your starting point. It is very simple and its only
    purpose is to activate the timple module. This is done by registering
    a custom converter for timedelta values and by patching some
    internal functionality of Matplotlib.

    Usage is very straight forward::

        import timple

        tmpl = timple.Timple()
        tmpl.enable()

    This is all that is necessary to get the basic functionality.
    You can now simply plot timedelta values and reasonable tick
    locations and formats will be chosen automatically.

    If you want to have more control over the result you can find
    more information on custom tick locations and formatters in
    :mod:`timple.timedelta`

    Parameters
    ----------
    converter (str): one of 'auto', 'concise', 'default'
        Default will use the same value as set in Matplotlib's rcParams
        for 'date.converter'. If this value does not exist it will fall
        back to 'auto'.
    """
    def __init__(self, converter='default', formatter_args=None):
        if converter not in ('default', 'auto', 'concise'):
            raise ValueError("Invalid value for keyword argument 'converter'")
        self._revert_funcs = list()
        self._converter = converter
        self._formatter_args = formatter_args

    def enable(self, pd_nat_dates_support=False):
        """
        Enables Timple by patching Matplotlib and registering either
        `timedelta.TimedeltaConverter` or
        `timedelta.ConciseTimedeltaConverter`.

        After this, you can plot timedelta values and Matplotlib
        will automatically choose appropriate locators and formatter which
        Timple provides.

        If you want more control over the result, you can always specify the
        formatter and locator for a plot manually. See `timedelta` for more
        information.

        Parameters
        ----------
        pd_nat_dates_support: (Optional)
            Patch Matplotlib internal functionality to support
            pandas NaT values when plotting dates too.
        """
        revert_units_patch = self._patch_supported_units()
        self._revert_funcs.append(revert_units_patch)

        revert_converters = self._add_converters(self._formatter_args)
        self._revert_funcs.append(revert_converters)

        revert_registry = self._patch_registry()
        self._revert_funcs.append(revert_registry)

        if pd_nat_dates_support:
            revert_date2num = self._patch_date2num()
            self._revert_funcs.append(revert_date2num)

    def disable(self):
        """
        Disables Timple. Reverts the applied patch and unregisters the
        timedelta converter.
        """
        for revert in self._revert_funcs:
            revert()

    def _add_converters(self, formatter_args):
        # register the appropriate matplotlib converter
        # return a function that reverts this change
        if self._converter == 'default':
            try:
                # option only exists in matplotlib >= 3.4.0
                conv_type = mpl.rcParams['date.converter']
                if conv_type not in ('auto', 'concise'):
                    raise ValueError
            except (KeyError, ValueError):
                conv_type = 'auto'
        else:
            conv_type = self._converter

        if conv_type == 'concise':
            timedelta_converter = ConciseTimedeltaConverter
        else:
            timedelta_converter = TimedeltaConverter

        conv_inst = timedelta_converter(formatter_args)
        munits.registry[np.timedelta64] = conv_inst
        munits.registry[datetime.timedelta] = conv_inst

        def revert():
            del munits.registry[np.timedelta64]
            del munits.registry[datetime.timedelta]

        return revert

    def _patch_supported_units(self):
        # patch matplotlibs ._is_natively_supported function
        # timedelta is a Number and therefore 'supported' by default
        # make it 'unsupported' so matplotlib will use the converter
        # return a function that reverts this change
        orig_func = munits._is_natively_supported

        patched = patches.get_patched_is_natively_supported(mpl)

        munits._is_natively_supported = patched

        def revert():
            munits._is_natively_supported = orig_func

        return revert

    def _patch_registry(self):
        # patch matplotlib.units.registry.get_converter
        # mainly necessary for special case whr e first element of an array
        # is pandas.NaT (pandas.NaT is always an instance of datetime.datetime
        # and therefore not representative of the arrays datatype
        orig_func = munits.Registry.get_converter

        patched = patches.get_patched_registry(mpl)
        munits.Registry.get_converter = patched

        def revert():
            munits.Registry.get_converter = orig_func

        return revert

    def _patch_date2num(self):
        # patch matplotlibs dates.date2num function to add support for
        # pandas nat
        # return a function that reverts this change
        orig_func = mdates.date2num

        patched = patches.get_patched_date2num(mpl)
        mdates.date2num = patched

        def revert():
            mdates.date2num = orig_func

        return revert
