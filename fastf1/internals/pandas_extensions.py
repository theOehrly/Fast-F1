from typing import List

import numpy as np
from pandas import (
    DataFrame,
    Index,
    RangeIndex
)

from fastf1.internals import internals_logger as logger


try:
    # import internal pandas functions and objects
    from pandas.core.internals.construction import (
        BlockPlacement,
        _get_axes,
        create_block_manager_from_blocks,
        new_block_2d
    )
    from pandas.core.internals.managers import _consolidate

    # verify existence of non-public methods of public objects
    if not hasattr(Index, '_with_infer'):
        raise AttributeError

except (AttributeError, ImportError) as import_exc:
    logger.warning("Import of pandas internals failed. Performance will be "
                   "reduced.")
    logger.debug("Traceback for import failure", exc_info=import_exc)
    CREATE_DF_FAST = False
else:
    CREATE_DF_FAST = True


def create_df_fast(
        *,
        arrays: List[np.ndarray],
        columns: list,
        fallback: bool = True
) -> DataFrame:
    """Implements fast creation of DataFrames.

    This function tries to speed up DataFrame creation by skipping many
    pandas internal steps that are not required. This only works for some
    data and only if this data is correctly processed beforehand.

    In case of error, this function falls back to the official documented
    way of creating DataFrames.

    Args:
        arrays: list of 1D numpy arrays of equal length
        columns: list of column names (one name per array)
        fallback: use Pandas' default method of DataFrame creation in case
            of errors

    Returns:
        Pandas DataFrame equivalent to the one create with the default
        dataframe constructor

    """
    try:
        return _unsafe_create_df_fast(arrays, columns)
    except Exception as exc:
        if not fallback:
            raise exc
        # in case of error, use the usual but slower method
        logger.warning("Falling back to slow data frame creation!")
        logger.debug("Error during fast DataFrame creation", exc_info=exc)
        return _fallback_create_df(arrays, columns)


def _fallback_create_df(
        arrays: List[np.ndarray],
        columns: list
) -> DataFrame:
    data = {col: arr for col, arr in zip(columns, arrays)}
    return DataFrame(data)


def _fallback_if_unsupported(func):
    if not CREATE_DF_FAST:
        return _fallback_create_df
    else:
        return func


@_fallback_if_unsupported
def _unsafe_create_df_fast(
        arrays: List[np.ndarray],
        columns: list
) -> DataFrame:
    # Implements parts of pandas' internal DataFrame creation mechanics
    # but skipping unnecessary tests and most importantly sanitization and
    # validation of the data. This results in much higher performance but is
    # not necessarily safe, for obvious reasons.
    # This method should only be used in FastF1 internal code where, type
    # casting, array creation and data sanitization is very explicitly already
    # performed. Always use this method through `create_df_fast`, so that there
    # is a fallback to safe DataFrame creation in case of an error.
    index = RangeIndex(0, len(arrays[0]))
    columns = Index._with_infer(
        list(columns), copy=False, tupleize_cols=False
    )

    index, columns = _get_axes(
        len(index), len(columns), index=index, columns=columns
    )

    block_values = list()
    for n, arr in enumerate(arrays):
        values = arr.reshape(-1, 1).T
        nb = new_block_2d(values, placement=BlockPlacement(n))
        block_values.append(nb)

    block_values = list(_consolidate(tuple(block_values)))

    mgr = create_block_manager_from_blocks(
            block_values, [columns, index], verify_integrity=False
    )

    df = DataFrame(mgr)

    return df
