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

# Constants

# Conversion from kEv to A, wavelength = h_over_e/energy
h_over_e = 12.3984


# Enumerations:


# Utility functions:

def java_property(keyword, value):
    """Return argument list for command line invocation setting java property"""
    if value is None:
        return ['-D' + keyword]
    else:
        return ['-D%s=%s' % (keyword, value)]

def command_option(keyword, value, prefix='-'):
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
