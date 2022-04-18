.. _testing:

=======
Testing
=======

FastF1 uses the pytest_ framework.

The tests are in :file:`fastf1/tests`, and customizations to the pytest
testing infrastructure are in :mod:`fastf1.testing`.

.. _pytest: http://doc.pytest.org/en/latest/
.. _pytest-xdist: https://pypi.org/project/pytest-xdist/


.. _testing_requirements:

Requirements
------------

To run the tests you will need to
:ref:`set up FastF1 for development <installing_for_devs>`. Note in
particular the additional dependencies for testing.


Running the tests
-----------------

In the root directory of your development repository run::

   python -m pytest


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
