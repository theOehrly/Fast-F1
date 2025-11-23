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
2. If no valid token exists, provide a URL that the user needs to open in a browser to login to F1TV
3. After successful login, store the authentication token locally
4. Use this token for subsequent data requests

A browser addon is required for FastF1 to perform this login. If you have not already installed this addon, you will
be redirected to a page that offers download options for the addon.
You can also visit f1login.fastf1.dev directly. If the addon is installed and working correctly, you will be redirected
to see a success status message. Else, you will be provided with download options for the addon.


Command Line Interface
----------------------

FastF1 also provides command line options for managing F1TV authentication:

.. code-block:: console

    python -m fastf1 auth f1tv [--authenticate] [--clear] [--status]

Options:
  --authenticate  Start the authentication process manually
  --clear         Remove stored authentication token
  --status        Display current authentication status



