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


In addition, the following FastF1-specific options are available:

===========================  ===========
``--no-f1-tel-api``          Skip tests that use data from the F1 telemetry
                             API
``--ergast-api``             Run the tests that use data from the Ergast API
                             (skipped by default)
``--prj-doc``                Run *only* the tests for project structure and
                             documentation
``--slow``                   Run the extremely slow tests as well (this may
                             take 30 minutes or more)
``--create-http-cache``      Record missing test data from the live APIs,
                             see :ref:`testing_test_data`
===========================  ===========


.. _command-line parameters: http://doc.pytest.org/en/latest/usage.html


.. _testing_test_data:

Test data
---------

The tests never make requests to the live APIs. They run against a frozen
snapshot of previously recorded API responses instead, so that test results are
reproducible and independent of the availability of the API servers.

This test data lives in a separate repository,
`fastf1-test-data <https://github.com/theOehrly/fastf1-test-data>`_, which is
included as a git submodule in :file:`fastf1/testing/data/`. Fetch it before
running the tests for the first time::

   git submodule update --init --depth 1

The submodule contains the recorded API responses in :file:`http_cache/` as
well as the static test files that some tests read directly, namely the
live timing data in :file:`livedata/` and the mocked API responses in
:file:`cache_test/`.

The commit of the submodule that is referenced by FastF1 is part of every
FastF1 commit. Checking out an older version of FastF1 and updating the
submodule therefore gives you exactly the test data that this version was
developed against. The continuous integration tests use the same referenced
commit, so that they test against the same data as a local test run.

The directory :file:`test_cache/` is used for FastF1's own parsed-data cache
while the tests run. It is not version controlled and can be deleted at any
time.


Adding test data
................

If a test fails because no test data is available for a request, pytest will
report the affected URLs at the end of the test run. This usually means that
the submodule is out of date, so try running
``git submodule update --init --depth 1`` first.

If you write a test that requires data which has not been recorded yet, you
need to record it. **Please first check whether you can write your test based
on a session that is already part of the test data.** Loading a single
additional race session adds roughly 30 MB of data that everybody who
contributes to FastF1 needs to download.

To record the missing data, run the affected tests with::

   python -m pytest --create-http-cache fastf1/tests/test_my_new_test.py

Only the missing responses are requested from the API; data that is already
available is never re-downloaded. The new responses are written to
:file:`fastf1/testing/data/http_cache/`, where they show up as untracked
files.

Because :file:`fastf1/testing/data/` is a submodule, these files need to be
contributed to the ``fastf1-test-data`` repository:

#. Fork `fastf1-test-data <https://github.com/theOehrly/fastf1-test-data>`_,
   then commit the new files inside the submodule and push them to your fork::

      cd fastf1/testing/data
      git status                    # you should be on a branch, not detached
      git checkout -b add-data-<topic>
      git remote add fork git@github.com:<you>/fastf1-test-data.git
      git status                    # this should list additions only
      git add http_cache
      git commit -m "add test data for <session>"
      git push fork add-data-<topic>

   Recording only ever adds files. Any deletion or modification that shows up
   here means that something went wrong, so investigate before committing.
   If the push is rejected with ``shallow update not allowed``, run
   ``git fetch --unshallow origin`` first; the submodule was cloned with
   ``--depth 1``.

   Then open a pull request against ``fastf1-test-data``.
#. Once it is merged, update the submodule reference in your FastF1 pull
   request, so that the new data is actually used::

      git submodule update --remote fastf1/testing/data
      git add fastf1/testing/data

   Data that only exists in a fork or that is newer than the referenced commit
   is never visible to the continuous integration tests.

If you are unsure about any of this, just open your FastF1 pull request and
ask. Recording the data can also be done for you.


Linting - Code style tests
--------------------------

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


Github Actions CI Tests
-----------------------

FastF1 uses Github Actions to run the tests on every push to the repository and
when updating a pull request. Usually, you should just let all tests run and
make sure that they are passing.

In rare cases, it may be useful to skip some tests. You can do this by adding
a specific comment to the commit message. The following comments are supported:

- ``[skip-pytest]``: Skip pytest runs on all Python versions
- ``[skip-ruff]``: Skip Ruff code style checks
- ``[skip-isort]``: Skip isort import order checks
- ``[skip-doc-build]``: Skip building the documentation
- ``[skip-readme-test]``: Skip the README render test for PyPI
