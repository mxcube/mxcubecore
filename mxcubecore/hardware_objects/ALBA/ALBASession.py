import os
import time
import logging

from mxcubecore.hardware_objects import Session
from mxcubecore.hardware_objects import queue_model_objects


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
            start_time = self.session_start_date.split(" ")[0].replace("-", "")
        else:
            start_time = time.strftime("%Y%m%d")

        # directory = os.path.join(self.base_directory, self.get_proposal(), 'DATA', start_time)
        if self.base_directory is not None:
            directory = os.path.join(self.base_directory, start_time)
        else:
            directory = "/tmp"
        return directory

    def get_archive_directory(self, directory=None):
        if directory is None:
            thedir = self.get_base_data_directory()
        else:
            thedir = directory

        parts = thedir.split(os.path.sep)
        user_dir = parts[5]
        session_date = parts[6]
        # remove RAW_DATA from da
        try:
            more = parts[8:]
        except Exception:
            more = []

        archive_dir = os.path.join(
            self.base_archive_directory, user_dir, session_date, *more
        )
        # if 'RAW_DATA' in thedir:
        #    thedir = thedir.replace('RAW_DATA','ARCHIVE')
        # else:
        #    thedir = os.path.join(thedir, 'ARCHIVE')

        logging.getLogger("HWR").debug(
            "ALBASession. returning archive directory: %s" % archive_dir
        )
        return archive_dir

    def set_ldap_homedir(self, homedir):
        self.base_directory = homedir
        self.base_process_directory = homedir

        queue_model_objects.PathTemplate.set_data_base_path(self.base_directory)


def test_hwo(hwo):
    print(hwo.get_base_data_directory())
    print(hwo.get_process_directory())
    print(hwo.get_archive_directory())
