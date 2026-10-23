.. _documenting-fastf1:

=====================
Writing documentation
=====================

Getting started
===============

General file structure
----------------------

All documentation is built from the :file:`docs/`.  The :file:`docs/`
directory contains configuration files for Sphinx and reStructuredText
(ReST_; ``.rst``) files that are rendered to documentation pages.


Setting up the doc build
------------------------

The documentation for FastF1 is generated from reStructuredText (ReST_)
using the Sphinx_ documentation generation tool.

To build the documentation you will need to
:ref:`set up FastF1 for development <installing_for_devs>`.

Building the docs
-----------------

The documentation sources are found in the :file:`docs/` directory in the trunk.
The configuration file for Sphinx is :file:`docs/conf.py`. It controls which
directories Sphinx parses, how the docs are built, and how the extensions are
used. The examples in the documentation are built against frozen API responses that
are provided by a git submodule. Fetch it before building the documentation
for the first time (see :ref:`documenting_doc_data`)::

   git submodule update --init --depth 1 docs/data

To build the documentation in html format run the following command
from the :file:`docs/` directory:

.. code:: sh

  make html


The generated documentation can be found in :file:`docs/_build/html` and viewed
in an internet browser by opening the html files. Run the following command
to open the homepage of the documentation build:

.. code:: sh

  make show


.. _documenting_doc_data:

Documentation data
------------------

The documentation build never makes requests to the live APIs. The examples
run against a frozen snapshot of previously recorded API responses instead, so
that the documentation is reproducible and independent of the availability of
the API servers.

This data lives in a separate repository,
`fastf1-doc-data <https://github.com/theOehrly/fastf1-doc-data>`_, which is
included as a git submodule in :file:`docs/data/`. Fetch it before building the
documentation for the first time::

   git submodule update --init --depth 1 docs/data

The commit of the submodule that is referenced by FastF1 is part of every
FastF1 commit. Checking out an older version of FastF1 and updating the
submodule therefore gives you exactly the data that this version of the
documentation was built against. The continuous integration build uses the
same referenced commit.

The directory :file:`doc_cache/` that is created in the root of the repository
is used for FastF1's own parsed-data cache (stage 2 cache) while the
documentation is built. It only serves to improve performance, is not version
controlled and can be deleted at any time.

The tests use a separate dataset, see :ref:`testing_test_data`.


Adding documentation data
.........................

If an example requires data for which no response has been recorded, the build
fails at the very end and reports the affected URLs. This usually means that
the submodule is out of date, so try running
``git submodule update --init --depth 1 docs/data`` first.

If you write an example that requires data which has not been recorded yet,
you need to record it. **Please first check whether you can write your example
based on a session that is already part of the data.** Loading a single
additional race session adds roughly 30 MB of data that everybody who
contributes to FastF1 needs to download.

To record the missing data, run the following command from the :file:`docs/`
directory::

   make record-data

This deletes the stage 2 cache and the previous build output, then builds the
documentation with recording enabled. Only the missing responses are requested
from the API; data that is already available is never re-downloaded. The new
responses are written to :file:`docs/data/http_cache/`, where they show up as
untracked files, and are listed at the end of the build.

.. note::

   Recording requires an IP address that is not blocked by the F1 API. Data
   centre IP addresses are usually blocked, so this cannot be done from a CI
   runner.

Because :file:`docs/data/` is a submodule, these files need to be contributed
to the ``fastf1-doc-data`` repository:

#. Fork `fastf1-doc-data <https://github.com/theOehrly/fastf1-doc-data>`_,
   then commit the new files inside the submodule and push them to your fork::

      cd docs/data
      git status                    # you should be on a branch, not detached
      git checkout -b add-data-<topic>
      git remote add fork git@github.com:<you>/fastf1-doc-data.git
      git status                    # this should list additions only
      git add http_cache
      git commit -m "add documentation data for <session>"
      git push fork add-data-<topic>

   Recording only ever adds files. Any deletion or modification that shows up
   here means that something went wrong, so investigate before committing.
   If the push is rejected with ``shallow update not allowed``, run
   ``git fetch --unshallow origin`` first; the submodule was cloned with
   ``--depth 1``.

   Then open a pull request against ``fastf1-doc-data``.
#. Once it is merged, update the submodule reference in your FastF1 pull
   request, so that the new data is actually used::

      git submodule update --remote docs/data
      git add docs/data

   Data that only exists in a fork or that is newer than the referenced commit
   is never visible to the continuous integration build.

If you are unsure about any of this, just open your FastF1 pull request and
ask. Recording the data can also be done for you.


Writing documentation
---------------------

In general, the style guidelines and formatting conventions described in
https://matplotlib.org/stable/devel/documenting_mpl.html should be applied to
FastF1 as well.

One notable exception is that FastF1 uses the `google docstring standard
<https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_
instead of the numpydoc format.



.. _ReST: https://docutils.sourceforge.io/rst.html
.. _Sphinx: http://www.sphinx-doc.org
