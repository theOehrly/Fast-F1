import asyncio
import concurrent.futures
import json
import logging
import time
from collections.abc import Iterable
from typing import Optional

import requests

import fastf1
from fastf1.signalr_aio import Connection


def messages_from_raw(r: Iterable):
    """Extract data messages from raw recorded SignalR data.

    This function can be used to extract message data from raw SignalR data
    which was saved using :class:`SignalRClient` in debug mode.

    Args:
        r: Iterable containing raw SignalR responses.
    """
    ret = list()
    errorcount = 0
    for data in r:
        # fix F1's not json compliant data
        data = data.replace("'", '"') \
            .replace('True', 'true') \
            .replace('False', 'false')
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            errorcount += 1
            continue
        messages = data['M'] if 'M' in data and len(data['M']) > 0 else {}
        for inner_data in messages:
            hub = inner_data['H'] if 'H' in inner_data else ''
            if hub.lower() == 'streaming':
                # method = inner_data['M']
                message = inner_data['A']
                ret.append(message)

    return ret, errorcount


class SignalRClient:
    """A client for receiving and saving F1 timing data which is streamed
    live over the SignalR protocol.

    During an F1 session, timing data and telemetry data are streamed live
    using the SignalR protocol. This class can be used to connect to the
    stream and save the received data into a file.

    The data will be saved in a raw text format without any postprocessing.
    It is **not** possible to use this data during a session. Instead, the
    data can be processed after the session by calling
    :func:`fastf1.core.Session.load` and providing a
    :class:`~fastf1.livetiming.data.LiveTimingData` object.

    Args:
        filename: filename (opt. with path) for the output file
        filemode: one of 'w' or 'a'; append to or overwrite
            file content it the file already exists. Append-mode may be useful
            if the client is restarted during a session.
        debug: When set to true, the complete SignalR
            message is saved. By default, only the actual data from a
            message is saved.
        timeout: Number of seconds after which the client
            will automatically exit when no message data is received.
            Set to zero to disable.
        logger: By default, errors are logged to the console. If you wish to
            customize logging, you can pass an instance of
            :class:`logging.Logger` (see: :mod:`logging`).
    """
    _connection_url = 'https://livetiming.formula1.com/signalr'

    def __init__(self, filename: str, filemode: str = 'w', debug: bool = False,
                 timeout: int = 60, logger: Optional = None):

        self.headers = {'User-agent': 'BestHTTP',
                        'Accept-Encoding': 'gzip, identity',
                        'Connection': 'keep-alive, Upgrade'}

        self.topics = ["Heartbeat", "CarData.z", "Position.z",
                       "ExtrapolatedClock", "TopThree", "RcmSeries",
                       "TimingStats", "TimingAppData",
                       "WeatherData", "TrackStatus", "DriverList",
                       "RaceControlMessages", "SessionInfo",
                       "SessionData", "LapCount", "TimingData"]

        self.debug = debug
        self.filename = filename
        self.filemode = filemode
        self.timeout = timeout
        self._connection = None

        if not logger:
            logging.basicConfig(
                format="%(asctime)s - %(levelname)s: %(message)s"
            )
            self.logger = logging.getLogger('SignalR')
            self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger

        self._output_file = None
        self._t_last_message = None

    def _to_file(self, msg):
        self._output_file.write(msg + '\n')
        self._output_file.flush()

    async def _on_do_nothing(self, msg):
        # just do nothing with the message; intended for debug mode where some
        # callback method still needs to be provided
        pass

    async def _on_message(self, msg):
        self._t_last_message = time.time()
        loop = asyncio.get_running_loop()
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await loop.run_in_executor(
                    pool, self._to_file, str(msg)
                )
        except Exception:
            self.logger.exception("Exception while writing message to file")

    async def _on_debug(self, **data):
        if 'M' in data and len(data['M']) > 0:
            self._t_last_message = time.time()

        loop = asyncio.get_running_loop()
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await loop.run_in_executor(
                    pool, self._to_file, str(data)
                )
        except Exception:
            self.logger.exception("Exception while writing message to file")

    async def _run(self):
        self._output_file = open(self.filename, self.filemode)
        # Create connection
        session = requests.Session()
        session.headers = self.headers
        self._connection = Connection(self._connection_url, session=session)

        # Register hub
        hub = self._connection.register_hub('Streaming')

        if self.debug:
            # Assign error handler
            self._connection.error += self._on_debug
            # Assign debug message handler to save raw responses
            self._connection.received += self._on_debug
            hub.client.on('feed', self._on_do_nothing)
            # need to connect an async method
        else:
            # Assign hub message handler
            hub.client.on('feed', self._on_message)

        hub.server.invoke("Subscribe", self.topics)

        # Start the client
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, self._connection.start)

    async def _supervise(self):
        self._t_last_message = time.time()
        while True:
            if (self.timeout != 0
                    and time.time() - self._t_last_message > self.timeout):
                self.logger.warning(f"Timeout - received no data for more "
                                    f"than {self.timeout} seconds!")

                self._connection.close()
                while self._connection.started:
                    await asyncio.sleep(0.1)
                return

            await asyncio.sleep(1)

    async def _async_start(self):
        self.logger.info(f"Starting FastF1 live timing client "
                         f"[v{fastf1.__version__}]")
        await asyncio.gather(asyncio.ensure_future(self._supervise()),
                             asyncio.ensure_future(self._run()))
        self._output_file.close()
        self.logger.warning("Exiting...")

    def start(self):
        """Connect to the data stream and start writing the data to a file."""
        try:
            # try to get an already running loop (e.g. in newer IPython)
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # there is no running loop yet
            self._start_without_existing_loop()
            return

        try:
            __IPYTHON__  # noqa
            is_ipython = True
        except NameError:
            is_ipython = False

        if loop and is_ipython:
            raise RuntimeError(
                "Running in an asynchronous IPython session. "
                "Please use `await SignalRClient().async_start()`"
            )

        else:
            raise RuntimeError(
                "Cannot start because an asynchronous event loop already "
                "exists. You can try to use the "
                "`SignalRClient().async_start()` coroutine."
            )

    async def async_start(self):
        """
        Connect to the data stream and start writing the data to a file
        when running inside an existing event loop.

        In most cases, you want to use :func:`start` instead.
        """
        loop = asyncio.get_running_loop()
        try:
            task = loop.create_task(self._async_start())
            while not task.done():
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.warning("Async execution cancelled - exiting...")

    def _start_without_existing_loop(self):
        try:
            asyncio.run(self._async_start())
        except KeyboardInterrupt:
            self.logger.warning("Keyboard interrupt - exiting...")
