.. _contributing:

============
Contributing
============


The community around FastF1 is slowly building and everyone is welcome to
contribute to the project.


Submitting a bug report
=======================

If you find a bug in the code or documentation, do not hesitate to open a
new issue in the `issue section <https://github.com/theOehrly/Fast-F1/issues>`_
on Github. You are also welcome to post feature requests or pull requests.

If you have more general questions or problems that likely are not caused by
a bug in FastF1, you can open a new
`discussion <https://github.com/theOehrly/Fast-F1/discussions>`_ instead.


If you are reporting a bug, please do your best to include the following:

- A short, top-level summary of the bug. In most cases, this should be 1-2
  sentences.

- A short, self-contained code snippet to reproduce the bug, ideally allowing
  a simple copy and paste to reproduce. Please do your best to reduce the code
  snippet to the minimum required.

- The actual outcome of the code snippet.

- The expected outcome of the code snippet.

- The FastF1 version and Python version that you are using.
  You can grab the version with the following commands::

      >>> import fastf1
      >>> fastf1.__version__  # doctest: +SKIP
      '2.2.1'
      >>> import platform
      >>> platform.python_version()  # doctest: +SKIP
      '3.9.2'


We have preloaded the issue creation page with a Markdown template that you
can use to organize this information.

Thank you for your help in keeping bug reports complete, targeted and
descriptive.


Requesting a new feature
========================

Please post feature requests in the
`issue section <https://github.com/theOehrly/Fast-F1/issues>`_ on Github.

Since FastF1 is an open source project with limited resources, you are
encouraged to also participate in the implementation as much as you can.


.. _contributing-code:

Contributing code
=================

.. _how-to-contribute:

How to contribute
-----------------

The preferred way to contribute to FastF1 is to fork the `main
repository <https://github.com/theOehrly/Fast-F1/>`__ on GitHub,
then submit a "pull request" (PR).

A brief overview is:

1. `Create an account <https://github.com/join>`_ on GitHub if you do not
   already have one.

2. Fork the `project repository <https://github.com/theOehrly/Fast-F1>`_:
   click on the 'Fork' button near the top of the page. This creates a copy of
   the code under your account on the GitHub server.

3. Clone this copy to your local disk::

      git clone https://github.com/<YOUR GITHUB USERNAME>/Fast-F1.git

4. Enter the directory and install the local version of FastF1.
   See :ref:`installing_for_devs` for instructions

5. Create a branch to hold your changes::

      git checkout -b my-feature origin/master

   and start making changes. Never work in the ``master`` branch!

6. Work on this copy, on your computer, using Git to do the version control.
   When you're done editing e.g., ``fastf1/core.py``, do::

      git add fastf1/core.py
      git commit

   to record your changes in Git, then push them to GitHub with::

      git push -u origin my-feature

Finally, go to the web page of your fork of the FastF1 repo, and click
'Pull request' to send your changes to the maintainer for review.

.. seealso::

  * `Git documentation <https://git-scm.com/doc>`_
  * `Git-Contributing to a Project <https://git-scm.com/book/en/v2/GitHub-Contributing-to-a-Project>`_
  * `Introduction to GitHub  <https://lab.github.com/githubtraining/introduction-to-github>`_


Contributing pull requests
--------------------------

It is recommended to check that your contribution complies with the following
rules before submitting a pull request:

* If your pull request addresses an issue, please use the title to describe the
  issue and mention the issue number in the pull request description to ensure
  that a link is created to the original issue.

* All public methods should have informative docstrings with sample usage when
  appropriate. Use the `google docstring standard
  <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_.

* Formatting should follow the recommendations of PEP8_, as enforced by
  ruff_. The maximum line length for all changed lines is 79 characters.
  You can check code style compliance from the command line with ::

    python -m pip install ruff
    ruff check .

  or your editor may provide integration with it. The above command will not
  flag lines that are too long!

  Ruff will also be run before each commit if you have the pre-commit hooks
  installed (see :ref:`install_pre_commit`).

  .. _PEP8: https://www.python.org/dev/peps/pep-0008/
  .. _ruff: https://docs.astral.sh/ruff/

* Changes (both new features and bugfixes) should have good test coverage. See
  :ref:`testing` for more details.

* Import the following modules using the standard scipy conventions::

     import numpy as np
     import pandas as pd
     import matplotlib as mpl
     import matplotlib.pyplot as plt

* If your change is a major new feature, add an entry to the ``Changelog``
  section by editing ``docs/changelog.rst``

.. note::

    The current state of the FastF1 code base is not compliant with all
    of those guidelines, but we expect that enforcing those constraints on all
    new contributions will move the overall code base quality in the right
    direction.

.. seealso::

  * :ref:`coding_guidelines`
  * :ref:`testing`
  * :ref:`documenting-fastf1`


.. _contributing_documentation:

Contributing documentation
==========================

You as an end-user of FastF1 can make a valuable contribution because you
more clearly see the potential for improvement than a core developer.
For example, you can:

- Fix a typo
- Clarify a docstring
- Write or update an :ref:`example plot <contributing_gallery_examples>`

The documentation source files live in the same GitHub repository as the code.
Contributions are proposed and accepted through the pull request process.
For details see :ref:`how-to-contribute`.

If you have trouble getting started, you may instead open an `issue`_
describing the intended improvement.

.. _issue: https://github.com/theOehrly/Fast-F1/issues

.. seealso::
  * :ref:`documenting-fastf1`


.. _contributing_gallery_examples:

Contributing examples to the gallery
------------------------------------

FastF1 uses `Sphinx-Gallery <https://sphinx-gallery.github.io/stable/index.html>`_
to generate a gallery of examples. The examples gallery is generated from the
files located in the :file:`examples` folder. To add a new gallery example,
create a new python file in this directory. The file should contain all the
code required to plot the examples. Check out the documentation of
Sphinx-Gallery to find out how to format your example code to include headings,
sections and explanatory text for your example.


.. _coding_guidelines:

Coding guidelines
=================

Supported versions of Python and dependencies
---------------------------------------------

This project supports:

- All minor versions of Python released 42 months prior to the project, and at
  minimum the two latest minor versions.

- All minor versions of Numpy, Pandas and Matplotlib released in the 24 months
  prior to the project, and at minimum the last three minor versions.

- For other dependencies: As a guideline, this project will try to support all
  minor versions initially released in the 12 months prior to our planned
  release date or the oldest that supports our minimum Python. We will only
  bump these dependencies as we need new features or the old versions are no
  longer compatible with other minimum version requirements of this project.

These guidelines are based on `NEP 29`__ .

__ https://numpy.org/neps/nep-0029-deprecation_policy.html


API changes
-----------

API consistency and stability are of great value. Therefore, API changes
(e.g. signature changes, behavior changes, removals) will only be conducted
if the added benefit is worth the user effort for adapting.

API changes in FastF1 have to be performed following the deprecation process
below, except in very rare circumstances as deemed necessary by the developers.
This ensures that users are notified before the change will take effect and thus
prevents unexpected breaking of code.

Note that FastF1 often needs to be adapted to changes in external APIs which
may come without prior warning. To be able to efficiently keep up with these
external changes, it can be necessary to make changes to FastF1 on shorter
notice than described below. In general, breaking changes and deprecations
should be avoided if possible and users should be given prior warnings and as
much time as possible to adapt.


Rules
~~~~~

- Deprecations are targeted at the next point release (e.g. 3.x)
- Deprecated API is generally removed two point-releases
  after introduction of the deprecation. Longer deprecations can be imposed by
  core developers on a case-by-case basis to give more time for the transition
- The old API must remain fully functional during the deprecation period
- If alternatives to the deprecated API exist, they should be available
  during the deprecation period


Introducing
~~~~~~~~~~~

1. Announce the deprecation in the changelog
   :file:`docs/changelog.rst` (reference your pull request as well)
2. If possible, issue a `DeprecationWarning` when the deprecated
   API is used, using the python `warnings` module.


Expiring
~~~~~~~~

1. Announce the deprecation in the changelog
   :file:`docs/changelog.rst` (reference your pull request as well)
   For the content, you can usually copy the deprecation notice
   and adapt it slightly.
2. Change the code functionality and remove any related deprecation warnings.

Adding new API
--------------

Every new function, parameter and attribute that is not explicitly marked as
private (i.e., starts with an underscore) becomes part of FastF1's public
API. As discussed above, changing the existing API is cumbersome. Therefore,
take particular care when adding new API:

- Mark helper functions and internal attributes as private by prefixing them
  with an underscore.
- Carefully think about good names for your functions and variables.
- Try to adopt patterns and naming conventions from existing parts of the
  FastF1 API.
- Consider making as many arguments keyword-only as possible. See also
  `API Evolution the Right Way -- Add Parameters Compatibly`__.

  __ https://emptysqua.re/blog/api-evolution-the-right-way/#adding-parameters


New modules and files: installation
-----------------------------------

* If you have added new files or directories, or reorganized existing
  ones, make sure the new files are included in the match patterns in
  in *packages* in :file:`setup.cfg`.


.. _using_logging:

Using logging for debug messages
--------------------------------

FastF1 uses a logging system that is based on the standard Python `logging`
library to write verbose warnings, information, and debug messages.
Please use it! In all those places you write `print` calls to do your
debugging, try using `logger.debug` instead!

FastF1 creates one main logger and then uses child loggers for each module.

To include logging in your module, at the top of the module, you need to add
``from fastf1.logger import get_logger``.  Then calls in your code like::

  # set up the logger once (!)
  logger = get_logger(__name__)

  # code
  logger.info('Here is some information')
  logger.debug('Here is some more detailed information')
  # more code

will log to a logger named ``fastf1.yourmodulename``.


Which logging level to use?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are five levels at which you can emit messages.

- `logger.critical` and `logger.error` are really only there for errors that
  will end the use of the library but not kill the interpreter.
- `logger.warning` is used to warn the user, for example, if an operation has
  failed gracefully, if some action is likely to have unintended side-effects
  or similar.
- `logger.info` is for information that the user may want to know if the
  program behaves oddly. For instance, if a driver did not participate in a
  session, some data cannot be loaded for this specific driver. But FastF1 can
  still be used normally with data of all other drivers in this session.
- `logger.debug` is the least likely to be displayed, and hence can be the
  most verbose. Information that is usually only required for development
  and debugging of FastF1 should be logged here.

By default, in FastF1, logging displays all log messages at levels higher than
``logging.INFO`` to `sys.stderr`.

.. _logging tutorial: https://docs.python.org/3/howto/logging.html#logging-basic-tutorial


Allowing optional functions to fail gracefully
----------------------------------------------

FastF1 processes lots of data that may change unexpectedly, contain unknown
values or that is not always available. Of course, the best way to deal with
this is to write code that is as robust as possible. But of course, it is not
always possible to foresee what unexpected data your code might need to deal
with. In some cases, FastF1 cannot work without some specific data being
processed correctly. But in other cases, FastF1 can still be used with limited
functionality if we prevent it from crashing when such an error is encountered.
Examples for such cases are:

- loading optional data: weather data, telemetry, ...
- doing additional (cross) validation of data
- applying corrections to improve the accuracy of data
- ...

If such a task fails, we want FastF1 to show a warning to the user. But
especially if such an error is encountered during data loading, it should not
crash FastF1 and make the whole session unavailable to the user. Loading
incomplete data is always preferred over loading no data at all.

To deal with this, FastF1 provides a special function decorator called
:func:`fastf1.logger.soft_exceptions` that can be used as follows::

  from fastf1.logger import soft_exceptions


  @soft_exceptions(descr_name="optional data processing",
                   msg="Failed to do some optional data processing",
                   logger=logger)
  def _optional_data_loading():
      ...
      return

The basic functionality of this decorator is to wrap a one big
`try: ... except Exception: ...` clause around the function call.
But additionally, if the function call fails, the `msg` is shown to the user,
using the logging level `WARNING`. The traceback is logged with the logging
level `DEBUG` and prefaced with the line `"Traceback for failure in
{descr_name}"`.
You need to pass the `logger` for the current module as a third argument to the
decorator.

This catch-all exception handling makes development more difficult, because for
example a debugger won't be able to stop on an unhandled exception. Therefore,
it is possible to easily disable the exception handling for all functions that
are decorated in this way. This is described in detail here:
:ref:`logging`.