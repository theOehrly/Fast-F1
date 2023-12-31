
.. _pr-guidelines:

***********************
Pull request guidelines
***********************

Pull requests (PRs) are the mechanism for contributing to FastF1s code and
documentation.

Summary for PR authors
======================

.. note::

   * We value contributions from people with all levels of experience. In
     particular if this is your first PR not everything has to be perfect.
     We'll guide you through the PR process.
   * Nevertheless, try to follow the guidelines below as well as you can to
     help make the PR process quick and smooth.
   * Be patient with reviewers. We try our best to respond quickly, but we
     have limited bandwidth. If there is no feedback within a couple of days,
     please ping us by posting a comment to your PR.

When making a PR, pay attention to:

.. rst-class:: checklist

* Adhere to the :ref:`coding_guidelines`.
* Update the :ref:`documentation <pr-documentation>` if necessary.
* Aim at making the PR as "ready-to-go" as you can. This helps to speed up
  the review process.
* It is ok to open incomplete or work-in-progress PRs if you need help or
  feedback from the developers. You may mark these as
  `draft pull requests <https://docs.github.com/en/github/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests#draft-pull-requests>`_
  on GitHub.
* When updating your PR, instead of adding new commits to fix something, please
  consider amending your initial commit(s) to keep the history clean.
  You can achieve this using

  .. code-block:: bash

     git commit --amend --no-edit
     git push [your-remote-repo] [your-branch] --force-with-lease

See also :ref:`contributing` for how to make a PR.

.. _pr-guidelines-details:

Detailed guidelines
===================

.. _pr-documentation:

Documentation
-------------

* Every new feature should be documented.  If it's a new module, don't
  forget to add a new rst file to the API docs.

* Each high-level function should have a small example in
  the ``Examples`` section of the docstring.  This should be as simple as
  possible to demonstrate the method.  More complex examples should go into
  a dedicated example file in the :file:`examples` directory, which will be
  rendered to the examples gallery in the documentation.

* Build the docs and make sure all formatting warnings are addressed.

* See :ref:`documenting-fastf1` for our documentation style guide.

* If your change is a major new feature, update
  :file:`docs/changelog.rst`.

.. _pr-automated-tests:

Automated tests
---------------

Whenever a pull request is created or updated, various automated test tools
will run on all supported versions of Python.

Make sure that all test are passing. (All checks are listed at the bottom of
the GitHub page of your pull request)
