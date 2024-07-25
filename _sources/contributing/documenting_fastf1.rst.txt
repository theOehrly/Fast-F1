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
used. To build the documentation in html format run the following command
from the :file:`docs/` directory:

.. code:: sh

  make html


The documentation build expects the cache directory :file:`doc_cache/` to exist
in the project root.
You will have to create it manually the first time you build the documentation.


The generated documentation can be found in :file:`docs/_build/html` and viewed
in an internet browser by opening the html files. Run the following command
to open the homepage of the documentation build:

.. code:: sh

  make show


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
