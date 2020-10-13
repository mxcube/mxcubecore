#! /usr/bin/env python
# encoding: utf-8
#
# License:
#
# This file is part of MXCuBE.
#
# MXCuBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MXCuBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with MXCuBE. If not, see <https://www.gnu.org/licenses/>.

"""General data and functions, that can be shared between different HardwareObjects
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

__author__ = "rhfogh"
__date__ = "19/06/17"
__credits__ = ["MXCuBE collaboration"]

# Constants

try:
    # Python 2
    string_types = (basestring,)
    text_type = unicode
    binary_type = str
except Exception:
    # Python 3+
    string_types = (str,)
    text_type = str
    binary_type = bytes

# Conversion from kEv to A, wavelength = H_OVER_E/energy
H_OVER_E = 12.3984


# Utility functions:


def java_property(keyword, value, quote_value=False):
    """Return argument list for command line invocation setting java property

    keyword, value are stringtypes"""
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
    or strings containing both single and double quotes
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


def make_table(column_names, rows):
    """Generate string with pretty-printed table

    Args:
        column_names (Sequence[str]) : Column names
        rows (Sequence[Sequence[str]]) : List of row data

    Returns:

    """
    lines = []
    longest_cols = [
        (max([len(str(row[i])) for row in rows]) + 3) for i in range(len(rows[0]))
    ]
    longest_cols = list(
        max(longest_cols[ind], len(txt)) for ind, txt in enumerate(column_names)
    )
    ruler = "+" + "=" * sum(longest_cols) + "+"
    row_format = "| ".join(
        ["{:<" + str(longest_col) + "}" for longest_col in longest_cols]
    )

    lines.append(ruler)
    lines.append("| %s" % row_format.format(*column_names))
    lines.append(ruler)

    for row in rows:
        lines.append("| %s" % row_format.format(*row))
    lines.append(ruler)
    #
    return "\n".join(lines)
