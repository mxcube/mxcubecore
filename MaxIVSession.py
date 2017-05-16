"""
MAXIV Session hardware object.

Adapting from original Session.py to adapt the names of data directories
"""
import os
import time
import storage

from Session import Session
import queue_model_objects_v1 as queue_model_objects


class MaxIVSession(Session):
    def __init__(self, name):
        Session.__init__(self, name)

    def run_number_intersection(self, rh_pt):
        result = False
        # Only do the intersection if there is possibilty for
        # Collision, that is directories and run_number are the same.
        if (self.run_number == rh_pt.run_number) and (self.directory == rh_pt.directory) and (self.base_prefix == rh_pt.base_prefix):
            result = True
        return result

    # Framework-2 method, inherited from HardwareObject and called
    # by the framework after the object has been initialized.
    def init(self):
        self.synchrotron_name = self.getProperty('synchrotron_name')
        self.endstation_name = self.getProperty('endstation_name').lower()
        self.suffix = self["file_info"].getProperty('file_suffix')

        self.base_directory = self["file_info"].getProperty('base_directory')
        self.base_process_directory = self["file_info"].getProperty('processed_data_base_directory')

        self.raw_data_folder_name = self["file_info"].getProperty('raw_data_folder_name')
        self.processed_data_folder_name = self["file_info"].getProperty('processed_data_folder_name')

        self.default_precision = "03"
        self.login = ''
        self.in_house_users = self.getProperty('inhouse_users').split(',')

        queue_model_objects.PathTemplate.set_path_template_style(self.synchrotron_name)
        queue_model_objects.PathTemplate.set_data_base_path(self.base_directory)
        queue_model_objects.PathTemplate.set_archive_path(self['file_info'].getProperty('archive_base_directory'),
                                                          self['file_info'].getProperty('archive_folder'))
        queue_model_objects.PathTemplate.set_path_template_style(self.getProperty('synchrotron_name'))
        queue_model_objects.PathTemplate.intersection = self.run_number_intersection

    def prepare_directories(self, proposal_info):
        self.login = proposal_info['Person']['login']

        start_time = proposal_info['Session']['startDate']

        if start_time:
            start_date = start_time.split(' ')[0].replace('-', '')
        else:
            start_date = time.strftime("%Y%m%d")

        self.set_session_start_date(start_date)

        # this checks that the beamline data path has been properly created
        # e.g. /data/visitor/biomax
        self.storage = storage.Storage(self.get_user_category(self.login), self.endstation_name)

        # this creates the path for the data and ensures proper permissions.
        # e.g. /data/visitor/biomax/<proposal>/<visit>/{raw, process}
        self.storage.create_path(self, self.proposal_code,
                                 storage.get_proposal_group(),
                                 self.get_session_start_date(),
                                 self.login)

    def is_inhouse(self, user):
        """
        Determines if a given user is considered to be inhouse.

        :param login: username
        :type login: str

        :returns: True if the user is inhouse, otherwise False.
        :rtype: bool
        """
        if user in self.in_house_users:
            return True
        else:
            return False

    def get_user_category(self):
        # missing industrial users
        if self.is_inhouse():
            user_category = 'staff'
        else:
            user_category = 'visitor'
        return user_category

    def get_base_data_directory(self):
        """
        Returns the base data directory taking the 'contextual'
        information into account, such as if the current user
        is inhouse.

        :returns: The base data path.
        :rtype: str
        """
        if self.session_start_date:
            start_time = self.session_start_date.split(' ')[0].replace('-', '')
        else:
            start_time = time.strftime("%Y%m%d")

        # /data/visitor/biomax/prop/visit/
        # /data/(user-type)/(beamline)/(proposal)/(visit)/raw

        user_category = self.get_user_category()

        # now it is a new visit everyday
        directory = os.path.join(self.base_directory,
                                 user_category,
                                 self.beamline_name,
                                 self.get_proposal(),
                                 start_time)

        return directory
