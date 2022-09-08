#!/usr/bin/python
# -*- coding: utf-8 -*-

class Event(object):
    """
    Event is base class providing an interface
    for all subsequent(inherited) events.
    """


class InvokeEvent(Event):
    def __init__(self, message):
        self.type = 'INVOKE'
        self.message = message


class CloseEvent(Event):
    def __init__(self):
        self.type = 'CLOSE'
