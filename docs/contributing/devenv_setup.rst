.. _installing_for_devs:

=====================================
Setting up FastF1 for development
=====================================

.. _dev-environment:

Creating a dedicated environment
================================
You should set up a dedicated environment to decouple your FastF1
development from other Python and FastF1 installations on your system.
Here we use python's virtual environment `venv`_, but you may also use others
such as conda.

.. _venv: https://docs.python.org/3/library/venv.html

A new environment can be set up with ::

   python -m venv <file folder location>

and activated with one of the following::

   source <file folder location>/bin/activate  # Linux/macOS
   <file folder location>\Scripts\activate.bat  # Windows cmd.exe
   <file folder location>\Scripts\Activate.ps1  # Windows PowerShell

Whenever you plan to work on FastF1, remember to activate the development
environment in your shell.

Retrieving the latest version of the code
=========================================

FastF1 is hosted at https://github.com/theOehrly/Fast-F1.git.

    git clone https://github.com/theOehrly/Fast-F1.git

This will place the sources in a directory :file:`Fast-F1` below your
current working directory.

If you have the proper privileges, you can use ``git@`` instead of
``https://``, which works through the ssh protocol and might be easier to use
if you are using 2-factor authentication.

Installing FastF1 in editable mode
======================================
Install FastF1 in editable mode from the :file:`Fast-F1` directory
using the command ::

    python -m pip install -e .

The 'editable/develop mode', builds everything and places links in your Python
environment so that Python will be able to import FastF1 from your
development source directory. This allows you to import your modified version
of FastF1 without re-installing after every change.

.. _install_pre_commit:

Installing pre-commit hooks
===========================
You can optionally install `pre-commit <https://pre-commit.com/>`_ hooks.
These will automatically check flake8 and other style issues when you run
``git commit``. The hooks are defined in the top level
``.pre-commit-config.yaml`` file. To install the hooks ::

    pip install pre-commit
    pre-commit install

Installing additional dependencies for development
==================================================
To install additional dependencies for development, testing and building of the
documentation, run the following command within the :file:`Fast-F1` directory::

    python -m pip install -r requirements-dev.txt
