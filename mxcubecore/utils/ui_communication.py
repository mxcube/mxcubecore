#! /usr/bin/env python
# encoding: utf-8
#
"""
License:

This file is part of MXCuBE.

MXCuBE is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MXCuBE is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with MXCuBE. If not, see <https://www.gnu.org/licenses/>.
"""

__copyright__ = """ Copyright © 2016 -  2023 MXCuBE Collaboration."""
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "01/03/2023"

import abc
import importlib

# These are the Qt.Colors supprted colors. Only a few are used.
# NB, LINE_EDIT_ARNING is *not* supported by Qt and is treated as a special case
WIDGET_COLOURS = [
    "BLUE",
    "WHITE",
    "GRAY",
    "LIGHT_GRAY",
    "DARK_BLUE",
    "DARK_GRAY",
    "GREEN",
    "DARK_GREEN",
    "RED",
    "LIGHT_GREEN",
    "LIGHT_RED",
    "LIGHT_YELLOW",
    "LIGHT_BLUE",
    "LIGHT_2_GRAY",
    "LIGHT_ORANGE",
    "SKY_BLUE",
    "PLUM",
    "LINE_EDIT_ORIGINAL",
    "LINE_EDIT_ACTIVE",
    "LINE_EDIT_CHANGED",
    "LINE_EDIT_ERROR",
    "LINE_EDIT_WARNING",
]


class AbstractValuesMap:
    """Abstract class for communicating with Qui Dialog"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, import_module_name=None):
        """

        Args:
            import_module_name (str): Path to import module containing pdate functions
        """
        # Override in individual objects to temporary block update functions
        self.block_updates = False
        # Function to execute whenever individual widget update functions are called
        self.update_function = None
        if import_module_name:
            self.import_module = importlib.import_module(import_module_name)
        else:
            self.import_module = None

    def set_values(self, **kwargs):
        """For each tag,val in kwargs set gui parameter tag, to value value

        Args:
            **kwargs: parameter name:value

        Returns: None

        """
        raise NotImplementedError()

    def get_values_map(self):
        """

        Returns: dict # str:parameter_name: Any:parameter_value

        """
        raise NotImplementedError()

    def reset_options(self, widget_name, **options):
        """Function to reset widgets.
        As of 202304 only the option 'value_dict' is supported
        - a label:value dictionary that sets the enum for pulldowns.
        More options may be supported in the future.

        Args:
            widget_name: Name of widget to modify
            **options: name and value of options to reset

        Returns: None

        """
        raise NotImplementedError()

    def colour_widget(self, widget_name, colour):
        """

        Args:
            widget_name (str):
            colour (str): One of WIDGET_COLOURS

        Returns: None

        """

        raise NotImplementedError()
