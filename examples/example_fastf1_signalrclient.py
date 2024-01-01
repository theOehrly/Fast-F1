"""Using the Fast-F1 signalr client?
======================================

Demonstrates the usage of the SignalRClient
"""
import logging

from fastf1.livetiming.client import SignalRClient


log = logging.getLogger()
log.setLevel(logging.DEBUG)

client = SignalRClient(filename="output.txt", debug=True)
client.start()
