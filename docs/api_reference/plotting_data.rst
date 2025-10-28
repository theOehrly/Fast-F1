.. _plotting-data:


Plotting Data
=============

The ``fastf1.plotting`` submodule contains helper functions for creating data plots.

This submodule mainly offers:
    - team names and colors
    - driver names and driver abbreviations
    - Matplotlib integration and helper functions

FastF1 focuses on plotting with Matplotlib or related libraries like Seaborn.
If you wish to use these libraries, it is highly recommended to enable
extend support for these by calling :func:`~fastf1.plotting.setup_mpl`.


Team Colormaps
--------------

Currently, two team colormaps are supported. Each colormap provides one color
for each team. All functions that return colors for teams or drivers accept an
optional ``colormap`` argument. If this argument is not provided, the default
colormap is used. The default colormap can be changed by using
:func:`~fastf1.plotting.set_default_colormap`.

The ``'fastf1'`` colormap is FastF1's default colormap. These colors are teams'
primary colors or accent colors as they are used by the teams on their website
or in promotional material. The colors are chosen to maximize readability in
plots by creating a stronger contrast while still being associated with the
team. Colors are constant over the course of a season.

The ``'official'`` colormap contains the colors exactly as they are used by
F1 in official graphics and in the TV broadcast. Those colors are often
slightly muted. While that makes them more pleasing to look at in some graphics,
it also reduces the contrast between colors which is often bad for
readability of plots. These colors may change during the season if they are
updated by F1.

See here for a complete list of all colors: :ref:`Team-Colormaps-Overview`


.. note:: **Driver Colors**

    Previously, individual colors for each driver were provided. This is no
    longer the case. The driver color is now equivalent to the team color,
    meaning that drivers from the same team have the exact same color. This
    change was made because different colors for 20 drivers end up looking
    very similar in a lot of cases. Therefore, it is not a good solution to
    use driver specific colors to distinguish between different drivers. Other
    means of plot styling should be used instead.



API Summary
-----------

.. currentmodule:: fastf1.plotting


Configuration and Setup
^^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: api_autogen/
    :template: function.rst

    setup_mpl


Get Colors, Names and Abbreviations for Drivers or Teams
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: api_autogen/
    :template: function.rst

    get_compound_color
    get_driver_abbreviation
    get_driver_abbreviations_by_team
    get_driver_color
    get_driver_name
    get_driver_names_by_team
    get_driver_style
    get_team_color
    get_team_name
    get_team_name_by_driver


List all Names and Abbreviations for Drivers/Teams in a Session
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: api_autogen/
    :template: function.rst

    get_compound_mapping
    get_driver_color_mapping
    list_compounds
    list_driver_abbreviations
    list_driver_names
    list_team_names


Plot Styling
^^^^^^^^^^^^

.. autosummary::
    :toctree: api_autogen/
    :template: function.rst

    add_sorted_driver_legend
    set_default_colormap


Advanced Functionality
^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: api_autogen/
    :template: function.rst

    override_team_constants
