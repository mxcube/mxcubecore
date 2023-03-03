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

    def get_default_subdir(self, sample_data: dict) -> str:
        """
        Gets the default sub-directory based on sample information

        Args:
           sample_data: Lims sample dictionary

        Returns:
           Sub-directory path string
        """

        subdir = ""

        if isinstance(sample_data, dict):
            sample_name = sample_data.get("sampleName", "")
            protein_acronym = sample_data.get("proteinAcronym", "")
        else:
            sample_name = sample_data.name
            protein_acronym = sample_data.crystals[0].protein_acronym

        # if protein_acronym:
        #    subdir = "%s/%s-%s/" % (protein_acronym, protein_acronym, sample_name)
        # else:
        subdir = "%s/" % sample_name

        return subdir.replace(":", "-")

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
