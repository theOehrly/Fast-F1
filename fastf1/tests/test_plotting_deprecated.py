import warnings

import pytest

import fastf1.plotting


with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    from fastf1.plotting import (
        DRIVER_COLORS,
        DRIVER_TRANSLATE,
        TEAM_COLORS,
        TEAM_TRANSLATE,
        COLOR_PALETTE,
        COMPOUND_COLORS
    )

import matplotlib.pyplot as plt


@pytest.mark.parametrize(
    "property_name",
    ('DRIVER_COLORS', 'DRIVER_TRANSLATE',
     'TEAM_COLORS', 'TEAM_TRANSLATE',
     'COLOR_PALETTE', 'COMPOUND_COLORS')
)
def test_all_warn_deprecated(property_name):
    with pytest.warns(FutureWarning, match="is deprecated"):
        obj = getattr(fastf1.plotting, property_name)
    assert isinstance(obj, (dict, list))


def test_driver_colors_driver_translate():
    for abb, name in DRIVER_TRANSLATE.items():
        assert len(abb) == 3
        assert abb.isalpha() and abb.isupper()
        assert len(name) > 3
        assert name.replace(' ', '').isalpha() and name.islower()

        assert name in DRIVER_COLORS
        color = DRIVER_COLORS[name]
        assert color.startswith('#')
        assert len(color) == 7
        _ = int(color[1:], base=16)  # ensure that it's a valid hex color


def test_team_colors_team_translate():
    for abb, name in TEAM_TRANSLATE.items():
        assert (len(abb) == 3) or (len(abb) == 2)
        assert abb.isalpha() and abb.isupper()
        assert (len(name) > 3) or (name.lower() == 'rb')
        assert name.replace(' ', '').isalpha() and name.islower()

        assert name in TEAM_COLORS
        color = TEAM_COLORS[name]
        assert color.startswith('#')
        assert len(color) == 7
        _ = int(color[1:], base=16)  # ensure that it's a valid hex color


def test_compound_colors():
    for compound, color in COMPOUND_COLORS.items():
        assert len(compound) >= 3
        assert compound.replace('-', '').isalpha()
        assert compound.replace('-', '').isupper()

        assert color.startswith('#')
        assert len(color) == 7
        _ = int(color[1:], base=16)  # ensure that it's a valid hex color


def test_color_palette():
    assert len(COLOR_PALETTE) == 7
    for color in COLOR_PALETTE:
        assert color.startswith('#')
        assert len(color) == 7
        _ = int(color[1:], base=16)  # ensure that it's a valid hex color


@pytest.mark.parametrize(
    "func_name",
    ("setup_mpl", "driver_color", "team_color", "lapnumber_axis")
)
def test_functions_exist(func_name):
    assert hasattr(fastf1.plotting, func_name)
    func = getattr(fastf1.plotting, func_name)
    assert callable(func)


def test_driver_color():
    with pytest.warns(FutureWarning, match="is deprecated"):
        color_ver = fastf1.plotting.driver_color('VER')
        color_per = fastf1.plotting.driver_color('PER')

    assert color_ver.startswith('#')
    assert len(color_ver) == 7
    _ = int(color_ver[1:], base=16)  # ensure that it's a valid hex color

    assert color_per != color_ver


def test_team_color():
    with pytest.warns(FutureWarning, match="is deprecated"):
        color_ferrari = fastf1.plotting.team_color('ferrari')

    assert color_ferrari.startswith('#')
    assert len(color_ferrari) == 7
    _ = int(color_ferrari[1:], base=16)  # ensure that it's a valid hex color

    with pytest.warns(FutureWarning, match="is deprecated"):
        color_visa = fastf1.plotting.team_color("visa")
        color_rb = fastf1.plotting.team_color("rb")
        color_visa_rb = fastf1.plotting.team_color("visa rb")
        color_rbr = fastf1.plotting.team_color("RBR")
    
    assert color_visa == color_rb == color_visa_rb
    assert color_visa_rb != color_rbr


def test_lapnumber_axis():
    ax = plt.figure().subplots()
    with pytest.warns(FutureWarning, match="is deprecated"):
        fastf1.plotting.lapnumber_axis(ax)
