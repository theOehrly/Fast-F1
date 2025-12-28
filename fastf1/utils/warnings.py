from fastf1.utils.parsing import to_datetime, to_timedelta
from fastf1.utils.dict_utils import recursive_dict_get

class FastF1DataWarning(UserWarning):
    """Warning for known, recoverable data issues in Fast-F1."""
    pass