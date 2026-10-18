.. _`accounts-auth`:

F1TV Account Authentication
===========================

F1TV Account Usage
------------------

FastF1 can require an active F1TV Access/Pro/Premium subscription to access certain data.
Currently, authentication is only required when using the :ref:`livetiming`.
All data that is obtained after the session has ended can be accessed without authentication.

When FastF1 encounters a feature that requires authentication, it will automatically prompt
you to authenticate with your F1TV account if you haven't done so already.

Authentication Workflow
-----------------------

When authentication is required, FastF1 will:

1. Check for an existing valid authentication token
2. If no valid token exists, sign in to your Formula 1 account with the selected sign-in method
3. After successful login, store the authentication token locally
4. Use this token for subsequent data requests

The stored token is independent of the sign-in method that was used to obtain it.


Sign-in Methods
---------------

FastF1 supports two sign-in methods.

``password`` (default)
    FastF1 signs in directly with your Formula 1 account email and password. The credentials
    are read from the environment variables ``F1_USERNAME`` and ``F1_PASSWORD``. If they are
    not set and the session is interactive, you are prompted for them. Your credentials are
    only sent to Formula 1 and are never stored by FastF1.

``browser``
    FastF1 provides a URL that you need to open in a browser to login to F1TV.
    A browser addon is required for FastF1 to perform this login. If you have not already
    installed this addon, you will be redirected to a page that offers download options for
    the addon. You can also visit f1login.fastf1.dev directly. If the addon is installed and
    working correctly, you will be redirected to see a success status message. Else, you will
    be provided with download options for the addon.

    .. note::

        This method is not supported in hosted environments like Google Colab or in
        WebAssembly based environments like Jupyter Lite.

The sign-in method is selected, in order of precedence:

1. by calling :func:`fastf1.set_auth_method` in your script, e.g.
   ``fastf1.set_auth_method('browser')``
2. by setting the environment variable ``FASTF1_AUTH_METHOD`` to ``password`` or ``browser``
3. else, ``password`` is used

.. autofunction:: fastf1.set_auth_method


Command Line Interface
----------------------

FastF1 also provides command line options for managing F1TV authentication:

.. code-block:: console

    python -m fastf1 auth f1tv [--authenticate] [--clear] [--status] [--method {password,browser}]

Options:
  --authenticate  Start the authentication process manually
  --clear         Remove stored authentication token
  --status        Display current authentication status
  --method        Sign-in method to use with ``--authenticate``
