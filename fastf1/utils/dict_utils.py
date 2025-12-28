from functools import reduce

def recursive_dict_get(d: dict, *keys: str, default_none: bool = False):
    """Recursive dict get. Can take an arbitrary number of keys and returns an
    empty dict if any key does not exist.
    https://stackoverflow.com/a/28225747"""
    ret = reduce(lambda c, k: c.get(k, {}), keys, d)
    if default_none and ret == {}:
        return None
    else:
        return ret