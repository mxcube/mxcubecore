#! /usr/bin/env python
# encoding: utf-8#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.

"""General data and functions, that can be shared between different HardwareObjects

WARNING This must *always* be imported directly:
'import General', 'from General import', ...
Using from HardwareObjects import General (etc.) causes it to be imported twice
so that States.On == States.ON is *not* always true.
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals
__author__ = "rhfogh"
__date__ = "19/06/17"


import enum


# Constants

# Conversion from kEv to A, wavelength = h_over_e/energy
h_over_e = 12.3984


# Enumerations:

@enum.unique
class States(enum.Enum):
    """Standard device states, based on TangoShutter states.
    SardanaMotor.state_map, and DiffractometerState,
    for general use across HardwareObjects.

    Limited to a common set of states.

    Grammar of tags corrected ('CLOSE->CLOSED, DISABLE->DISABLED) relative
    to Tango states, so you can echo them to the UI without misunderstanding"""

    CLOSED = 0
    OPEN = 1  # Also used for workflow 'Expecting input'
    ON = 2  # Could be used to mean 'Connected'.
    OFF = 3  # Could be used to mean 'Disconnected'
    INSERT = 4
    EXTRACT = 5
    MOVING = 6
    STANDBY = 7  # Could be used to mean 'Ready'
    FAULT = 8
    INIT = 9
    RUNNING = 10
    ALARM = 11
    DISABLED = 12
    UNKNOWN = 13


# Utility functions:

def javaProperty(keyword, value):
    """Return argument list for command line invocation setting java property"""
    if value is None:
        return ['-D' + keyword]
    else:
        return ['-D%s=%s' % (keyword, value)]

def commandOption(keyword, value, prefix='-'):
    """Return argument list for command line option"""
    if value is None:
        return [prefix + keyword]
    else:
        return [prefix + keyword, str(value)]

def to_ascii(text):
    """Rough-and-ready conversion to bytes, intended for ascii contexts"""

    if hasattr(text, 'encode'):
        return text.encode('utf8', 'replace')
    else:
        return text

def convert_string_value(text):
    """Convert in put string to int, float, or sstring (in order of priority)"""
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text
