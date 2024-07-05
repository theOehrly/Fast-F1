import matplotlib.pyplot as plt
import pytest

import fastf1
import fastf1.plotting
from fastf1.plotting._constants import season2023
from fastf1.plotting._constants.base import CompoundsConst


OFFICIAL_MERC_COLOR = season2023.Teams['mercedes'].TeamColor.Official
OFFICIAL_RB_COLOR = season2023.Teams['red bull'].TeamColor.Official
DEFAULT_MERC_COLOR = season2023.Teams['mercedes'].TeamColor.FastF1
DEFAULT_RB_COLOR = season2023.Teams['red bull'].TeamColor.FastF1


@pytest.mark.parametrize(
    "use_exact", (True, False)
)
@pytest.mark.parametrize(
    "identifier, expected, can_match_exact",
    (
            ('VER', 'max verstappen', True),  # test abbreviation
            ('HAM', 'lewis hamilton', True),
            ('max verstappen', 'max verstappen', True),  # exact name match
            ('lewis hamilton', 'lewis hamilton', True),
            ('verstappen', 'max verstappen', False),  # partial name match
            ('hamilton', 'lewis hamilton', False),
            ('verstaapen', 'max verstappen', False),  # test fuzzy (typos)
            ('hamiltime', 'lewis hamilton', False),
    )
)
def test_internal_get_driver(identifier, expected, can_match_exact, use_exact):
    session = fastf1.get_session(2023, 10, 'R')

    if use_exact and not can_match_exact:
        with pytest.raises(KeyError, match="No driver found"):
            _ = fastf1.plotting._interface._get_driver(
                identifier, session, exact_match=use_exact
            )
            return

    else:
        driver = fastf1.plotting._interface._get_driver(
            identifier, session, exact_match=use_exact
        )
        assert driver.normalized_value == expected


@pytest.mark.parametrize(
    "use_exact", (True, False)
)
@pytest.mark.parametrize(
    "identifier, expected, can_match_exact",
    (
            ('red bull', 'red bull', True),  # exact name match
            ('mercedes', 'mercedes', True),
            ('bull', 'red bull', False),  # partial name match
            ('haas', 'haas', True),
            ('Red Bull Racing', 'red bull', True),  # exact match with full name
            ('Haas F1 Team', 'haas', True),
            ('merciless', 'mercedes', False),  # test fuzzy (typos)
            ('alfadauri', 'alphatauri', False),
    )
)
def test_internal_get_team(identifier, expected, can_match_exact, use_exact):
    session = fastf1.get_session(2023, 10, 'R')

    if use_exact and not can_match_exact:
        with pytest.raises(KeyError, match="No team found"):
            _ = fastf1.plotting._interface._get_team(
                identifier, session, exact_match=use_exact
            )
        return

    else:
        team = fastf1.plotting._interface._get_team(
            identifier, session, exact_match=use_exact
        )
        assert team.normalized_value == expected


def test_fuzzy_driver_team_key_error():
    session = fastf1.get_session(2023, 10, 'R')

    with pytest.raises(KeyError):
        _ = fastf1.plotting._interface._get_team('andretti', session)

    with pytest.raises(KeyError):
        _ = fastf1.plotting._interface._get_driver('toto wolf', session)


@pytest.mark.parametrize(
    "identifier, kwargs, expected",
    (
            ('red bull', {'colormap': 'default'}, DEFAULT_RB_COLOR),
            ('mercedes', {'colormap': 'default'}, DEFAULT_MERC_COLOR),
            ('mercedes', {'colormap': 'official'}, OFFICIAL_MERC_COLOR),
    )
)
def test_internal_get_team_color(identifier, kwargs, expected):
    session = fastf1.get_session(2023, 10, 'R')
    color = fastf1.plotting._interface._get_team_color(
        identifier, session, **kwargs
    )
    assert color == expected


def test_internal_get_team_color_exceptions():
    session = fastf1.get_session(2023, 10, 'R')
    with pytest.raises(ValueError, match="Invalid colormap"):
        fastf1.plotting._interface._get_team_color(
            'mercedes', session, colormap='bullshit'
        )


@pytest.mark.parametrize(
    "identifier, kwargs, expected",
    (
            ('Red Bull', {'short': False}, 'Red Bull Racing'),
            ('Red Bull', {'short': True}, 'Red Bull'),
            ('merciless', {'short': True}, 'Mercedes'),  # test fuzzy (typos)
    )
)
def test_get_team_name(identifier, kwargs, expected):
    session = fastf1.get_session(2023, 10, 'R')
    name = fastf1.plotting.get_team_name(identifier, session, **kwargs)
    assert name == expected


@pytest.mark.parametrize(
    "identifier, kwargs, expected",
    (
            ('max verstappen', {'short': False}, 'Red Bull Racing'),  # long
            ('max verstappen', {'short': True}, 'Red Bull'),  # test short
            ('HAM', {'short': True}, 'Mercedes'),  # test abbreviation
            ('verstaapen', {'short': True}, 'Red Bull'),  # test fuzzy (typos)
    )
)
def test_get_team_name_by_driver(identifier, kwargs, expected):
    session = fastf1.get_session(2023, 10, 'R')
    name = fastf1.plotting.get_team_name_by_driver(
        identifier, session, **kwargs
    )
    assert name == expected


@pytest.mark.parametrize(
    "identifier, kwargs, expected",
    (
            ('red bull', {'colormap': 'default'},
             DEFAULT_RB_COLOR),
            ('mercedes', {'colormap': 'default'},
             DEFAULT_MERC_COLOR),
            ('mercedes', {'colormap': 'official'},
             OFFICIAL_MERC_COLOR),
    )
)
def test_get_team_color(identifier, kwargs, expected):
    session = fastf1.get_session(2023, 10, 'R')
    color = fastf1.plotting.get_team_color(
        identifier, session, **kwargs
    )
    assert color == expected


@pytest.mark.parametrize(
    "identifier, expected",
    (
            ('VER', 'Max Verstappen'),  # test abbreviation
            ('HAM', 'Lewis Hamilton'),
            ('max verstappen', 'Max Verstappen'),  # exact name match
            ('lewis hamilton', 'Lewis Hamilton'),
            ('verstappen', 'Max Verstappen'),  # exact partial name match
            ('hamilton', 'Lewis Hamilton'),
            ('verstaapen', 'Max Verstappen'),  # test fuzzy (typos)
            ('hamiltime', 'Lewis Hamilton'),
    )
)
def test_get_driver_name(identifier, expected):
    session = fastf1.get_session(2023, 10, 'R')
    name = fastf1.plotting.get_driver_name(identifier, session)
    assert name == expected


@pytest.mark.parametrize(
    "identifier, expected",
    (
            ('VER', 'VER'),  # test abbreviation
            ('HAM', 'HAM'),
            ('max verstappen', 'VER'),  # exact name match
            ('lewis hamilton', 'HAM'),
            ('verstappen', 'VER'),  # exact partial name match
            ('hamilton', 'HAM'),
            ('verstaapen', 'VER'),  # test fuzzy (typos)
            ('hamiltime', 'HAM'),
    )
)
def test_get_driver_abbreviation(identifier, expected):
    session = fastf1.get_session(2023, 10, 'R')
    abb = fastf1.plotting.get_driver_abbreviation(identifier, session)
    assert abb == expected


@pytest.mark.parametrize(
    "identifier, expected",
    (
            ('red bull', ['Max Verstappen', 'Sergio Perez']),  # exact name match
            ('mercedes', ['Lewis Hamilton', 'George Russell']),
    )
)
def test_get_driver_names_by_team(identifier, expected):
    session = fastf1.get_session(2023, 10, 'R')
    names = fastf1.plotting.get_driver_names_by_team(identifier, session)
    for name in expected:
        assert name in names
    assert len(names) == len(expected)


@pytest.mark.parametrize(
    "identifier, expected",
    (
            ('red bull', ['VER', 'PER']),  # exact name match
            ('mercedes', ['HAM', 'RUS']),
    )
)
def test_get_driver_abbreviations_by_team(identifier, expected):
    session = fastf1.get_session(2023, 10, 'R')
    abbs = fastf1.plotting.get_driver_abbreviations_by_team(identifier, session)
    for abb in expected:
        assert abb in abbs
    assert len(abbs) == len(expected)


@pytest.mark.parametrize(
    "identifier, kwargs, expected",
    (
            ('verstappen', {'colormap': 'default'},
             DEFAULT_RB_COLOR),
            ('perez', {'colormap': 'default'},
             DEFAULT_RB_COLOR),
            ('hamilton', {'colormap': 'default'},
             DEFAULT_MERC_COLOR),
            ('hamilton', {'colormap': 'official'},
             OFFICIAL_MERC_COLOR),
    )
)
def test_get_driver_color(identifier, kwargs, expected):
    session = fastf1.get_session(2023, 10, 'R')
    color = fastf1.plotting.get_driver_color(
        identifier, session, **kwargs
    )
    assert color == expected


@pytest.mark.parametrize(
    "identifier, style, colormap, expected",
    (
            ('verstappen', 'linestyle', 'default',
             {'linestyle': 'solid'}
             ),
            ('perez', ['marker'], 'default',
             {'marker': 'o'}
             ),
            ('verstappen', ['marker', 'color'], 'default',
             {'marker': 'x', 'color': DEFAULT_RB_COLOR}
             ),
            ('hamilton', ['edgecolor', 'facecolor'], 'official',
             {'edgecolor': OFFICIAL_MERC_COLOR,
              'facecolor': OFFICIAL_MERC_COLOR}),

    )
)
def test_get_driver_style_default_styles(
        identifier, style, colormap, expected
):
    session = fastf1.get_session(2023, 10, 'R')
    color = fastf1.plotting.get_driver_style(
        identifier, style, session, colormap=colormap
    )
    assert color == expected


def test_get_driver_style_custom_style():
    session = fastf1.get_session(2023, 10, 'R')

    custom_style = (
        {'color': '#00ff00', 'rain': 'yes', 'snow': False, 'skycolor': 'auto'},
        {'rain': 'no', 'snow': True, 'sun': 100, 'edgecolor': 'auto'},
    )

    ver_style = fastf1.plotting.get_driver_style(
        'verstappen',
        custom_style,
        session,
        colormap='default',
        additional_color_kws=('skycolor', )  # register custom color key
    )

    assert ver_style == {
        'color': '#00ff00',  # static color on color keyword
        'rain': 'yes',  # string option
        'snow': False,  # bool option
        # 'sun': 100  # no sun option
        'skycolor': DEFAULT_RB_COLOR,  # auto color on custom registered key
    }

    per_style = fastf1.plotting.get_driver_style(
        'perez',
        custom_style,
        session,
        colormap='default',
        additional_color_kws=('skycolor', )
    )

    assert per_style == {
        # 'color': '#00ff00',  # no color entry
        'rain': 'no',  # string option
        'snow': True,  # bool option
        'sun': 100,  # int option
        # 'skycolor': DEFAULT_RB_COLOR_0,  no skycolor entry
        'edgecolor': DEFAULT_RB_COLOR,  # auto color on default key
    }


def test_get_compound_color():
    session = fastf1.get_session(2023, 10, 'R')
    assert (fastf1.plotting.get_compound_color('HARD', session)
            == season2023.CompoundColors[CompoundsConst.Hard])

    assert (fastf1.plotting.get_compound_color('sOfT', session)
            == season2023.CompoundColors[CompoundsConst.Soft])

    with pytest.raises(KeyError):
        fastf1.plotting.get_compound_color('HYPERSOFT', session)


def test_get_compound_mapping():
    session = fastf1.get_session(2023, 10, 'R')
    assert (fastf1.plotting.get_compound_mapping(session)
            == season2023.CompoundColors)


def test_get_driver_color_mapping():
    session = fastf1.get_session(2023, 10, 'R')

    default = fastf1.plotting.get_driver_color_mapping(session,
                                                       colormap='default')
    assert default['VER'] == default['PER'] == DEFAULT_RB_COLOR
    assert default['HAM'] == default['RUS'] == DEFAULT_MERC_COLOR
    assert len(default) == 20

    official = fastf1.plotting.get_driver_color_mapping(session,
                                                        colormap='official')
    assert official['VER'] == official['PER'] == OFFICIAL_RB_COLOR
    assert official['HAM'] == official['RUS'] == OFFICIAL_MERC_COLOR
    assert len(default) == 20


def test_list_team_names():
    session = fastf1.get_session(2023, 10, 'R')
    names = fastf1.plotting.list_team_names(session)

    assert 'Red Bull Racing' in names
    assert 'Haas F1 Team' in names
    assert 'Aston Martin' in names
    assert len(names) == 10


def test_list_short_team_names():
    session = fastf1.get_session(2023, 10, 'R')
    names = fastf1.plotting.list_short_team_names(session)

    assert 'Red Bull' in names
    assert 'Haas' in names
    assert 'Aston Martin' in names
    assert len(names) == 10


def test_list_driver_abbreviations():
    session = fastf1.get_session(2023, 10, 'R')
    abbs = fastf1.plotting.list_driver_abbreviations(session)

    assert 'VER' in abbs
    assert 'RUS' in abbs
    assert len(abbs) == 20


def test_list_driver_names():
    session = fastf1.get_session(2023, 10, 'R')
    names = fastf1.plotting.list_driver_names(session)

    assert 'Max Verstappen' in names
    assert 'George Russell' in names
    assert len(names) == 20


def test_list_compounds():
    session = fastf1.get_session(2023, 10, 'R')
    compounds = fastf1.plotting.list_compounds(session)

    reference = ('HARD', 'MEDIUM', 'SOFT', 'INTERMEDIATE', 'WET',
           'TEST-UNKNOWN', 'UNKNOWN')

    for compound in reference:
        assert compound in compounds

    assert len(compounds) == len(reference)


def test_add_sorted_lapnumber_axis():
    session = fastf1.get_session(2023, 10, 'R')
    ax = plt.figure().subplots()

    ax.plot(0, 0, label='HAM')
    ax.plot(0, 0, label='RUS')
    ax.plot(0, 0, label='PER')
    ax.plot(0, 0, label='VER')

    legend = fastf1.plotting.add_sorted_driver_legend(ax, session)

    # sorting is generally done by driver number to guarantee consistency
    # in 2023, VER was #1, so he is first, then followed by PER;
    # Red Bull as a team before Mercedes, again because VER has the lower number
    # within Mercedes, Hamilton has the lower number
    assert ([txt.get_text() for txt in legend.texts]
            == ['VER', 'PER', 'HAM', 'RUS'])


def test_override_team_constants():
    session = fastf1.get_session(2023, 10, 'R')
    fastf1.plotting.override_team_constants(
        'Haas', session,
        short_name='Gene',
        fastf1_color='#badbad',
        official_color='#bada55'
    )

    assert fastf1.plotting.get_team_name('Haas', session) == 'Haas F1 Team'
    assert fastf1.plotting.get_team_name('Haas', session, short=True) == 'Gene'

    assert fastf1.plotting.get_team_color(
        'Haas', session, colormap='fastf1'
    ) == '#badbad'

    assert fastf1.plotting.get_team_color(
        'Haas', session, colormap='official'
    ) == '#bada55'

    # cleanup: explicitly clear the driver-team-mapping to avoid side effects
    # in other tests
    fastf1.plotting._interface._DRIVER_TEAM_MAPPINGS = dict()

    if fastf1.plotting.get_team_name('Haas', session, short=True) != 'Haas':
        raise RuntimeError("Test cleanup failed!")
