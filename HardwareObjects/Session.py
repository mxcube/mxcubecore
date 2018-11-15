"""
Session hardware object.

Contains information regarding the current session and methods to
access and manipulate this information.
"""
import os
import time
import socket
import logging
import xml.etree.ElementTree as ET

from HardwareRepository.HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import HardwareObject
import queue_model_objects_v1 as queue_model_objects

# Configuration file used to override base_directory paths.
# Will be ignored if not found
parameter_override_file = 'session_parameter_override.xml'

class Session(HardwareObject):

    default_raw_data_folder = "RAW_DATA"

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
        self.user_group = ''
        self.email_extension = None
        self.template = None

        self.default_precision = '05'
        self.suffix = None

        self.base_directory = None
        self.base_process_directory = None
        self.base_archive_directory = None

        self.raw_data_folder_name = 'RAW_DATA'
        self.processed_data_folder_name = 'PROCESS_DATA'
        self.archive_folder_name = 'ARCHIVE'

    # Framework-2 method, inherited from HardwareObject and called
    # by the framework after the object has been initialized.
    def init(self):

        self.synchrotron_name = self.getProperty('synchrotron_name')
        self.beamline_name = self.getProperty('beamline_name')
        self.endstation_name = self.getProperty('endstation_name').lower()

        self.suffix = self["file_info"].getProperty('file_suffix')
        self.template = self["file_info"].getProperty('file_template')

        # Override directory names, if parameter_override_file exists.
        # Intended to allow resetting directories in mock mode,
        # while keeping the session/xml used for the mocked beamline.
        override_file = HardwareRepository().findInRepository(
            parameter_override_file
        )
        logging.getLogger('HWR').info('Reading override directory names from %s' % override_file)
        if override_file:
            parameters =  ET.parse(override_file).getroot()
            for elem in parameters:
                tag = elem.tag
                if tag in ('base_directory', 'processed_data_base_directory',
                           'archive_base_directory'):
                    val = elem.text.strip()
                    if val is not None:
                        self["file_info"].setProperty(tag, val)

        base_directory = self["file_info"].\
                              getProperty('base_directory')

        base_process_directory = self["file_info"].\
            getProperty('processed_data_base_directory')

        base_archive_directory = self['file_info'].\
            getProperty('archive_base_directory')

        raw_folder = self["file_info"].\
            getProperty('raw_data_folder_name')

        if raw_folder is None or (not raw_folder.strip()):
            raw_folder = Session.default_raw_data_folder 

        process_folder = self["file_info"].\
            getProperty('processed_data_folder_name')

        archive_folder = self['file_info'].\
            getProperty('archive_folder')

        try:
            inhouse_proposals = self["inhouse_users"]["proposal"]
            for prop in inhouse_proposals:
                self.in_house_users.append((prop.getProperty('code'),
                                            str(prop.getProperty('number'))))
        except IndexError:
            pass

        email_extension = self.getProperty('email_extension')
        if email_extension:
            self.email_extension = email_extension
        else:
            try:
                domain = socket.getfqdn().split('.')
                self.email_extension = '.'.join((domain[-2], domain[-1]))
            except (TypeError, IndexError):
                pass

        archive_base_directory = self['file_info'].getProperty('archive_base_directory')
        if archive_base_directory:
            queue_model_objects.PathTemplate.set_archive_path(archive_base_directory,
                                                              self['file_info'].getProperty('archive_folder'))

        queue_model_objects.PathTemplate.set_path_template_style(self.synchrotron_name)
        queue_model_objects.PathTemplate.set_data_base_path(self.base_directory)

        self.set_base_data_directories( base_directory, 
                                        base_process_directory, 
                                        base_archive_directory, 
                                        raw_folder=raw_folder, 
                                        process_folder=process_folder, 
                                        archive_folder=archive_folder)

        precision = self.default_precision
                
        try:
            precision = eval(self["file_info"].getProperty('precision', self.default_precision))
        except:
            pass

        queue_model_objects.PathTemplate.set_precision(precision)

    def set_base_data_directories(self, base_directory, base_process_directory, base_archive_directory,
              raw_folder="RAW_DATA", process_folder="PROCESS_DATA", archive_folder="ARCHIVE"):

        self.base_directory = base_directory
        self.base_process_directory = base_process_directory
        self.base_archive_directory = base_archive_directory

        self.raw_data_folder_name = raw_folder
        self.process_data_folder_name = process_folder
        self.archive_data_folder_name = archive_folder
    
        if self.base_directory is not None:
            queue_model_objects.PathTemplate.set_data_base_path(self.base_directory)

        if self.base_archive_directory is not None:
            queue_model_objects.PathTemplate.set_archive_path(
               self.base_archive_directory, self.archive_folder_name)

    def get_base_data_directory(self):
        """
        Returns the base data directory taking the 'contextual'
        information into account, such as if the current user
        is inhouse.

        :returns: The base data path.
        :rtype: str
        """
        user_category = ''
        directory = ''

        if self.session_start_date:
            start_time = self.session_start_date.split(' ')[0].replace('-', '')
        else:
            start_time = time.strftime("%Y%m%d")

        if self.synchrotron_name == "EMBL-HH":
            if os.getenv("SUDO_USER"):
                user = os.getenv("SUDO_USER")
            else:
                user = os.getenv("USER")
            directory = os.path.join(self.base_directory, str(os.getuid()) + '_'\
                                     + str(os.getgid()), user, start_time)
        else: 
            if self.is_inhouse():
                user_category = 'inhouse'
                directory = os.path.join(self.base_directory, self.endstation_name,
                                         user_category, self.get_proposal(),
                                         start_time)
            else:
                user_category = 'visitor'
                directory = os.path.join(self.base_directory, user_category,
                                         self.get_proposal(), self.endstation_name,
                                         start_time)

        return directory

    def get_base_image_directory(self):
        """
        :returns: The base path for images.
        :rtype: str
        """
        return os.path.join(self.get_base_data_directory(),
                            self.raw_data_folder_name)

    def get_base_process_directory(self):
        """
        :returns: The base path for procesed data.
        :rtype: str
        """
        return os.path.join(self.get_base_data_directory(),
                            self.processed_data_folder_name)

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
        directory = self.get_base_image_directory()

        if sub_dir:
            sub_dir = sub_dir.replace(' ', '').replace(':', '-')
            directory = os.path.join(directory, sub_dir) + os.path.sep
            
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
            sub_dir = sub_dir.replace(' ', '').replace(':', '-')
            directory = os.path.join(directory, sub_dir) + '/'

        return directory

    def get_default_prefix(self, sample_data_node = None, generic_name = False):
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
                prefix = sample_data_node.crystals[0].protein_acronym + \
                         '-' + sample_data_node.name
        elif generic_name:
            prefix = '<acronym>-<name>'

        return prefix

    def get_archive_directory(self):
        archive_directory = os.path.join(self['file_info'].getProperty('archive_base_directory'),
                                         self['file_info'].getProperty('archive_folder'))

        if self.synchrotron_name == "EMBL-HH":
            folders = self.get_base_data_directory().split('/')
            archive_directory = os.path.join(archive_directory,
                                             *folders[4:])
        else:
            archive_directory = queue_model_objects.PathTemplate.get_archive_directory()

        return archive_directory
        

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

            proposal = "%s%s" % (self.proposal_code,
                                 self.proposal_number)

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