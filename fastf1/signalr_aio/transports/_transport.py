#!/usr/bin/python
# -*- coding: utf-8 -*-

# python compatiblity for <3.6
try:
    ModuleNotFoundError
except NameError:
    ModuleNotFoundError = ImportError

# -----------------------------------
# Internal Imports
from ._exceptions import ConnectionClosed
from ._parameters import WebSocketParameters
from ._queue_events import InvokeEvent, CloseEvent

# -----------------------------------
# External Imports
try:
    from ujson import dumps, loads
except ModuleNotFoundError:
    from json import dumps, loads
import websockets
import asyncio

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ModuleNotFoundError:
    pass


class Transport:
    def __init__(self, connection):
        self._connection = connection
        self._ws_params = None
        self._conn_handler = None
        self.ws_loop = None
        self.invoke_queue = None
        self.ws = None
        self._set_loop_and_queue()

    # ===================================
    # Public Methods

    def start(self):
        self._ws_params = WebSocketParameters(self._connection)
        self._connect()
        if not self.ws_loop.is_running():
            self.ws_loop.run_forever()

    def send(self, message):
        asyncio.Task(self.invoke_queue.put(InvokeEvent(message)), loop=self.ws_loop)

    def close(self):
        asyncio.Task(self.invoke_queue.put(CloseEvent()), loop=self.ws_loop)

    # -----------------------------------
    # Private Methods

    def _set_loop_and_queue(self):
        try:
            self.ws_loop = asyncio.get_event_loop()
        except RuntimeError:
            self.ws_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.ws_loop)
        self.invoke_queue = asyncio.Queue()

    def _connect(self):
        self._conn_handler = asyncio.ensure_future(self._socket(self.ws_loop), loop=self.ws_loop)

    async def _socket(self, loop):
        async with websockets.connect(self._ws_params.socket_url, extra_headers=self._ws_params.headers,
                                      loop=loop) as self.ws:
            self._connection.started = True
            await self._master_handler(self.ws)

    async def _master_handler(self, ws):
        consumer_task = asyncio.ensure_future(self._consumer_handler(ws), loop=self.ws_loop)
        producer_task = asyncio.ensure_future(self._producer_handler(ws), loop=self.ws_loop)
        done, pending = await asyncio.wait([consumer_task, producer_task],
                                           return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()

    async def _consumer_handler(self, ws):
        while True:
            message = await ws.recv()
            if len(message) > 0:
                data = loads(message)
                await self._connection.received.fire(**data)

    async def _producer_handler(self, ws):
        while True:
            try:
                event = await self.invoke_queue.get()
                if event is not None:
                    if event.type == 'INVOKE':
                        await ws.send(dumps(event.message))
                    elif event.type == 'CLOSE':
                        await ws.close()
                        while ws.open is True:
                            await asyncio.sleep(0.1)
                        else:
                            self._connection.started = False
                            break
                else:
                    break
                self.invoke_queue.task_done()
            except Exception as e:
                raise e