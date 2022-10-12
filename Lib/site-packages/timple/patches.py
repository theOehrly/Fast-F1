import numpy as np
import datetime


def get_patched_date2num(mpl):
    """Returns a patched version of `matplotlib.dates.date2num`"""
    def date2num(d):
        """
        Convert datetime objects to Matplotlib dates.

        Parameters
        ----------
        d : `datetime.datetime` or `numpy.datetime64` or sequences of these

        Returns
        -------
        float or sequence of floats
            Number of days since the epoch.  See `.get_epoch` for the
            epoch, which can be changed by :rc:`date.epoch` or `.set_epoch`. If
            the epoch is "1970-01-01T00:00:00" (default) then noon Jan 1 1970
            ("1970-01-01T12:00:00") returns 0.5.

        Notes
        -----
        The Gregorian calendar is assumed; this is not universal practice.
        For details see the module docstring.
        """
        # this code is copied from matplotlib with the only modification
        # being the added block of code that converts pandas nat
        if hasattr(d, "values"):
            # this unpacks pandas series or dataframes...
            d = d.values

        # make an iterable, but save state to unpack later:
        iterable = np.iterable(d)
        if not iterable:
            d = [d]

        d = np.asarray(d)
        if not d.size:
            # deals with an empty array...
            return d.astype('float64')

        if hasattr(d.take(0), 'value'):
            # elements are pandas objects; temporarily convert data to numbers
            # pandas nat is defined as the minimum value of int64,
            # replace all 'min int' values with the string 'nat' and convert
            # the array to the dtype of the first non-nat value
            values = np.asarray([x.value for x in d], dtype='object')
            nat_mask = (np.iinfo('int64').min == values)
            if not all(nat_mask):
                _dtype = d[~nat_mask].take(0).to_numpy().dtype
            else:
                _dtype = 'timedelta64[us]'  # default in case of all NaT
            d = np.where(nat_mask, 'nat', values).astype(_dtype)

        # convert to datetime64 arrays, if not already:
        if not np.issubdtype(d.dtype, np.datetime64):
            # datetime arrays
            if not d.size:
                # deals with an empty array...
                return d
            tzi = getattr(d[0], 'tzinfo', None)
            if tzi is not None:
                # make datetime naive:
                d = [dt.astimezone(mpl.dates.UTC).replace(tzinfo=None)
                     for dt in d]
                d = np.asarray(d)
            d = d.astype('datetime64[us]')

        d = mpl.dates._dt64_to_ordinalf(d)

        return d if iterable else d[0]

    return date2num


def get_patched_is_natively_supported(mpl):
    """Returns a patched version of
    `matplotlib.units._is_natively_supported`"""
    mpl_native = mpl.units._is_natively_supported

    def is_natively_supported(x, *args, **kwargs):
        # returns false if x is a timedelta
        # calls matplotlib's native function for all other dtypes
        patch_types = (datetime.timedelta, np.timedelta64)
        if isinstance(x, patch_types):
            return False
        if np.iterable(x):
            if (isinstance(x, np.ndarray)
                    and np.issubdtype(x.dtype, 'timedelta64')):
                return False

            try:
                if hasattr(x[0], 'value'):
                    # pandas nat is defined as the minimum value of int64,
                    # remove all values which are equal to min int
                    values = np.asarray([elem.value for elem in x],
                                        dtype='object')
                    mask = (np.iinfo('int64').min == values)
                    x = x[~mask]
            except IndexError:
                pass

        return mpl_native(x, *args, **kwargs)

    return is_natively_supported


def get_patched_registry(mpl):
    mpl_native = mpl.units.Registry.get_converter

    def get_converter(self, x):
        try:
            if np.iterable(x) and hasattr(x[0], 'value'):
                # pandas nat is defined as the minimum value of int64,
                # remove all values which are equal to min int
                values = np.asarray([elem.value for elem in x], dtype='object')
                mask = (np.iinfo('int64').min == values)
                x = x[~mask]
        except IndexError:
            pass

        return mpl_native(self, x)

    return get_converter
