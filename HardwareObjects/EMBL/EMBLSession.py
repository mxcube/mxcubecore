#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
Session hardware object.

Contains information regarding the current session and methods to
access and manipulate this information.
"""

import os
import time

from HardwareRepository.HardwareObjects.Session import Session


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLSession(Session):
    """
    EMBLSession
    """

    def __init__(self, name):
        Session.__init__(self, name)
        self.start_time = time.strftime("%Y%m%d")

    def get_base_data_directory(self):
        """
        Returns the base data directory taking the 'contextual'
        information into account, such as if the current user
        is inhouse.

        :returns: The base data path.
        :rtype: str
        """
        if os.getenv("SUDO_USER"):
            user = os.getenv("SUDO_USER")
        else:
            user = os.getenv("USER")
        return os.path.join(
            self.base_directory,
            user,
            self.start_time,
        )

    """
    def get_base_process_directory(self):
        process_directory = self["file_info"].getProperty("processed_data_base_directory")
        folders = self.get_base_data_directory().split("/")

        process_directory = os.path.join(process_directory,
                                         *folders[4:])
        process_directory = process_directory + "/" + \
               self["file_info"].getProperty("processed_data_folder_name")

        return process_directory
    """

    def get_base_process_directory(self):
        """
        Returns base process directory
        :return: str
        """
        if self.session_start_date:
            start_time = self.session_start_date.split(" ")[0].replace("-", "")
        else:
            start_time = time.strftime("%Y%m%d")

        if os.getenv("SUDO_USER"):
            user = os.getenv("SUDO_USER")
        else:
            user = os.getenv("USER")

        return os.path.join(
            self.base_process_directory, user, start_time, "PROCESSED_DATA"
        )
