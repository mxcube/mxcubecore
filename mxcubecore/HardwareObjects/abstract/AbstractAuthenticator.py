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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.


import abc

from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2010- 2022 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractAuthenticator(HardwareObject):
    __metaclass__ = abc.ABCMeta

    def init(self) -> None:
        super().init()

    @abc.abstractmethod
    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with credentials username, password

        Args:
            username: username
            password: password

        Returns:
            True on success otherwise false
        """
        pass

    @abc.abstractmethod
    def invalidate(username: str) -> None:
        """
        de-authetnicate user with <username>

        Args:
            username: username
        """
