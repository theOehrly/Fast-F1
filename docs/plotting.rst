Plotting - :mod:`fastf1.plotting`
=================================

Helper functions for creating data plots.

:mod:`fastf1.plotting` provides optional functionality with the intention of
making it easy to create nice plots.

This module mainly offers:
    - team names and colors
    - driver names and driver abbreviations
    - Matplotlib integration and helper functions

FastF1 focuses on plotting with Matplotlib or related libraries like Seaborn.
If you wish to use these libraries, it is highly recommended to enable
extend support for these by calling :func:`~fastf1.plotting.setup_mpl`.


Team Colormaps
--------------

Currently, two team colormaps are supported. Each colormap provides one color
for each team. Colors are constant over the course of a season. All functions
that return colors for teams or drivers accept an optional ``colormap``
argument.

The ``'default'`` colormap is FastF1's default colormap. These colors are teams'
primary colors or accent colors as they are used by the teams on their website
or in promotional material. The colors are chosen to maximize readability in
plots by creating a stronger contrast while still being associated with the
team.

The ``'official'`` colormap contains the colors exactly as they are used by
the FOM in official graphics and in the TV graphics. Those colors are often
slightly muted. While that makes them more pleasing to look at in some graphics,
it also reduces the contrast between colors which is often bad for
readability of plots.

See here for a complete list of all colors: :ref:`Team-Colormaps-Overview`


.. note:: **Driver Colors**

    Previously, individual colors for each driver were provided. This is no
    longer the case. The driver color is now equivalent to the team color,
    meaning that drivers from the same team have the exact same color. This
    change was made because different colors for 20 drivers end up looking
    very similar in many cases anyway, meaning it is not a good solution to
    use these to distinguish different drivers. Other means of plot styling
    should be used instead.



Overview
--------


Configuration and Setup
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: fastf1.plotting
  :noindex:
  :no-members:
  :autosummary:
  :autosummary-members:
    setup_mpl


Get Colors, Names and Abbreviations for Drivers or Teams
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: fastf1.plotting
  :noindex:
  :no-members:
  :autosummary:
  :autosummary-members:
    get_compound_color,
    get_driver_abbreviation,
    get_driver_abbreviations_by_team,
    get_driver_color,
    get_driver_name,
    get_driver_names_by_team,
    get_driver_style,
    get_team_color,
    get_team_name,
    get_team_name_by_driver


List all Names and Abbreviations for Drivers/Teams in a Session
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: fastf1.plotting
  :noindex:
  :no-members:
  :autosummary:
  :autosummary-members:
    get_compound_mapping,
    get_driver_color_mapping,
    list_driver_abbreviations,
    list_driver_names,
    list_short_team_names,
    list_team_names


Plot Styling
^^^^^^^^^^^^

.. automodule:: fastf1.plotting
  :noindex:
  :no-members:
  :autosummary:
  :autosummary-members:
    add_sorted_driver_legend


Deprecated Functionality
^^^^^^^^^^^^^^^^^^^^^^^^

The following module-level attributes are deprecated since version 3.4.0 and
will be removed in a future release.


.. automodule:: fastf1.plotting
  :noindex:
  :no-members:
  :autosummary:
  :autosummary-members:
    driver_color,
    lapnumber_axis,
    team_color,
    COMPOUND_COLORS,
    DRIVER_TRANSLATE,
    DRIVER_COLORS,
    TEAM_COLORS,
    TEAM_TRANSLATE,
    COLOR_PALETTE



Plotting API Reference
----------------------

.. automodule:: fastf1.plotting
  :members:
