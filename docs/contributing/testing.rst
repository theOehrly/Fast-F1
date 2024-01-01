.. _testing:

=======
Testing
=======

FastF1 uses the pytest_ framework.

The tests are in :file:`fastf1/tests`, and customizations to the pytest
testing infrastructure are in ``fastf1.testing``.

.. _pytest: http://doc.pytest.org/en/latest/
.. _pytest-xdist: https://pypi.org/project/pytest-xdist/


.. _testing_requirements:

Requirements
------------

To run the tests you will need to
:ref:`set up FastF1 for development <installing_for_devs>`.


Running the tests
-----------------

In the root directory of your development repository run::

   python -m pytest


pytest expects the cache directory :file:`test_cache/` to exist. You will have to create it the first time.


pytest can be configured via a lot of `command-line parameters`_. Some
particularly useful ones are:

=============================  ===========
``-v`` or ``--verbose``        Be more verbose
``-n NUM``                     Run tests in parallel over NUM
                               processes (requires pytest-xdist_)
``--capture=no`` or ``-s``     Do not capture stdout
=============================  ===========

To run a single test from the command line, you can provide a file path,
optionally followed by the function separated by two colons, e.g., (tests do
not need to be installed, but FastF1 should be)::

  pytest fastf1/tests/test_events.py::test_event_get_session_date


.. _command-line parameters: http://doc.pytest.org/en/latest/usage.html


==========================
Linting - Code style tests
==========================

FastF1 uses Ruff_ and isort_ to ensure that the code has a consistent style and
is easily readable. All code should conform to the guidelines that are defined
by PEP8_.

To check whether your code is formatted correctly, run::

  ruff check .


To check and correct the import order, run::

  python -m isort .

If you have installed the :ref:`pre-commit hooks <pre_commit_hooks>`,
these commands will also be run automatically before each commit.


.. _Ruff: https://docs.astral.sh/ruff/
.. _isort: https://pycqa.github.io/isort/
.. _PEP8: https://pep8.org/