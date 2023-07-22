"""Using the Fast-F1 signalr client?
======================================

Demonstrates the usage of the SignalRClient
"""
from fastf1.livetiming.client import SignalRClient

import logging

log = logging.getLogger()
log.setLevel(logging.DEBUG)

client = SignalRClient(filename="output.txt", debug=True)
client.start()
