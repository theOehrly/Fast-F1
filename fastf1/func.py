import numpy as np


def min_index(_iterable):
    """Return the index of the minimum value in an iterable"""
    return _iterable.index(min(_iterable))


def max_index(_iterable):
    """Return the index of the minimum value in an iterable"""
    return _iterable.index(max(_iterable))


def reject_outliers(data, *secondary, m=2.):
    """Reject outliers from a numpy array.

    Calculates the deviation of each value from the median of the arrays values. Then calculates the median of
    all deviations. If a values deviation is greater than m times the median deviation, it is removed.
    An arbitrary number of additional arrays can be passed to this function. For each value that is removed
    from the reference array, the value at the corresponding index is removed from the other arryays."""
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d/mdev if mdev else 0.

    ret_secondary = list()
    for i in range(len(secondary)):
        ret_secondary.append(secondary[i][s < m])

    return data[s < m], *ret_secondary
