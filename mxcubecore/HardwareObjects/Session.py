"""
Session hardware object.

Contains information regarding the current session and methods to
access and manipulate this information.
"""
import os
import time
import socket

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.model.queue_model_objects import PathTemplate
from typing import Tuple


default_raw_data_folder = "RAW_DATA"
default_processed_data_folder = "PROCESSED_DATA"
default_archive_folder = "ARCHIVE"


class Session(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.synchrotron_name = None
        self.beamline_name = None

        self.session_id = None
        self.proposal_code = None
        self.proposal_number = None
        self.proposal_id = None
        self.in_house_users = []
        self.endstation_name = None
        self.session_start_date = None
        self.user_group = ""
        self.email_extension = None
        self.template = None

        self.default_precision = 5
        self.suffix = None

        self.base_directory = None
        self.base_process_directory = None
        self.base_archive_directory = None

        self.raw_data_folder_name = default_raw_data_folder
        self.processed_data_folder_name = default_processed_data_folder

    # Framework-2 method, inherited from HardwareObject and called
    # by the framework after the object has been initialized.
    def init(self):
        self.synchrotron_name = self.get_property("synchrotron_name")
        self.beamline_name = self.get_property("beamline_name")
        self.endstation_name = self.get_property("endstation_name").lower()

        self.suffix = self["file_info"].get_property("file_suffix")
        self.template = self["file_info"].get_property("file_template")

        base_directory = self["file_info"].get_property("base_directory")

        base_process_directory = self["file_info"].get_property(
            "processed_data_base_directory"
        )

        base_archive_directory = self["file_info"].get_property(
            "archive_base_directory"
        )

        folder_name = self["file_info"].get_property("raw_data_folder_name")
        if folder_name and folder_name.strip():
            self.raw_data_folder_name = folder_name

        folder_name = self["file_info"].get_property("processed_data_folder_name")
        if folder_name and folder_name.strip():
            self.processed_data_folder_name = folder_name

        archive_folder = self["file_info"].get_property("archive_folder")
        if archive_folder:
            archive_folder = archive_folder.strip()
        if not archive_folder:
            archive_folder = default_archive_folder
        try:
            inhouse_proposals = self["inhouse_users"]["proposal"]
            for prop in inhouse_proposals:
                self.in_house_users.append(
                    (prop.get_property("code"), str(prop.get_property("number")))
                )
        except KeyError:
            pass

        email_extension = self.get_property("email_extension")
        if email_extension:
            self.email_extension = email_extension
        else:
            try:
                domain = socket.getfqdn().split(".")
                self.email_extension = ".".join((domain[-2], domain[-1]))
            except (TypeError, IndexError):
                pass

        self.set_base_data_directories(
            base_directory,
            base_process_directory,
            base_archive_directory,
            raw_folder=self.raw_data_folder_name,
            process_folder=self.processed_data_folder_name,
            archive_folder=archive_folder,
        )

        try:
            precision = int(self["file_info"].get_property("precision", ""))
        except ValueError:
            precision = self.default_precision

        PathTemplate.set_precision(precision)
        PathTemplate.set_path_template_style(self.synchrotron_name, self.template)

    def set_base_data_directories(
        self,
        base_directory,
        base_process_directory,
        base_archive_directory,
        raw_folder="RAW_DATA",
        process_folder="PROCESSED_DATA",
        archive_folder="ARCHIVE",
    ):
        self.base_directory = base_directory
        self.base_process_directory = base_process_directory
        self.base_archive_directory = base_archive_directory

        self.raw_data_folder_name = raw_folder
        self.processed_data_folder_name = process_folder

        if self.base_directory is not None:
            PathTemplate.set_data_base_path(self.base_directory)

        if self.base_archive_directory is not None:
            PathTemplate.set_archive_path(self.base_archive_directory, archive_folder)

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

        if self.is_inhouse():
            user_category = "inhouse"
            directory = os.path.join(
                self.base_directory,
                self.endstation_name,
                user_category,
                self.get_proposal(),
                start_time,
            )
        else:
            user_category = "visitor"
            directory = os.path.join(
                self.base_directory,
                user_category,
                self.get_proposal(),
                self.endstation_name,
                start_time,
            )

        return directory

    def get_path_with_proposal_as_root(self, path: str) -> str:
        """
        Strips the begining of the path so that it starts with
        the proposal folder as root

        :path: The full path
        :returns: Path stripped so that it starts with proposal
        """
        if self.is_inhouse():
            user_category = "inhouse"
            directory = os.path.join(
                self.base_directory, self.endstation_name, user_category
            )
        else:
            user_category = "visitor"
            directory = os.path.join(self.base_directory, user_category)

        return path.split(directory)[1]

    def get_base_image_directory(self):
        """
        :returns: The base path for images.
        :rtype: str
        """
        return os.path.join(self.get_base_data_directory(), self.raw_data_folder_name)

    def get_base_process_directory(self):
        """
        :returns: The base path for procesed data.
        :rtype: str
        """
        return os.path.join(
            self.get_base_data_directory(), self.processed_data_folder_name
        )

    def get_image_directory(self, sub_dir: str = "") -> str:
        """
        Returns the full path to images

        :param subdir: sub directory relative to path returned
                       by get_base_image_directory

        :returns: The full path to images.
        """
        directory = self.get_base_image_directory()

        if sub_dir:
            sub_dir = sub_dir.replace(" ", "").replace(":", "-")
            directory = os.path.join(directory, sub_dir) + os.path.sep

        return directory

    def get_process_directory(self, sub_dir: str = "") -> str:
        """
        Returns the full path to processed data,

        :param subdir: sub directory relative to path returned
                       by get_base_proccess_directory

        :returns: The full path to processed data.
        """
        directory = self.get_base_process_directory()

        if sub_dir:
            sub_dir = sub_dir.replace(" ", "").replace(":", "-")
            directory = os.path.join(directory, sub_dir) + "/"

        return directory

    def get_full_path(self, subdir: str = "", tag: str = "") -> Tuple[str, str]:
        """
        Returns the full path to both image and processed data.
        The path(s) returned will follow the convention:

          <base_direcotry>/<subdir>/run_<NUMBER>_<tag>

        Where NUMBER is a automaticaly sequential number and
        base_directory the path returned by get_base_image/process_direcotry

        :param subdir: subdirecotry
        :param tag: tag for

        :returns: Tuple with the full path to image and processed data
        """

        return self.get_image_directory(subdir), self.get_process_directory(subdir)

    def get_default_prefix(self, sample_data_node=None, generic_name=False):
        """
        Returns the default prefix, using sample data such as the
        acronym as parts in the prefix.

        :param sample_data_node: The data node to get additional
                                 information from, (which will be
                                 added to the prefix).
        :type sample_data_node: Sample


        :returns: The default prefix.
        :rtype: str
        """
        proposal = self.get_proposal()
        prefix = proposal

        if sample_data_node:
            if sample_data_node.has_lims_data():
                protein_acronym = sample_data_node.crystals[0].protein_acronym
                name = sample_data_node.name
                if protein_acronym:
                    if name:
                        prefix = "%s-%s" % (protein_acronym, name)
                    else:
                        prefix = protein_acronym
                else:
                    prefix = name or ""
        elif generic_name:
            prefix = "<acronym>-<name>"
        #
        return prefix

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

        if protein_acronym:
            subdir = "%s/%s-%s/" % (protein_acronym, protein_acronym, sample_name)
        else:
            subdir = "%s/" % sample_name

        return subdir.replace(":", "-")

    def get_archive_directory(self):
        archive_directory = os.path.join(
            self["file_info"].get_property("archive_base_directory"),
            self["file_info"].get_property("archive_folder"),
        )

        archive_directory = PathTemplate.get_archive_directory()

        return archive_directory

    def get_proposal(self):
        """
        :returns: The proposal, 'local-user' if no proposal is
                  available
        :rtype: str
        """
        proposal = "local-user"

        if self.proposal_code and self.proposal_number:
            if self.proposal_code == "ifx":
                self.proposal_code = "fx"

            proposal = "%s%s" % (self.proposal_code, self.proposal_number)

        return proposal

    def is_inhouse(self, proposal_code=None, proposal_number=None):
        """
        Determines if a given proposal is considered to be inhouse.

        :param proposal_code: Proposal code
        :type propsal_code: str

        :param proposal_number: Proposal number
        :type proposal_number: str

        :returns: True if the proposal is inhouse, otherwise False.
        :rtype: bool
        """
        if not proposal_code:
            proposal_code = self.proposal_code

        if not proposal_number:
            proposal_number = self.proposal_number

        if (proposal_code, proposal_number) in self.in_house_users:
            return True
        else:
            return False

    def get_inhouse_user(self):
        """
        :returns: The current inhouse user.
        :rtype: tuple (<proposal_code>, <proposal_number>)
        """
        return self.in_house_users[0]

    def set_session_start_date(self, start_date_str):
        """
        :param start_date_str: The session start date
        :type start_date_str: str
        """
        self.session_start_date = start_date_str

    def get_session_start_date(self):
        """
        :returns: The session start date
        :rtype: str
        """
        return self.session_start_date

    def set_user_group(self, group_name):
        """
        :param group_name: Name of user group
        :type group_name: str
        """
        self.user_group = str(group_name)

    def get_group_name(self):
        """
        :returns: Name of user group
        :rtype: str
        """
        return self.user_group
