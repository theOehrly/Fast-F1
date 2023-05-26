from fastf1.internals.pandas_extensions import _unsafe_create_df_fast

import numpy as np
import pandas as pd


def test_fast_df_creation():
    data = {'A': [1, 2, 3], 'B': [1.0, 2.0, 3.0], 3: ['a', 'b', 'c']}

    # need to explicitly force numpy dtypes to match pandas defaults
    dtypes = ['int64', 'float64', 'object']

    df_safe = pd.DataFrame(data)

    arrays = list(np.array(d, dtype=t) for d, t in zip(data.values(), dtypes))
    df_fast = _unsafe_create_df_fast(
        arrays=arrays, columns=list(data.keys())
    )

    pd.testing.assert_frame_equal(df_safe, df_fast)
