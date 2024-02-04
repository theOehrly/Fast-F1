import json
import unicodedata
from collections import defaultdict
from typing import (
    Dict,
    List,
    Optional,
    Sequence,
    Union
)

import matplotlib.axes
from thefuzz import fuzz

from fastf1._api import driver_info
from fastf1.core import Session
from fastf1.plotting._constants import Constants
from fastf1.req import Cache


def _get_latest_api_path() -> (str, str):
    # find out what the "current" season is; this is the latest season
    # for which data is available, therefore before the first session
    # of any year, the "current" season is still last year
    res_seasons = Cache.requests_get(
        'https://livetiming.formula1.com/static/Index.json'
    )
    if res_seasons.status_code != 200:
        raise ValueError("Unable to fetch driver list")
    year = str(json.loads(
        res_seasons.content.decode('utf-8-sig')
    )['Years'][-1].get('Year'))
    # find the latest session of the current season
    res_meetings = Cache.requests_get(
        f'https://livetiming.formula1.com/static/{year}/Index.json'
    )
    if res_meetings.status_code != 200:
        raise ValueError("Unable to fetch driver list")
    meeting_info = json.loads(res_meetings.content.decode('utf-8-sig'))
    n_meetings = len(meeting_info.get('Meetings', []))
    # iterate over all session of the season in reverse and find the
    # latest session that has an api path (not necessarily every
    # session has that in case of error or if teh session is testing)
    path = None
    for i in range(n_meetings):
        sessions = meeting_info['Meetings'][-(i + 1)]['Sessions']
        for j in range(len(sessions)):
            path = sessions[-(j + 1)].get('Path', None)
            if path is not None:
                break
        if path is not None:
            break

    api_path = "/static/" + path

    return api_path, year


def _load_drivers_from_f1_livetiming(
        *, api_path: str, year: str
) -> Sequence[Dict[str, str]]:
    # load the driver information for the determined session
    drivers = driver_info(api_path)

    # parse the data into the required format
    abb_to_name: Dict[str, str] = dict()
    abb_to_full_team_name: Dict[str, str] = dict()
    name_normalized_to_abb: Dict[str, str] = dict()

    for num, driver in drivers.items():
        abb = driver.get('Tla')
        name = driver.get('FirstName') + ' ' + driver.get('LastName')
        team = driver.get('TeamName')

        abb_to_name[abb] = name
        abb_to_full_team_name[abb] = team
        name_normalized_to_abb[_normalize_name(name)] = abb

    team_name_to_full_team_name: Dict[str, str] = dict()
    full_team_name_to_team_name: Dict[str, str] = dict()
    for full_team_name in abb_to_full_team_name.values():
        normalized_full_team_name = _normalize_name(full_team_name).lower()
        for team in Constants[year].Teams:
            if team in normalized_full_team_name:
                team_name_to_full_team_name[team] = full_team_name
                full_team_name_to_team_name[full_team_name] = team

    abb_to_team: Dict[str, str] = dict()
    for abb, full_team_name in abb_to_full_team_name.items():
        abb_to_team[abb] = full_team_name_to_team_name[full_team_name]

    ret_data = (abb_to_name,
                abb_to_team,
                name_normalized_to_abb,
                team_name_to_full_team_name)

    return ret_data


_DRIVER_TEAM_MAPPINGS = dict()


def _get_driver_team_mapping(
        session: Optional[Session] = None
) -> "_DriverTeamMapping":

    if session is None:
        api_path, year = _get_latest_api_path()
    else:
        api_path = session.api_path
        year = str(session.event['EventDate'].year)

    if api_path not in _DRIVER_TEAM_MAPPINGS:
        datas = _load_drivers_from_f1_livetiming(
            api_path=api_path, year=year
        )
        mapping = _DriverTeamMapping(year, *datas)
        _DRIVER_TEAM_MAPPINGS[api_path] = mapping

    return _DRIVER_TEAM_MAPPINGS[api_path]


def _fuzzy_matcher(
        identifier: str,
        reference: Dict[str, str]
) -> str:
    # do fuzzy string matching
    key_ratios = list()
    for existing_key in reference.keys():
        ratio = fuzz.ratio(identifier, existing_key)
        key_ratios.append((ratio, existing_key))
    key_ratios.sort(reverse=True)
    if ((key_ratios[0][0] < 35)
            or (key_ratios[0][0] / key_ratios[1][0] < 1.2)):
        # ensure that the best match has a minimum accuracy (35 out of
        # 100) and that it has a minimum confidence (at least 20%
        # better than second best)
        raise KeyError
    best_matched_key = key_ratios[0][1]
    team_name = reference[best_matched_key]
    return team_name


def _normalize_name(name: str) -> str:
    # removes accents from a string and returns the closest possible
    # ascii representation (https://stackoverflow.com/a/518232)
    stripped = ''.join(c for c in unicodedata.normalize('NFD', name)
                       if unicodedata.category(c) != 'Mn')
    return stripped


class _DriverTeamMapping:
    def __init__(
            self,
            year: str,
            abb_to_name: Dict[str, str],
            abb_to_team: Dict[str, str],
            name_normalized_to_abb: Dict[str, str],
            team_name_to_full_team_name: Dict[str, str]
    ):
        self.year = year
        self.abbreviation_to_name = abb_to_name
        self.abbreviation_to_team = abb_to_team
        self.name_normalized_to_abbreviation = name_normalized_to_abb
        self.team_name_to_full_team_name = team_name_to_full_team_name

        self.team_to_abbreviations: Dict[str, List[str]] = defaultdict(list)
        for abb, team in self.abbreviation_to_team.items():
            self.team_to_abbreviations[team].append(abb)


def _get_normalized_team_name(
        identifier: str,
        *,
        session: Session
) -> str:
    dti = _get_driver_team_mapping(session)
    identifier = _normalize_name(identifier).lower()
    team_name: Optional[str] = None
    # check for an exact team name match
    if identifier in dti.team_name_to_full_team_name:
        team_name = identifier
    # check for exact partial string match
    if team_name is None:
        for _team_name in dti.team_name_to_full_team_name.keys():
            if identifier in _team_name:
                team_name = _team_name
                break
    # do fuzzy string match
    if team_name is None:
        team_name = _fuzzy_matcher(
            identifier, dti.team_name_to_full_team_name
        )
    return team_name


def get_team_name(
        identifier: str,
        *,
        session: Session,
        short: bool = False
) -> str:
    """
    Get a full team name based on a recognizable and identifiable part of
    the team name.

    Alternatively, a shortened version of the team name can be returned. The
    short version is intended for saving as much space as possible when
    annotating plots and may skip parts of the official team name.

    Args:
        identifier: a recognizable part of the team name
        session: the session for which the data should be obtained
        short: if True, a shortened version of the team name will be returned
    """
    dti = _get_driver_team_mapping(session)
    team_name = _get_normalized_team_name(identifier, session=session)

    if short:
        return Constants[dti.year].ShortTeamNames[team_name]

    return dti.team_name_to_full_team_name[team_name]


def get_team_name_by_driver(
        identifier: str,
        *,
        session: Session,
        short: bool = False
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
    """
    dti = _get_driver_team_mapping(session)
    abb = get_driver_abbreviation(identifier, session=session)
    team = dti.abbreviation_to_team[abb]
    if short:
        return Constants[dti.year].ShortTeamNames[team]
    else:
        return dti.team_name_to_full_team_name[team]


def _get_team_color(
            identifier: str,
            *,
            session: Session,
            colormap: str = 'default',
            _variant: int = 0  # internal use only
    ):
    if (_variant != 0) and (colormap != 'default'):
        raise ValueError("Color variants are only supported on the "
                         "'default' colormap.")

    dti = _get_driver_team_mapping(session)

    team_name = _get_normalized_team_name(identifier, session=session)

    if dti.year not in Constants.keys():
        raise ValueError(f"No team colors for year '{dti.year}'")

    colormaps = Constants[dti.year].Colormaps
    if colormap not in colormaps.keys():
        raise ValueError(f"Invalid colormap '{colormap}'")

    if team_name not in colormaps[colormap].keys():
        raise ValueError(f"Invalid team name '{team_name}'")

    return colormaps[colormap][team_name][_variant]


def get_team_color(
        identifier: str,
        *,
        session: Session,
        colormap: str = 'default',
):
    """
    Get a team color based on a recognizable and identifiable part of
    the team name.

    The team color is returned as a hexadecimal RGB color code.

    Args:
        identifier: a recognizable part of the team name
        session: the session for which the data should be obtained
        colormap: one of ``'default'`` or ``'official'``
    """
    return _get_team_color(identifier, session=session, colormap=colormap)


def get_driver_name(identifier: str, *, session: Session) -> str:
    """
    Get a full driver name based on the driver's abbreviation or based on
    a recognizable and identifiable part of the driver's name.

    Args:
        identifier: driver abbreviation or recognizable part of the driver name
        session: the session for which the data should be obtained
    """
    dti = _get_driver_team_mapping(session)
    abb = get_driver_abbreviation(identifier, session=session)
    return dti.abbreviation_to_name[abb]


def get_driver_abbreviation(identifier, *, session: Session):
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
    """
    identifier = _normalize_name(identifier).lower()
    dti = _get_driver_team_mapping(session)

    # try driver abbreviation first
    if (abb := identifier.upper()) in dti.abbreviation_to_name:
        return abb

    # check for an exact driver name match
    if identifier in dti.name_normalized_to_abbreviation:
        return dti.name_normalized_to_abbreviation[identifier]

    # check for exact partial string match
    for name, abb in dti.name_normalized_to_abbreviation.items():
        if identifier in name:
            return abb

    # do fuzzy string matching
    return _fuzzy_matcher(
        identifier, dti.name_normalized_to_abbreviation
    )


def get_driver_names_by_team(
        identifier: str, *, session: Session
) -> List[str]:
    """
    Get a list of full names of all drivers that drove for a team in a given
    session based on a recognizable and identifiable part of the team name.

    Args:
        identifier: a recognizable part of the team name
        session: the session for which the data should be obtained
    """
    dti = _get_driver_team_mapping(session)
    team = get_team_name(identifier, session=session)
    names = list()
    for abb in dti.team_to_abbreviations[team]:
        names.append(dti.abbreviation_to_name[abb])
    return names


def get_driver_abbreviations_by_team(
        identifier: str, *, session: Session
) -> List[str]:
    """
    Get a list of abbreviations of all drivers that drove for a team in a given
    session based on a recognizable and identifiable part of the team name.

    Args:
        identifier: a recognizable part of the team name
        session: the session for which the data should be obtained
    """
    dti = _get_driver_team_mapping(session)
    team = get_team_name(identifier, session=session)
    return dti.team_to_abbreviations[team].copy()


def _get_driver_color(
        identifier: str,
        *,
        session: Session,
        colormap: str = 'default',
        _variants: bool = False
):
    dti = _get_driver_team_mapping(session)
    abb = get_driver_abbreviation(identifier, session=session)
    team = dti.abbreviation_to_team[abb]

    if _variants:
        idx = dti.team_to_abbreviations[team].index(abb)
        if idx > 1:
            idx = 1  # we only have two colors, limit to 0 or 1
        return _get_team_color(team, session=session, colormap='default',
                               _variant=idx)
    else:
        return _get_team_color(team, session=session, colormap=colormap)


def get_driver_color(
        identifier: str,
        *,
        session: Session,
        colormap: str = 'default',
):
    """
    Get the color that is associated with a driver based on the driver's
    abbreviation or based on a recognizable and identifiable part of the
    driver's name.

    .. note:: This will simply return the team color of the team that the
        driver participated for in this session. Contrary to older versions
        of FastF1, there are no separate colors for each driver!

    Args:
        identifier: driver abbreviation or recognizable part of the driver name
        session: the session for which the data should be obtained
        colormap: one of ``'default'`` or ``'official'``
    """
    return _get_driver_color(identifier, session=session, colormap=colormap)


def get_driver_style(
        identifier: str,
        style: Union[str, List[str], List[dict]],
        *,
        session: Session,
        colormap: str = 'default',
        additional_color_kws: Union[list, tuple] = ()
):
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

    The styling options include one color for each team, up to four different
    line styles and marker styles within a team. That means that no more than
    four different drivers are supported for a team in a single session. This
    should be sufficent in almost all scenarios.

    The following example obtains the driver style for Alonso and Stroll in a
    race in the 2023 season. The drivers should be represented using the
    ``color`` and ``marker`` arguments, as may be useful in a scatter plot.
    Both drivers were driving for the Aston Martin team, therefore, both
    automatically get assigned the same color, which is the Aston Martin team
    color. But both drivers get assigned a different marker style, so they can
    be uniquely identified in the plot.

    Example::
        >>> from fastf1 import get_session
        >>> from fastf1.plotting import get_driver_style
        >>> session = get_session(2023, 10, 'R')
        >>> get_driver_style('ALO', style=['color', 'marker'], session=session)
        {'color': '#00665e', 'marker': 'x'}
        >>> get_driver_style('STR', style=['color', 'marker'], session=session)
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

    Example::
        >>> from fastf1 import get_session
        >>> from fastf1.plotting import get_driver_style
        >>> session = get_session(2023, 10, 'R')
        >>> my_styles = [ \
                {'linestyle': 'solid', 'color': 'auto', 'custom_arg': True}, \
                {'linestyle': 'dotted', 'color': '#FF0060', 'other_arg': 10} \
            ]
        >>> get_driver_style('ALO', style=my_styles, session=session)
        {'linestyle': 'solid', 'color': '#00665e', 'custom_arg': True}
        >>> get_driver_style('STR', style=my_styles, session=session)
        {'linestyle': 'dotted', 'color': '#FF0060', 'other_arg': 10}

    .. seealso::
        :ref:`sphx_glr_examples_gallery_plot_driver_styling.py`

    Args:
        identifier: driver abbreviation or recognizable part of the driver name
        style: list of matplotlib plot arguments that should be used for
            styling or a list of custom style dictionaries
        session: the session for which the data should be obtained
        colormap: one of ``'default'`` or ``'official'``
        additional_color_kws: A list of keys that should additionally be
            treated as colors. This is most usefull for making the magic
            ``'auto'`` color work with custom styling options.

    Returns: a dictionary of plot style arguments that can be directly passed
        to a matplotlib plot function using the ``**`` expansion operator
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

    dti = _get_driver_team_mapping(session)
    abb = get_driver_abbreviation(identifier, session=session)
    team = dti.abbreviation_to_team[abb]
    idx = dti.team_to_abbreviations[team].index(abb)

    if isinstance(style, (list, tuple)) and (len(style) == 0):
        raise ValueError

    if isinstance(style, str):
        style = [style]

    plot_style = dict()

    if isinstance(style[0], str):
        # generate the plot style based on the provided keyword
        # arguments
        for opt in style:
            if opt in color_kwargs:
                value = get_team_color(team, colormap=colormap,
                                       session=session)
            elif opt in stylers:
                value = stylers[opt][idx]
            else:
                raise ValueError(f"'{opt}' is not a supported styling "
                                 f"option")
            plot_style[opt] = value

    elif isinstance(style[0], dict):
        # copy the correct user provided style and replace any 'auto'
        # colors with the correct color value
        plot_style = style[idx].copy()
        for kwarg in color_kwargs:
            if plot_style.get(kwarg, None) == 'auto':
                color = get_team_color(team, colormap=colormap,
                                       session=session)
                plot_style[kwarg] = color

    return plot_style


def add_sorted_driver_legend(ax: matplotlib.axes.Axes, *, session: Session):
    """
    Adds a legend to the axis where drivers are ordered by team and within a
    team in the same order that is used for selecting plot styles.

    This function is a drop in replacement for calling Matplotlib's
    ``ax.legend()`` method. It can only be used when driver names or driver
    abbreviations are used as labels for the legend.

    There is no particular need to use this function except to make the
    legend more visually pleasing.

    .. seealso::
        :ref:`sphx_glr_examples_gallery_plot_driver_styling.py`

    Args:
        ax: An instance of a Matplotlib ``Axes`` object
        session: the session for which the data should be obtained
    """
    dti = _get_driver_team_mapping(session)
    handles, labels = ax.get_legend_handles_labels()

    teams_list = list(dti.team_to_abbreviations.keys())

    # create an intermediary list where each element is a tuple that
    # contains (team_idx, driver_idx, handle, label). Then sort this list
    # based on the team_idx and driver_idx. As a result, drivers from the
    # same team will be next to each other and in the same order as their
    # styles are cycled.
    ref = list()
    for hdl, lbl in zip(handles, labels):
        abb = get_driver_abbreviation(identifier=lbl, session=session)
        team = dti.abbreviation_to_team[abb]
        team_idx = teams_list.index(team)
        driver_idx = dti.team_to_abbreviations[team].index(abb)
        ref.append((team_idx, driver_idx, hdl, lbl))

    # sort based only on team_idx and driver_idx (i.e. first two entries)
    ref.sort(key=lambda e: e[:2])

    handles_new = list()
    labels_new = list()
    for elem in ref:
        handles_new.append(elem[2])
        labels_new.append(elem[3])

    ax.legend(handles_new, labels_new)
