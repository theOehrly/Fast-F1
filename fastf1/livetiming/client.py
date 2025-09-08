import json
import logging
import time
from collections.abc import Iterable
from typing import Optional

import requests
from signalrcore.hub_connection_builder import HubConnectionBuilder
from signalrcore.messages.completion_message import CompletionMessage

import fastf1
from fastf1.internals.f1auth import get_auth_token


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
    # legacy naming, this is now a SignalR Core client
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
        no_auth: If set to true, the client will attempt to connect without
            authentication. This may only work for some sessions or may only
            return empty or partial data.
    """
    _connection_url = 'wss://livetiming.formula1.com/signalrcore'
    _negotiate_url = 'https://livetiming.formula1.com/signalrcore/negotiate'


    def __init__(self,
                 filename: str,
                 filemode: str = 'w',
                 debug: bool = False,
                 timeout: int = 60,
                 logger: Optional = None,
                 no_auth: bool = False):

        if debug:
            raise ValueError("Debug mode is no longer supported.")

        self.headers = {}

        self.topics = ["Heartbeat","AudioStreams","DriverList",
                       "ExtrapolatedClock","RaceControlMessages",
                       "SessionInfo","SessionStatus","TeamRadio",
                       "TimingAppData","TimingStats","TrackStatus",
                       "WeatherData","Position.z","CarData.z",
                       "ContentStreams","SessionData","TimingData",
                       "TopThree", "RcmSeries", "LapCount"]

        self.filename = filename
        self.filemode = filemode
        self.timeout = timeout

        self._no_auth = no_auth

        self._connection = None
        self._is_connected = False

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

    def _on_message(self, msg: list | CompletionMessage):
        self._t_last_message = time.time()

        if isinstance(msg, CompletionMessage):
            data = []
            for key in msg.result.keys():
                data.append([key, json.dumps(msg.result[key]), ''])
            formatted = '\n'.join(map(str, data))

        elif isinstance(msg, list):
            formatted = str(msg)

        else:
            self.logger.error(f"Unknown message type: {type(msg)}")
            return

        try:
            self._output_file.write(formatted + '\n')
            self._output_file.flush()
        except Exception:
            self.logger.exception("Exception while writing message to file")

    def _on_connect(self):
        self._is_connected = True
        self.logger.info("Connection established")

    def _on_close(self):
        self._is_connected = False
        self.logger.info("Connection closed")

    def _run(self):
        self._output_file = open(self.filename, self.filemode)

        # Pre-negotiate to the get a valid AWSALBCORS header token
        r = requests.options(self._negotiate_url, headers=self.headers)
        self.headers.update(
            {"Cookie": f"AWSALBCORS={r.cookies['AWSALBCORS']}"}
        )

        # Configure and create connection
        options = {
            "verify_ssl": True,
            "access_token_factory": None if self._no_auth else get_auth_token,
            "headers": self.headers
        }

        self._connection = HubConnectionBuilder() \
            .with_url(self._connection_url, options=options) \
            .configure_logging(logging.INFO) \
            .build()
            # TODO: enable auto reconnect?

        self._connection.on_open(self._on_connect)
        self._connection.on_close(self._on_close)
        self._connection.on('feed', self._on_message)

        self._connection.start()

        # wait for connection to be established
        while not self._is_connected:
            time.sleep(0.1)

        self._connection.send(
            "Subscribe", [self.topics], on_invocation=self._on_message
        )

    def _supervise(self):
        # check if data is still being received and exit if not
        self._t_last_message = time.time()
        while True:
            if (self.timeout != 0
                    and time.time() - self._t_last_message > self.timeout):

                self.logger.warning(f"Timeout - received no data for more "
                                    f"than {self.timeout} seconds!")

                self._exit()
                return

            time.sleep(1)

    def _exit(self):
        self._connection.stop()
        self._output_file.close()

    def start(self):
        """Connect to the data stream and start writing the data to a file."""
        self.logger.info(f"Starting FastF1 live timing client "
                         f"[v{fastf1.__version__}]")
        self._run()
        try:
            self._supervise()
        except KeyboardInterrupt:
            self.logger.info("Exiting...")
            self._exit()

    async def async_start(self):
        """
        :meta private:
        """
        raise NotImplementedError(
            "This method is no longer provided because the SignalR client no "
            "longer uses asyncio! Please use `.start` instead."
        )
