"""
Live Timing Client - :mod:`fastf1.livetiming`
=============================================

.. warning::
    The live timing client does only support Python 3.8 or 3.9!

This module can be used to save live timing data during a session.
It is **not** possible to do real-time processing of the data.


There are two ways to interact with this module.

    - From a python script by creating an instance of
      :class:`.SignalRClient`

    - From the command line by calling ``python -m fastf1.livetiming``


Usage Example
-------------

1. Record live timing data during a session

.. code-block:: console

    python -m fastf1.livetiming save saved_data.txt


2. Load this data into FastF1 after the session has finished

.. code-block::

    import fastf1
    from fastf1.livetiming.data import LiveTimingData

    fastf1.Cache.enable_cache('cache_directory')

    livedata = LiveTimingData('saved_data.txt')
    session = fastf1.get_session(2021, 'testing', 1)
    session.load(livedata=livedata)

optionally you can load live timing data from two or more files

.. code-block::

    livedata = LiveTimingData('saved_data_1.txt', 'saved_data_2.txt')




Important Notes
---------------

- You should try to record a full session whenever possible. Recording should
  start 2-3 minutes before a sessions starts. The api parser may not be able to
  deal with the data correctly if the beginning of a session is missing.
  Your mileage may vary depending on what and how much data is missing.

- You should not mix recorded live timing data and data requested from the api
  after a session. The data will likely not be synchronized correctly.

- You should use the cache with saved live timing data too. This will speed up
  loading of the data considerably after the first run.

- You need to used different cache directories if you want to cache
  saved live timing data and api data **for the same session**!
  The cache cannot tell the data sources apart. If cached data from one source
  already exists it will not be reloaded automatically from a different source.

- You need to force a cache update if you modify the :class:`LiveTimingData`
  (e.g. by adding a second file). The cache cannot tell that the input source
  was modified and will still use the old cached data.

  You can force-refresh the cache::

    fastf1.Cache.enable_cache('cache_directory', force_renew=True)

  You only need to use ``forece_renew=True`` once after modifying the
  input data.

- The SignalR Client seems to get disconnected after 2 hours of recording. It looks
  like the connection is terminated by the server. You need to manually start a
  second recording before the first one disconnects if you want to have no gap in
  your recording.

  Use a different output file name for the second (or any subsequent) recording.
  You can then load :class:`.data.LiveTimingData` from multiple files. The files need
  to be provided in chronological order. The content of the files may overlap.
  Data from overlapping recordings is recognized and will not be loaded as a
  duplicate.




Command Line Interface
----------------------

Available commands and options when calling ``python -m fastf1.livetiming``

The module has two main commands

.. code-block:: console

      {save,extract}
        save          Save live timing data
        extract       Extract messages from saved debug-mode data

Save
++++

**The main command for recording live timing data during a session**

.. code-block:: console

    usage: python -m fastf1.livetiming save [-h] [--append] [--debug] [--timeout TIMEOUT] file

    positional arguments:
      file               Output file name

    optional arguments:
      -h, --help         show this help message and exit
      --append           Append to output file. By default the file is overwritten if it exists already.
      --debug            Enable debug mode: save full SignalR message, not just the data.
      --timeout TIMEOUT  Timeout in seconds after which the client will automatically exit if no data is received


Extract
+++++++

**Only for when data was saved with the optional '--debug' argument**

Recording in debug mode saves the full SignalR messages as received. The non debug mode saves only the
important data part of a message. The data part of each message needs to be extracted to utilize the debug-mode
data.
The extracted data is the same data you get when saving without the '--debug' argument.

.. code-block:: console

    usage: python -m fastf1.livetiming extract [-h] input output

    positional arguments:
      input       Input file name
      output      Output file name

    optional arguments:
      -h, --help  show this help message and exit




Live Timing Client
------------------

.. automodule:: fastf1.livetiming.client
    :members:
    :undoc-members:
    :show-inheritance:


Live Timing Data Object
-----------------------

.. automodule:: fastf1.livetiming.data
    :members:
    :undoc-members:
    :show-inheritance:

"""
