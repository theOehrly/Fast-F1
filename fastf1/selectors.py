"""
:mod:`fastf1.selectors` - Selectors module
==========================================

This module provides a set of functions to be used in combination with
:meth:`fastf1.core.Lap.sel`.
"""
import pandas as pd

QUICKLAP_THRESHOLD = 1.07

def driver(name):
    """Select driver given his three letters identifier
    """
    return lambda x: x[x['Driver'] == name]

def drivers(names):
    """Select drivers given a list of their three letters identifiers
    """
    return lambda x: x[x['Driver'].isin(names)]

def team(name):
    """Select team given its name
    """
    return lambda x: x[x['Team'] == name]

def teams(names):
    """Select teams given a list of names
    """
    return lambda x: x[x['Team'].isin(names)]

def fastest(x):
    """Select fastest lap time 
    """
    return x.loc[x['LapTime'].idxmin()]

def quicklaps(x):
    """Select laps with lap time below :attr:`QUICKLAP_THRESHOLD`
    (default 107%) of the fastest lap from the given laps set
    """
    return x[x['LapTime'] < (x['LapTime'].min() * QUICKLAP_THRESHOLD)]

