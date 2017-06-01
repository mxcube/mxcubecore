"""
MAXIV Session hardware object.

Adapting from original Session.py to adapt the names of data directories
"""
import os
import sys
import time
import storage
import logging

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
        Session.init(self)
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
        msg = "[SDM]MAX IV Session preparing directories for proposal: "
        msg += "%s, user: %s" % (proposal_info['Proposal']['number'],
                                 proposal_info['person']['login'])
        logging.getLogger("HWR").info(msg)

        self.login = proposal_info['person']['login']
        start_time = proposal_info['session']['session']['startDate']
        if start_time:
            start_date = start_time.split(' ')[0].replace('-', '')
        else:
            start_date = time.strftime("%Y%m%d")
        self.set_session_start_date(start_date)
        try:
            # this checks that the beamline data path has been properly created
            # e.g. /data/visitor/biomax
            self.storage = storage.Storage(self.get_user_category(self.login), self.endstation_name)

            # this creates the path for the data and ensures proper permissions.
            # e.g. /data/visitor/biomax/<propsal>/<visit>/{raw, process}
            self.storage.create_path(self.proposal_number,
                                     self.storage.get_proposal_group(self.proposal_number),
                                     self.get_session_start_date(),
                                     self.login)
        except:
            logging.getLogger("HWR").error("[SDM] Cannot create directory, %s" % sys.exc_info()[1])

        logging.getLogger("HWR").info("[SDM] Directories created.")

    def is_inhouse(self, user=None, proposal_number=None):
>>>>>>> b90c265... sdm related fixes
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

    def get_user_category(self, username):
        # missing industrial users
        if self.is_inhouse(user=username):
            user_category = 'staff'
        else:
            user_category = 'visitors'
        return user_category

    def get_proposal(self):
        """
        :returns: The proposal, 'local-user' if no proposal is
                  available
        :rtype: str
        """
        proposal = 'local-user'

        if self.proposal_code and self.proposal_number:
            proposal = self.proposal_number

        return proposal

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
        user_category = self.get_user_category(self.login)

        # now it is a new visit everyday
        directory = os.path.join(self.base_directory,
                                 user_category,
                                 self.beamline_name,
                                 self.get_proposal(),
                                 start_time)

        return directory
