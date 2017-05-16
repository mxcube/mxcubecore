"""
MAXIV Session hardware object.

Adapting from original Session.py to adapt the names of data directories
"""
import os
import time
import storage

from Session import Session


class MaxIVSession(Session):
    def __init__(self, name):
        Session.__init__(self, name)

    # Framework-2 method, inherited from HardwareObject and called
    # by the framework after the object has been initialized.
    def init(self):
        self.default_precision = "03"
        self.login = ''
        self.in_house_users = self.getProperty('inhouse_users').split(',')

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
        # e.g. /data/visitor/biomax/<propsal>/<visit>/{raw, process}
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
