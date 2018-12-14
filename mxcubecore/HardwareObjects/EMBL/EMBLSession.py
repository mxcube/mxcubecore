"""
Session hardware object.

Contains information regarding the current session and methods to
access and manipulate this information.
"""
import os
import time

from Session import Session

class EMBLSession(Session):

    def get_base_data_directory(self):
        """
        Returns the base data directory taking the 'contextual'
        information into account, such as if the current user
        is inhouse.

        :returns: The base data path.
        :rtype: str
        """
        user_category = ""
        directory = ""

        if self.session_start_date:
            start_time = self.session_start_date.split(" ")[0].replace("-", "")
        else:
            start_time = time.strftime("%Y%m%d")

        if os.getenv("SUDO_USER"):
            user = os.getenv("SUDO_USER")
        else:
            user = os.getenv("USER")
        return os.path.join(
            self.base_directory,
            str(os.getuid()) + "_" + str(os.getgid()),
            user,
            start_time,
        )

    def get_archive_directory(self):
        archive_directory = os.path.join(
            self["file_info"].getProperty("archive_base_directory"),
            self["file_info"].getProperty("archive_folder"),
        )

        folders = self.get_base_data_directory().split("/")
        archive_directory = os.path.join(archive_directory, *folders[4:])

        return archive_directory
