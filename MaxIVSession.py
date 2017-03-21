"""
MAXIV Session hardware object.

Adapting from original Session.py to adapt the names of data directories
"""
import os
import time

from Session import Session


class MaxIVSession(Session):
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
        if self.session_start_date:
            start_time = self.session_start_date.split(' ')[0].replace('-', '')
        else:
            start_time = time.strftime("%Y%m%d")

        # /data/visitor/biomax/prop/visit/
        # /data/(user-type)/(beamline)/(proposal)/(visit)/raw

        if self.is_inhouse():
            user_category = 'staff'
        else:
            user_category = 'visitor'
        # missing industrial users and visit info
        # now it is a new visit everyday
        directory = os.path.join(self.base_directory,
                                 user_category,
                                 self.beamline_name,
                                 self.get_proposal(),
                                 start_time)

        return directory
