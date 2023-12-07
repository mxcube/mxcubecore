"""
MAXIV Session hardware object.

Adapting from original Session.py to adapt the names of data directories
"""
import os
import time
import socket
import logging

try:
    from sdm import storage, SDM
except ImportError:
    raise Exception('Cannot import SDM library.')

from Session import Session
from mxcubecore.model import queue_model_objects


class MaxIVSession(Session):
    def __init__(self, name):
        Session.__init__(self, name)

    # Framework-2 method, inherited from HardwareObject and called
    # by the framework after the object has been initialized.
    def init(self):
        Session.init(self)
        self.default_precision = "04"
        self.login = ''
        self.is_commissioning = False
        self.remote_address = self.get_property('remote_address')
        self.base_process_directory = self["file_info"].\
            get_property('processed_data_base_directory')

        self.raw_data_folder_name = self["file_info"].\
            get_property('raw_data_folder_name')

        self.processed_data_folder_name = self["file_info"].\
            get_property('processed_data_folder_name')

        try:
            self.in_house_users = self.getProperty("inhouse_users").split(',')
        except Exception:
            self.in_house_users = []

        try:
            domain = socket.getfqdn().split('.')
            self.email_extension = '.'.join((domain[-2], domain[-1]))
        except (TypeError, IndexError):
            pass

        if self.base_archive_directory:
            # we initialize with an empty archive_folder, to be set once proposal is selected
            queue_model_objects.PathTemplate.set_archive_path(self.base_archive_directory, '')

        queue_model_objects.PathTemplate.set_path_template_style(self.synchrotron_name)
        queue_model_objects.PathTemplate.set_data_base_path(self.base_directory)

        self.commissioning_fake_proposal = {'Laboratory': {'address': None,
                                                           'city': 'Lund',
                                                           'laboratoryId': 312171,
                                                           'name': 'Lund University'},
                                            'Person': {'familyName': 'commissioning',
                                                       'givenName': '',
                                                       'laboratoryId': 312171,
                                                       'login': '',
                                                       'personId': 0},
                                            'Proposal': {'code': 'MX',
                                                         'number': time.strftime("%Y"),
                                                         'proposalId': '0',
                                                         'timeStamp': time.strftime("%Y%m%d"),
                                                         'title': 'Commissioning Proposal',
                                                         'type': 'MX'},
                                            'Session': [{'is_inhouse': True,
                                                         'beamlineName': 'BioMAX',
                                                         'comments': 'Fake session for commissioning',
                                                         'endDate': '2027-12-31 23:59:59',
                                                         'nbShifts': 100,
                                                         'proposalId': '0',
                                                         'scheduled': 0,
                                                         'sessionId': 0,
                                                         'startDate': '2016-01-01 00:00:00'}
                                                        ]
                                            }

    def set_in_commissioning(self, proposal_info):
        self.proposal_code = proposal_info['Proposal']['code']
        self.proposal_number = proposal_info['Proposal']['number']
        self.is_commissioning = True

    def get_proposal(self):
        """
        :returns: The proposal, 'local-user' if no proposal is
                  available
        :rtype: str
        """
        proposal = 'local-user'

        if self.proposal_code and self.proposal_number:
            if self.proposal_code == 'ifx':
                self.proposal_code = 'fx'

            proposal = str(self.proposal_number)

        return proposal

    def get_base_data_directory(self):
        """
        Returns the base data directory taking the 'contextual'
        information into account, such as if the current user
        is inhouse.

        :returns: The base data path.
        :rtype: str
        """
        # /data/(user-type)/(beamline)/(proposal)/(visit)/raw
        if self.session_start_date:
            start_time = self.session_start_date.split(' ')[0].replace('-', '')
        else:
            start_time = time.strftime("%Y%m%d")
        _proposal = self.get_proposal()

        if not self.is_commissioning:
            if self.is_proprietary(_proposal):
                directory = os.path.join(self.base_directory,
                                         'proprietary',
                                         self.beamline_name.lower(),
                                         _proposal,
                                         start_time)
            else:
                directory = os.path.join(self.base_directory,
                                         'visitors',
                                         self.beamline_name.lower(),
                                         _proposal,
                                         start_time)

        else:
            # /data/staff/biomax/commissioning/date
            directory = os.path.join(self.base_directory,
                                     'staff',
                                      self.beamline_name.lower(),
                                     'commissioning',
                                      time.strftime("%Y%m%d"))

        logging.getLogger("HWR").info("[MAX IV Session] Data directory for proposal %s: %s" % (self.get_proposal(), directory))

        return directory

    def prepare_directories(self, proposal_info):
        logging.getLogger("HWR").info("[MAX IV Session] Preparing Data directory for proposal %s" % proposal_info)
        self.login = proposal_info['Person']['login']
        start_time = proposal_info.get('Session')[0].get('startDate')

        if start_time:
            start_date = start_time.split(' ')[0].replace('-', '')
        else:
            start_date = time.strftime("%Y%m%d")

        self.set_session_start_date(start_date)

        # this checks that the beamline data path has been properly created
        # e.g. /data/visitors/biomax
        _proposal = self.get_proposal()

        logging.getLogger("HWR").info("[MAX IV Session] Preparing Data directory for proposal %s" % _proposal)
        if self.is_commissioning:
            category = 'staff'
        else:
            if self.is_proprietary(_proposal):
                category = 'proprietary'
            else:
                category = 'visitors'

        try:
            self.storage = storage.Storage(category, self.endstation_name)
        except Exception as ex:
            print(ex)
            # this creates the path for the data and ensures proper permissions.
            # e.g. /data/visitors/biomax/<proposal>/<visit>/{raw, process}
        if self.is_commissioning:
            group = self.beamline_name.lower()
        else:
            group = self.storage.get_proposal_group(self.proposal_number)
        try:
            _raw_path = self.storage.create_path(self.proposal_number,
                                                 group,
                                                 self.get_session_start_date())

            logging.getLogger("HWR").info("[MAX IV Session] SDM Data directory created: %s" % _raw_path)
        except Exception as ex:
            msg = "[MAX IV Session] SDM Data directory creation failed. %s" % ex
            logging.getLogger("HWR").warning(msg)
            logging.getLogger("HWR").info("[MAX IV Session] SDM Data directory trying to create again after failure")
            time.sleep(0.1)
            try:
                _raw_path = self.storage.create_path(self.proposal_number,
                                                     group,
                                                     self.get_session_start_date())

                logging.getLogger("HWR").info("[MAX IV Session] SDM Data directory created: %s" % _raw_path)
            except Exception as ex:
                msg = "[MAX IV Session] SDM Data directory creation failed. %s" % ex
                logging.getLogger("HWR").error(msg)
                raise Exception(msg)

        if self.base_archive_directory:
            archive_folder = "{}/{}".format(category, self.beamline_name.lower())
            queue_model_objects.PathTemplate.set_archive_path(self.base_archive_directory, archive_folder)
            _archive_path = os.path.join(self.base_archive_directory, archive_folder)
            logging.getLogger("HWR").info("[MAX IV Session] Archive directory configured: %s" % _archive_path)

    def is_proprietary(self, proposal_number=None):
        """
        Determines if a given proposal is considered to be proprietary.

        :param proposal_number: Proposal number
        :type proposal_number: str

        :returns: True if the proposal is proprietary, otherwise False.
        :rtype: bool
        """
        return self.proposal_code == "IN"

    def clear_session(self):
        self.session_id = None
        self.proposal_code = None
        self.proposal_number = None

        self.login = ''
        self.is_commissioning = False
