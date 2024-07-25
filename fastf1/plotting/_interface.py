import dataclasses
import warnings
from collections.abc import Sequence
from typing import (
    Any,
    Literal,
    Optional,
    Union
)

import matplotlib.axes
import matplotlib.legend

from fastf1.core import Session
from fastf1.internals.fuzzy import fuzzy_matcher
from fastf1.plotting._backend import _load_drivers_from_f1_livetiming
from fastf1.plotting._base import (
    _Driver,
    _DriverTeamMapping,
    _logger,
    _normalize_string,
    _Team
)
from fastf1.plotting._constants import Constants as _Constants


_DEFAULT_COLOR_MAP: Literal['fastf1', 'official'] = 'fastf1'
_DRIVER_TEAM_MAPPINGS = dict()


def _get_driver_team_mapping(
        session: Session
) -> "_DriverTeamMapping":
    # driver-team mappings are generated once for each session and then reused
    # on future calls
    api_path = session.api_path
    year = str(session.event['EventDate'].year)

    if api_path not in _DRIVER_TEAM_MAPPINGS:
        teams = _load_drivers_from_f1_livetiming(
            api_path=api_path, year=year
        )
        mapping = _DriverTeamMapping(year, teams)
        _DRIVER_TEAM_MAPPINGS[api_path] = mapping

    return _DRIVER_TEAM_MAPPINGS[api_path]


def _get_driver(
        identifier: str, session: Session, *, exact_match: bool = False
) -> _Driver:
    if exact_match:
        return _get_driver_exact(identifier, session)
    return _get_driver_fuzzy(identifier, session)


def _get_driver_fuzzy(identifier: str, session: Session) -> _Driver:
    dtm = _get_driver_team_mapping(session)
    identifier = _normalize_string(identifier).lower()

    # try driver abbreviation first
    if (abb := identifier.upper()) in dtm.drivers_by_abbreviation:
        return dtm.drivers_by_abbreviation[abb]

    # check for an exact driver name match
    if identifier in dtm.drivers_by_normalized:
        return dtm.drivers_by_normalized[identifier]

    # check for exact partial string match
    for normalized_driver in dtm.drivers_by_normalized.keys():
        if identifier in normalized_driver:
            return dtm.drivers_by_normalized[normalized_driver]

    # do fuzzy string matching
    drivers = list(dtm.drivers_by_normalized.values())
    strings = [[driver.normalized_value, ] for driver in drivers]
    index, exact = fuzzy_matcher(query=identifier,
                                 reference=strings,
                                 abs_confidence=0.35,
                                 rel_confidence=0.30)
    normalized_driver = drivers[index].normalized_value

    if not exact:
        _logger.warning(f"Correcting user input '{identifier}' to "
                        f"'{normalized_driver}'")

    return dtm.drivers_by_normalized[normalized_driver]


def _get_driver_exact(identifier: str, session: Session) -> _Driver:
    dtm = _get_driver_team_mapping(session)
    identifier = _normalize_string(identifier).lower()

    # try driver abbreviation first
    if (abb := identifier.upper()) in dtm.drivers_by_abbreviation:
        return dtm.drivers_by_abbreviation[abb]

    # check for an exact driver name match
    if identifier in dtm.drivers_by_normalized:
        return dtm.drivers_by_normalized[identifier]

    raise KeyError(f"No driver found for '{identifier}' (exact match only)")


def _get_team(
        identifier: str, session: Session, *, exact_match=False
) -> _Team:
    if exact_match:
        return _get_team_exact(identifier, session)
    return _get_team_fuzzy(identifier, session)


def _get_team_fuzzy(identifier: str, session: Session) -> _Team:
    dtm = _get_driver_team_mapping(session)
    identifier = _normalize_string(identifier).lower()

    # remove common non-unique words
    for word in ('racing', 'team', 'f1', 'scuderia'):
        identifier = identifier.replace(word, "")

    # check for an exact team name match
    if identifier in dtm.teams_by_normalized.keys():
        return dtm.teams_by_normalized[identifier]

    # check full match with full team name or for exact partial string
    # match with normalized team name
    for normalized, team in dtm.teams_by_normalized.items():
        if (identifier == team.value.casefold()) or (identifier in normalized):
            return dtm.teams_by_normalized[normalized]

    # do fuzzy string match
    teams = list(dtm.teams_by_normalized.values())
    strings = [[team.normalized_value, ] for team in teams]
    index, exact = fuzzy_matcher(query=identifier,
                                 reference=strings,
                                 abs_confidence=0.35,
                                 rel_confidence=0.30)
    normalized_team_name = teams[index].normalized_value

    if not exact:
        _logger.warning(f"Correcting user input '{identifier}' to "
                        f"'{normalized_team_name}'")

    return dtm.teams_by_normalized[normalized_team_name]


def _get_team_exact(identifier: str, session: Session) -> _Team:
    dtm = _get_driver_team_mapping(session)
    identifier = _normalize_string(identifier).lower()

    # check for an exact normalized team name match
    if identifier in dtm.teams_by_normalized.keys():
        return dtm.teams_by_normalized[identifier]

    # check full match with full team name
    for normalized, full in dtm.teams_by_normalized.items():
        if identifier == full.value.casefold():
            return dtm.teams_by_normalized[normalized]

    raise KeyError(f"No team found for '{identifier}' (exact match only)")


def _get_driver_color(
        identifier: str,
        session: Session,
        *,
        colormap: str = 'default',
        exact_match: bool = False,
        _variants: bool = False
) -> str:
    driver = _get_driver(identifier, session, exact_match=exact_match)
    team_name = driver.team.normalized_value

    return _get_team_color(team_name, session, colormap=colormap,
                           exact_match=True)


def _get_team_color(
        identifier: str,
        session: Session,
        *,
        colormap: str = 'default',
        exact_match: bool = False
) -> str:
    dtm = _get_driver_team_mapping(session)

    if dtm.year not in _Constants.keys():
        raise ValueError(f"No team colors for year '{dtm.year}'")

    team = _get_team(
        identifier, session, exact_match=exact_match
    )

    if colormap == 'default':
        colormap = _DEFAULT_COLOR_MAP

    if colormap == 'fastf1':
        return team.constants.TeamColor.FastF1
    elif colormap == 'official':
        return team.constants.TeamColor.Official
    else:
        raise ValueError(f"Invalid colormap '{colormap}'")


def get_team_name(
        identifier: str,
        session: Session,
        *,
        short: bool = False,
        exact_match: bool = False
) -> str:
    """
    Get a full or shortened team name based on a recognizable and identifiable
    part of the team name.

    The short version of the team name is intended for saving space when
    annotating plots and may skip parts of the official team name, for example
    "Haas F1 Team" becomes just "Haas".

    Args:
        identifier: a recognizable part of the team name
        session: the session for which the data should be obtained
        short: if True, a shortened version of the team name will be returned
        exact_match: match the identifier exactly (case-insensitive, special
            characters are converted to their nearest ASCII equivalent)
    """
    team = _get_team(identifier, session, exact_match=exact_match)

    if short:
        return team.constants.ShortName

    return team.value


def get_team_name_by_driver(
        identifier: str,
        session: Session,
        *,
        short: bool = False,
        exact_match: bool = False
) -> str:
    """
    Get a full team name based on a driver's abbreviation or based on a
    recognizable and identifiable part of a driver's name.

    Alternatively, a shortened version of the team name can be returned. The
    short version is intended for saving as much space as possible when
    annotating plots and may skip parts of the official team name.

    Args:
        identifier: driver abbreviation or recognizable part of the driver name
        session: the session for which the data should be obtained
        short: if True, a shortened version of the team name will be returned
        exact_match: match the identifier exactly (case-insensitive, special
            characters are converted to their nearest ASCII equivalent)
    """
    driver = _get_driver(identifier, session, exact_match=exact_match)
    team = driver.team

    if short:
        return team.constants.ShortName

    return team.value


def get_team_color(
        identifier: str,
        session: Session,
        *,
        colormap: str = 'default',
        exact_match: bool = False
) -> str:
    """
    Get a team color based on a recognizable and identifiable part of
    the team name.

    The team color is returned as a hexadecimal RGB color code.

    Args:
        identifier: a recognizable part of the team name
        session: the session for which the data should be obtained
        colormap: one of ``'default'``, ``'fastf1'`` or ``'official'``.
            The default colormap is ``'fastf1'``. Use
            :func:`~fastf1.plotting.set_default_colormap` to change it.
        exact_match: match the identifier exactly (case-insensitive, special
            characters are converted to their nearest ASCII equivalent)

    Returns:
        A hexadecimal RGB color code
    """
    return _get_team_color(identifier, session,
                           colormap=colormap,
                           exact_match=exact_match)


def get_driver_name(
        identifier: str, session: Session, *, exact_match: bool = False
) -> str:
    """
    Get a full driver name based on the driver's abbreviation or based on
    a recognizable and identifiable part of the driver's name.

    Args:
        identifier: driver abbreviation or recognizable part of the driver name
        session: the session for which the data should be obtained
        exact_match: match the identifier exactly (case-insensitive, special
            characters are converted to their nearest ASCII equivalent)
    """
    driver = _get_driver(identifier, session, exact_match=exact_match)
    return driver.value


def get_driver_abbreviation(
        identifier: str, session: Session, *, exact_match: bool = False
) -> str:
    """
    Get a driver's abbreviation based on a recognizable and identifiable
    part of the driver's name.

    Note that the driver's abbreviation, if given exactly, is also a valid
    identifier. In this case the same value is returned as was given as the
    identifier.

    Args:
        identifier: recognizable part of the driver's name (or the
            driver's abbreviation)
        session: the session for which the data should be obtained
        exact_match: match the identifier exactly (case-insensitive, special
            characters are converted to their nearest ASCII equivalent)
    """
    driver = _get_driver(identifier, session, exact_match=exact_match)
    return driver.abbreviation


def get_driver_names_by_team(
        identifier: str, session: Session, *, exact_match: bool = False
) -> list[str]:
    """
    Get a list of full names of all drivers that drove for a team in a given
    session based on a recognizable and identifiable part of the team name.

    Args:
        identifier: a recognizable part of the team name
        session: the session for which the data should be obtained
        exact_match: match the identifier exactly (case-insensitive, special
            characters are converted to their nearest ASCII equivalent)
    """
    team = _get_team(identifier, session, exact_match=exact_match)
    return [driver.value for driver in team.drivers]


def get_driver_abbreviations_by_team(
        identifier: str, session: Session, *, exact_match: bool = False
) -> list[str]:
    """
    Get a list of abbreviations of all drivers that drove for a team in a given
    session based on a recognizable and identifiable part of the team name.

    Args:
        identifier: a recognizable part of the team name
        session: the session for which the data should be obtained
        exact_match: match the identifier exactly (case-insensitive, special
            characters are converted to their nearest ASCII equivalent)
    """
    team = _get_team(identifier, session, exact_match=exact_match)
    return [driver.abbreviation for driver in team.drivers]


def get_driver_color(
        identifier: str,
        session: Session,
        *,
        colormap: str = 'default',
        exact_match: bool = False
) -> str:
    """
    Get the color that is associated with a driver based on the driver's
    abbreviation or based on a recognizable and identifiable part of the
    driver's name.

    .. note:: This will simply return the team color of the team that the
        driver participated for in this session. Contrary to older versions
        of FastF1, there are no separate colors for each driver. You should use
        styling options other than color if you need to differentiate drivers
        of the same team. The function
        :func:`~fastf1.plotting.get_driver_style` can help you to customize
        the plot styling for each driver.

    Args:
        identifier: driver abbreviation or recognizable part of the driver name
        session: the session for which the data should be obtained
        colormap: one of ``'default'``, ``'fastf1'`` or ``'official'``.
            The default colormap is ``'fastf1'``. Use
            :func:`~fastf1.plotting.set_default_colormap` to change it.
        exact_match: match the identifier exactly (case-insensitive, special
            characters are converted to their nearest ASCII equivalent)

    Returns:
        A hexadecimal RGB color code

    """
    return _get_driver_color(identifier, session, colormap=colormap,
                             exact_match=exact_match)


def get_driver_style(
        identifier: str,
        style: Union[str, Sequence[str], Sequence[dict]],
        session: Session,
        *,
        colormap: str = 'default',
        additional_color_kws: Union[list, tuple] = (),
        exact_match: bool = False
) -> dict[str, Any]:
    """
    Get a plotting style that is unique for a driver based on the driver's
    abbreviation or based on a recognizable and identifiable part of the
    driver's name.

    This function simplifies the task of generating unique and easily
    distinguishable visual styles for multiple drivers in a plot.
    Primarily, the focus is on plotting with Matplotlib, but it is possible
    to customize the behaviour for compatibility with other plotting libraries.

    The general idea for creating visual styles is as follows:

    1. Set the primary color of the style to the color of the team for
       which a driver is driving. This may be the line color in a line plot,
       the marker color in a scatter plot, and so on.

    2. Use one or multiple other styling options (line style, markers, ...)
       to differentiate drivers in the same team.

    .. note:: It cannot be guaranteed that the styles are consistent throughout
        a full season, especially in case of driver changes within a team.


    **Option 1**: Rely on built-in styling options

    By default, this function supports the following Matplotlib plot arguments:
    ``linestyle``, ``marker``, ``color``, ``facecolor``, ``edgecolor`` as well
    as almost all other color-related arguments.

    The styling options include one color for each team and up to four
    different line styles and marker styles within a team. That means that no
    more than four different drivers are supported for a team in a single
    session. This should be sufficent in almost all scenarios.

    The following example obtains the driver style for Alonso and Stroll in a
    race in the 2023 season. The drivers should be represented using the
    ``color`` and ``marker`` arguments, as may be useful in a scatter plot.
    Both drivers were driving for the Aston Martin team, therefore, both
    automatically get assigned the same color, which is the Aston Martin team
    color. But both drivers get assigned a different marker style, so they can
    be uniquely identified in the plot.

    Example:

    .. doctest::

        >>> from fastf1 import get_session
        >>> from fastf1.plotting import get_driver_style
        >>> session = get_session(2023, 10, 'R')
        >>> get_driver_style('ALO', ['color', 'marker'], session)
        {'color': '#00665e', 'marker': 'x'}
        >>> get_driver_style('STR', ['color', 'marker'], session)
        {'color': '#00665e', 'marker': 'o'}

    **Option 2**: Provide a custom list of styling variants

    To allow for almost unlimited styling options, it is possible to specify
    custom styling variants. These are not tied to any specific plotting
    library.

    In the following example, a list with two custom stlyes is defined that are
    then used to generate driver specific styles. Each style is represented by
    a dictionary of keywords and values.

    The first driver in a team gets assigned the first style, the second driver
    the second style and so on (if there are more than two drivers). It is
    necessary to define at least as many styles as there are drivers in a team.

    The following things need to be noted:

    1. The notion of first or second driver does not refer to any particular
    reference and no specific order for drivers within a team is intended or
    guranteed.

    2. Any color-related key can make use of the "magic" ``'auto'`` value as
    shown with Alonso in this example. When the color value is set to
    ``'auto'`` it will automatically be replaced with the team color for this
    driver. All color keywords that are used in Matplotlib should be recognized
    automatically. You can define custom arguments as color arguments through
    the ``additional_color_kws`` argument.

    3. Each style dictionary can contain arbitrary keys and value. Therefore,
    you are not limited to any particular plotting library.

    Example:

    .. doctest::

        >>> from fastf1 import get_session
        >>> from fastf1.plotting import get_driver_style
        >>> session = get_session(2023, 10, 'R')
        >>> my_styles = [
        ...     {'linestyle': 'solid', 'color': 'auto', 'custom_arg': True},
        ...     {'linestyle': 'dotted', 'color': '#FF0060', 'other_arg': 10}
        ... ]
        >>> get_driver_style('ALO', my_styles, session)
        {'linestyle': 'solid', 'color': '#00665e', 'custom_arg': True}
        >>> get_driver_style('STR', my_styles, session)
        {'linestyle': 'dotted', 'color': '#FF0060', 'other_arg': 10}

    Args:
        identifier: driver abbreviation or recognizable part of the driver name
        style: list of matplotlib plot arguments that should be used for
            styling or a list of custom style dictionaries
        session: the session for which the data should be obtained
        colormap: one of ``'default'``, ``'fastf1'`` or ``'official'``.
            The default colormap is ``'fastf1'``. Use
            :func:`~fastf1.plotting.set_default_colormap` to change it.
        additional_color_kws: A list of keys that should additionally be
            treated as colors. This is most usefull for making the magic
            ``'auto'`` color work with custom styling options.
        exact_match: match the identifier exactly (case-insensitive, special
            characters are converted to their nearest ASCII equivalent)

    Returns: a dictionary of plot style arguments that can be directly passed
        to a matplotlib plot function using the ``**`` expansion operator


    .. minigallery:: fastf1.plotting.get_driver_style
        :add-heading:
    """
    stylers = {
        'linestyle': ['solid', 'dashed', 'dashdot', 'dotted'],
        'marker': ['x', 'o', '^', 'D']
    }

    # color keyword arguments that are supported by various matplotlib
    # functions
    color_kwargs = (
        # generic
        'color', 'colors', 'c',
        # .plot
        'gapcolor',
        'markeredgecolor', 'mec',
        'markerfacecolor', 'mfc',
        'markerfacecoloralt', 'mfcalt',
        # .scatter
        'facecolor', 'facecolors', 'fc',
        'edgecolor', 'edgecolors', 'ec',
        # .errorbar
        'ecolor',
        # add user defined color keyword arguments
        *additional_color_kws
    )

    driver = _get_driver(identifier, session, exact_match=exact_match)
    team = driver.team
    idx = team.drivers.index(driver)

    if not style:
        # catches empty list, tuple, str
        raise ValueError("The provided style info is empty!")

    if isinstance(style, str):
        style = [style]

    plot_style = dict()

    if isinstance(style[0], str):
        # generate the plot style based on the provided keyword
        # arguments
        for opt in style:
            if opt in color_kwargs:
                value = _get_team_color(team.normalized_value,
                                        session,
                                        colormap=colormap,
                                        exact_match=True)
            elif opt in stylers:
                value = stylers[opt][idx]
            else:
                raise ValueError(f"'{opt}' is not a supported styling "
                                 f"option")
            plot_style[opt] = value

    else:
        try:
            custom_style = style[idx]
        except IndexError:
            raise ValueError(f"The provided custom style info does not "
                             f"contain enough variants! (Has: {len(style)}, "
                             f"Required: {idx})")

        if not isinstance(custom_style, dict):
            raise ValueError("The provided style info has an invalid format!")

        # copy the correct user provided style and replace any 'auto'
        # colors with the correct color value
        plot_style = custom_style.copy()
        for kwarg in color_kwargs:
            if plot_style.get(kwarg, None) == 'auto':
                color = _get_team_color(team.normalized_value,
                                        session,
                                        colormap=colormap,
                                        exact_match=True)
                plot_style[kwarg] = color

    return plot_style


def get_compound_color(compound: str, session: Session) -> str:
    """
    Get the compound color as hexadecimal RGB color code for a given compound.

    Args:
        compound: the name of the compound
        session: the session for which the data should be obtained

    Returns:
        A hexadecimal RGB color code
    """
    year = str(session.event['EventDate'].year)
    return _Constants[year].CompoundColors[compound.upper()]


def get_compound_mapping(session: Session) -> dict[str, str]:
    """
    Returns a dictionary that maps compound names to their associated
    colors. The colors are given as hexadecimal RGB color codes.

    Args:
        session: the session for which the data should be obtained

    Returns:
        dictionary mapping compound names to RGB hex colors
    """
    year = str(session.event['EventDate'].year)
    return _Constants[year].CompoundColors.copy()


def get_driver_color_mapping(
        session: Session, *, colormap: str = 'default',
) -> dict[str, str]:
    """
    Returns a dictionary that maps driver abbreviations to their associated
    colors. The colors are given as hexadecimal RGB color codes.

    Args:
        session: the session for which the data should be obtained
        colormap: one of ``'default'``, ``'fastf1'`` or ``'official'``.
            The default colormap is ``'fastf1'``. Use
            :func:`~fastf1.plotting.set_default_colormap` to change it.
    Returns:
        dictionary mapping driver abbreviations to RGB hex colors
    """
    dtm = _get_driver_team_mapping(session)

    if colormap == 'default':
        colormap = _DEFAULT_COLOR_MAP

    if colormap == 'fastf1':
        colors = {
            abb: driver.team.constants.TeamColor.FastF1
            for abb, driver in dtm.drivers_by_abbreviation.items()
        }
    elif colormap == 'official':
        colors = {
            abb: driver.team.constants.TeamColor.Official
            for abb, driver in dtm.drivers_by_abbreviation.items()
        }
    else:
        raise ValueError(f"Invalid colormap '{colormap}'")

    return colors


def list_team_names(session: Session, *, short: bool = False) -> list[str]:
    """Returns a list of team names of all teams in the ``session``.

    By default, the full team names are returned. Use the ``short`` argument
    to get shortened versions of the team names instead.

    Args:
        session: the session for which the data should be obtained
        short: if True, a list of the shortened team names is returned

    Returns:
        a list of team names
    """
    dtm = _get_driver_team_mapping(session)

    if short:
        return list(team.constants.ShortName
                    for team in dtm.teams_by_normalized.values())

    return list(team.value for team in dtm.teams_by_normalized.values())


def list_driver_abbreviations(session: Session) -> list[str]:
    """Returns a list of abbreviations of all drivers in the ``session``."""
    dtm = _get_driver_team_mapping(session)
    return list(dtm.drivers_by_abbreviation.keys())


def list_driver_names(session: Session) -> list[str]:
    """Returns a list of full names of all drivers in the ``session``."""
    dtm = _get_driver_team_mapping(session)
    return list(driver.value for driver in dtm.drivers_by_normalized.values())


def list_compounds(session: Session) -> list[str]:
    """Returns a list of all compound names for this season (not session)."""
    year = str(session.event['EventDate'].year)
    return list(_Constants[year].CompoundColors.keys())


def add_sorted_driver_legend(
    ax: matplotlib.axes.Axes, session: Session, *args, **kwargs
):
    """
    Adds a legend to the axis where drivers are grouped by team and within each
    team they are shown in the same order that is used for selecting plot
    styles.

    This function is a drop-in replacement for calling Matplotlib's
    ``ax.legend()`` method. It can only be used when driver names or driver
    abbreviations are used as labels for the legend.

    This function supports the same ``*args`` and ``**kwargs`` as
    Matplotlib's ``ax.legend()``, including the ``handles`` and ``labels``
    arguments. Check the Matplotlib documentation for more information.

    There is no particular need to use this function except to make the
    legend more visually pleasing.

    Args:
        ax: An instance of a Matplotlib ``Axes`` object
        session: the session for which the data should be obtained
        *args: Matplotlib legend args
        **kwargs: Matplotlib legend kwargs

     Returns:
        ``matplotlib.legend.Legend``

    .. minigallery:: fastf1.plotting.add_sorted_driver_legend
        :add-heading:

    """
    dtm = _get_driver_team_mapping(session)

    try:
        ret = matplotlib.legend._parse_legend_args([ax], *args, **kwargs)
        if len(ret) == 3:
            handles, labels, kwargs = ret
            extra_args = []
        else:
            handles, labels, extra_args, kwargs = ret

    except AttributeError:
        warnings.warn("Failed to parse optional legend arguments correctly.",
                      UserWarning)
        extra_args = []
        kwargs.pop('handles', None)
        kwargs.pop('labels', None)
        handles, labels = ax.get_legend_handles_labels()

    teams_list = list(dtm.teams_by_normalized.values())
    driver_list = list(dtm.drivers_by_normalized.values())

    # create an intermediary list where each element is a tuple that
    # contains (team_idx, driver_idx, handle, label). Then sort this list
    # based on the team_idx and driver_idx. As a result, drivers from the
    # same team will be next to each other and in the same order as their
    # styles are cycled.
    ref = list()
    for hdl, lbl in zip(handles, labels):
        driver = _get_driver(lbl, session)
        team = driver.team

        team_idx = teams_list.index(team)
        driver_idx = driver_list.index(driver)

        ref.append((team_idx, driver_idx, hdl, lbl))

    # sort based only on team_idx and driver_idx (i.e. first two entries)
    ref.sort(key=lambda e: e[:2])

    handles_new = list()
    labels_new = list()
    for elem in ref:
        handles_new.append(elem[2])
        labels_new.append(elem[3])

    return ax.legend(handles_new, labels_new, *extra_args, **kwargs)


def set_default_colormap(colormap: str):
    """
    Set the default colormap that is used for color lookups.

    Args:
        colormap: one of ``'fastf1'`` or ``'official'``
    """
    global _DEFAULT_COLOR_MAP
    if colormap not in ('fastf1', 'official'):
        raise ValueError(f"Invalid colormap '{colormap}'")
    _DEFAULT_COLOR_MAP = colormap


def override_team_constants(
        identifier: str,
        session: Session,
        *,
        short_name: Optional[str] = None,
        official_color: Optional[str] = None,
        fastf1_color: Optional[str] = None
):
    """
    Override the default team constants for a specific team.

    This function is intended for advanced users who want to customize the
    default team constants. The changes are only applied for the current
    session and do not persist.

    Args:
        identifier: A part of the team name. Note that this function does
            not support fuzzy matching and will raise a ``KeyError`` if no
            exact and unambiguous match is found!
        session: The session for which the override should be applied
        short_name: New value for the short name of the team
        official_color: New value for the team color in the "official"
            color map; must be a hexadecimal RGB color code
        fastf1_color: New value for the team color in the "fastf1" color map;
            must be a hexadecimal RGB color code
    """
    team = _get_team(identifier, session, exact_match=True)

    colors = team.constants.TeamColor
    if official_color is not None:
        colors = dataclasses.replace(colors, Official=official_color)
    if fastf1_color is not None:
        colors = dataclasses.replace(colors, FastF1=fastf1_color)
    if (official_color is not None) or (fastf1_color is not None):
        team.constants = dataclasses.replace(team.constants, TeamColor=colors)

    if short_name is not None:
        team.constants = dataclasses.replace(team.constants,
                                             ShortName=short_name)
