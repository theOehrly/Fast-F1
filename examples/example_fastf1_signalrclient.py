from fastf1.livetiming.client import SignalRClient

import asyncio
import logging

log = logging.getLogger()
log.setLevel(logging.DEBUG)

client = SignalRClient(filename="output.txt", debug=True)
asyncio.run(client.start())
