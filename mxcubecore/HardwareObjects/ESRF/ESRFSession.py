from mxcubecore.HardwareObjects import Session
import os
import time
from mxcubecore.HardwareObjects import queue_model_objects


class ESRFSession(Session.Session):
    def __init__(self, name):
        Session.Session.__init__(self, name)

    def init(self):
        Session.Session.init(self)

        archive_base_directory = self["file_info"].get_property(
            "archive_base_directory"
        )
        if archive_base_directory:
            archive_folder = os.path.join(
                self["file_info"].get_property("archive_folder"), time.strftime("%Y")
            )
            queue_model_objects.PathTemplate.set_archive_path(
                archive_base_directory, archive_folder
            )
