"""
MaxLab Session hardware object.

Adapting from original Session.py to adapt the names of data directories
"""
import os
import time

from Session import Session


class MaxLabSession(Session):
    def __init__(self, name):
        Session.__init__(self, name)
        self.default_precision = "03"

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
                self.base_directory, user_category, self.get_proposal(), start_time
            )
        else:
            user_category = "visitor"
            directory = os.path.join(
                self.base_directory, user_category, self.get_proposal(), start_time
            )

        return directory

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

    def get_image_directory(self, sub_dir):
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
        directory = self.get_base_image_directory()

        if sub_dir:
            sub_dir = sub_dir.replace(" ", "").replace(":", "-")
            directory = os.path.join(directory, sub_dir) + "/"

        return directory

    def get_process_directory(self, sub_dir=None):
        """
        Returns the full path to processed data, using the name of
        each of data_nodes parents as sub directories.

        :param data_node: The data node to get additional
                          information from, (which will be added
                          to the path).
        :type data_node: TaskNode

        :returns: The full path to images.
        """
        directory = self.get_base_process_directory()

        if sub_dir:
            sub_dir = sub_dir.replace(" ", "").replace(":", "-")
            directory = os.path.join(directory, sub_dir) + "/"

        return directory

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
                prefix = (
                    sample_data_node.crystals[0].protein_acronym
                    + "-"
                    + sample_data_node.name
                )
        elif generic_name:
            prefix = "<acronym>-<name>"

        return prefix

    def get_archive_directory(self, directory):
        # Return the same directory base + /archive

        logging.getLogger().info("In get_archive_directory")
        if not directory:
            return directory

        try:
            logging.getLogger().info(
                "Getting archive directory name from %s", directory
            )
            dirname = os.path.abspath(directory)

            if dirname[-1] != os.path.sep:
                dirname += os.path.sep

            parts = dirname.split(os.path.sep)
            archive_dir_base = os.path.sep + os.path.join(*parts[1:-2])
            logging.getLogger().info("archive_dir_base:%s", archive_dir_base)
            # Set up the archiving directory if the user is logged in
            # Check if the original path is /data/data1/visitor/mx... AN 25/03/2014

            if archive_dir_base.startswith("/data/data1/visitor"):
                archive_dir_base = archive_dir_base.replace(
                    "/data/data1/visitor", "/data/ispyb/"
                )
            elif archive_dir_base.startswith("/data/data1/inhouse"):
                archive_dir_base = archive_dir_base.replace(
                    "/data/data1/inhouse", "/data/ispyb/"
                )

            archive_dir = os.path.join(archive_dir_base, "archive")
            # archive_dir = os.path.join(archive_dir_base, "archive")
            logging.getLogger().info("archive_dir:%s", archive_dir)

            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
            return archive_dir
        except BaseException:
            import traceback

            traceback.print_exc()
            return directory

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
