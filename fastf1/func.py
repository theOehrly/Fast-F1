"""
:mod:`fastf1.func` - General functions
======================================
"""

import numpy as np


def min_index(_iterable):
    """Return the index of the minimum value in an iterable

    :param _iterable: any iterable
    """
    return _iterable.index(min(_iterable))


def max_index(_iterable):
    """Return the index of the maximum value in an iterable

    :param _iterable: any iterable
    """
    return _iterable.index(max(_iterable))


def reject_outliers(data, *secondary, m=2.):
    """Reject outliers from a numpy array.

    Calculates the deviation of each value from the median of the arrays values. Then calculates the median of
    all deviations. If a values deviation is greater than m times the median deviation, it is removed.
    An arbitrary number of additional arrays can be passed to this function. For each value that is removed
    from the reference array, the value at the corresponding index is removed from the other arrays.

    :param data: reference array based on which the outliers are determined
    :type data: numpy.array
    :param secondary: an arbitrary number of additional arrays
    :type secondary: numpy.array
    :param m: factor by which the deviation of a value may be greater than the median deviation
    :type m: int or float
    :return: the arrays which were passed in, same order
    """
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d/mdev if mdev else 0.

    ret_secondary = list()
    for i in range(len(secondary)):
        ret_secondary.append(secondary[i][s < m])

    return data[s < m], *ret_secondary
