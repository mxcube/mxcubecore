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

class AbstractValuesMap:
    """Abstract class for communicating with Qui Dialog"""

    __metaclass__ = abc.ABCMeta

    def set_values(self, **kwargs):
        """For each tag,val in kwargs set gui parametet tag, to value value

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
