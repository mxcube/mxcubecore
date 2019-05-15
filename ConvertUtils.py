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

import sys

__author__ = "rhfogh"
__date__ = "19/06/17"

# Constants


# 'Borrowed' from six, pending installation as a dependency
PYVERSION = sys.version_info[0]
if PYVERSION > 2:
    string_types = (str,)
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = (basestring,)
    text_type = unicode
    binary_type = str

# Conversion from kEv to A, wavelength = H_OVER_E/energy
H_OVER_E = 12.3984

# Utility functions:


def java_property(keyword, value, quote_value=False):
    """Return argument list for command line invocation setting java property"""
    if value is None:
        return ["-D" + keyword]
    else:
        if value and quote_value:
            value = quoted_string(value)
        return ["-D%s=%s" % (keyword, value)]


def command_option(keyword, value, prefix="-", quote_value=False):
    """Return argument list for command line option"""
    if value is None:
        return [prefix + keyword]
    else:
        if value and quote_value:
            value = quoted_string(value)
        else:
            value = str(value)
        return [prefix + keyword, value]


def quoted_string(text):
    """Return quoted value of a (single-line) string

    Intended for command line arguments.
    Will work for Python 2 str or unicode, OR Python 3 str and (some) bytes).
    Somewhat fragile, will definitely break for multiline strings
    or strings containint both single and double quotes
    """
    result = ensure_text(text)
    if not '"' in result:
        result = "".join(('"', result, '"'))
    elif not "'" in result:
        result = "".join(("'", result, "'"))
    else:
        result = repr(result)
    ind = 0
    for ind, char in enumerate(result):
        if char in ('"', "'"):
            break
    #
    return result[ind:]


# def to_ascii(text):
#     """Rough-and-ready conversion to bytes, intended for ascii contexts"""
#
#
#     if hasattr(text, "encode"):
#         text = text.encode("utf8", "replace")
#     return text


def convert_string_value(text):
    """Convert input string to int, float, or string (in order of priority)"""
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


# 'Borrowed' from six, pending installation as a dependency
def ensure_text(chars, encoding="utf-8", errors="strict"):
    """Coerce *chars* to six.text_type.
    For Python 2:
      - `unicode` -> `unicode`
      - `str` -> `unicode`
    For Python 3:
      - `str` -> `str`
      - `bytes` -> decoded to `str`
    """
    if isinstance(chars, binary_type):
        return chars.decode(encoding, errors)
    elif isinstance(chars, text_type):
        return chars
    else:
        raise TypeError("not expecting type '%s'" % type(chars))


# # 'Borrowed' from six, pending installation as a dependency
# def ensure_str(chars, encoding='utf-8', errors='strict'):
#     """Coerce *s* to `str`.
#     For Python 2:
#       - `unicode` -> encoded to `str`
#       - `str` -> `str`
#     For Python 3:
#       - `str` -> `str`
#       - `bytes` -> decoded to `str`
#     """
#     if not isinstance(chars, (text_type, binary_type)):
#         raise TypeError("not expecting type '%chars'" % type(s))
#     if PYVERSION < 3 and isinstance(chars, text_type):
#         chars = chars.encode(encoding, errors)
#     elif PYVERSION > 2 and isinstance(chars, binary_type):
#         chars = chars.decode(encoding, errors)
#     return chars
