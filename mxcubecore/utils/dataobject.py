# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import jsonschema
import copy

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class DataObject(dict):
    """
    Object intended as a base class for data models
    """

    # See https://www.python.org/dev/peps/pep-0351/
    VERBOSE = True
    _SCHEMA = {}

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.validate()
        self._intset("_mutations", [])
        self._intset("_original", copy.deepcopy(dict(self)))
        self._intset("_previous", copy.deepcopy(dict(self)))

    def _immutable(self, *args, **kwargs):
        raise TypeError(
            "object is immutable, trying to set: %s to %s" % (args[0], args[1])
        )

    _intset = dict.__setattr__
    _setitem = dict.__setitem__
    clear = _immutable
    update = _immutable
    setdefault = _immutable
    pop = _immutable
    popitem = _immutable
    __setitem__ = _immutable
    __setattr__ = _immutable
    __delitem__ = _immutable
    __getattr__ = dict.__getitem__

    def __hash__(self):
        return id(self)

    def dangerously_set(self, key, value):
        """
        Sets the attribute name <key> to value

        Args:
            key (str): Atttribute name
            value (any): The value to set

        Returns:
            None
        """
        if self.VERBOSE:
            print(
                "ImmutableDict (%s), dangerously set %s to %s:"
                % (str(self), key, value)
            )

        self._setitem(key, value)

        try:
            self.validate()
        except jsonschema.exceptions.ValidationError:
            self._setitem(key, self._previous[key])
            raise
        else:
            self._mutations.append((key, value))
            self._intset("_previous", copy.deepcopy(dict(self)))

    def validate(self):
        """
        Validates the attributes against the schema defined in _SCHEMA
        """
        if self._SCHEMA:
            jsonschema.validate(instance=self, schema=self._SCHEMA)

    def to_mutable(self):
        """
        Returns:
            A new standard python dict with all the values
        """
        return copy.deepcopy(dict(self))
