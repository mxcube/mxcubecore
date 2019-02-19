#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import logging
import Session
import queue_model_objects_v1 as queue_model_objects

__credits__ = ["ALBA"]
__version__ = "2.3."
__category__ = "General"


class ALBASession(Session.Session):

    def get_base_data_directory(self):
        """
        Returns the base data directory for ALBA
        In ALBA the base directory already includes the user
        home directory. So
        information into account, such as if the current user
        is inhouse.

        :returns: The base data path.
        :rtype: str
        """
        if self.session_start_date:
            start_time = self.session_start_date.split(' ')[0].replace('-', '')
        else:
            start_time = time.strftime("%Y%m%d")

        if self.base_directory is not None:
            directory = os.path.join(self.base_directory, start_time)
        else:
            directory = '/tmp'
        return directory

    def get_archive_directory(self, directory=None):
        if directory is None:
            _dir = self.get_base_data_directory()
        else:
            _dir = directory

        parts = _dir.split(os.path.sep)
        user_dir = parts[5]
        session_date = parts[6]
        # remove RAW_DATA from da
        try:
            more = parts[8:]
        except Exception as e:
            more = []

        archive_dir = os.path.join(
            self.base_archive_directory,
            user_dir,
            session_date,
            *more)
        logging.getLogger("HWR").debug(
            "ALBASession. returning archive directory: %s" %
            archive_dir)
        return archive_dir

    def set_ldap_homedir(self, homedir):
        self.base_directory = homedir
        self.base_process_directory = homedir

        queue_model_objects.PathTemplate.set_data_base_path(self.base_directory)


def test_hwo(hwo):
    print hwo.get_base_data_directory()
    print hwo.get_process_directory()
    print hwo.get_archive_directory()
