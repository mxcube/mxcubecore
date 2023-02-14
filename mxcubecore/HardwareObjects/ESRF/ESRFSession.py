from mxcubecore.HardwareObjects import Session
import os
import time
from mxcubecore.model import queue_model_objects


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


    def get_image_directory(self, sub_dir=None):
        """
        Returns the full path to images, using the name of each of
        data_nodes parents as sub directories.

        :param data_node: The data node to get additional
                          information from, (which will be added
                          to the path).
        :type data_node: TaskNode

        :returns: The full path to images.
        :rtype: str
        """
        data_path = self.get_base_image_directory()

        if sub_dir:
            run_num = 0
            data_path = os.path.join(
                self.get_base_image_directory(), sub_dir, f"run_{run_num}/"
            )

            while os.path.exists(data_path):
                data_path = os.path.join(
                    self.get_base_image_directory(), sub_dir, f"run_{run_num}/"
                )
                run_num += 1

        return data_path