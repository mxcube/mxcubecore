"""
Session hardware object.

Contains information regarding the current session and methods to access
and manipulate that information.
"""
import os
import time

from HardwareRepository.BaseHardwareObjects import HardwareObject
from queue_entry import QueueEntryContainer

__author__ = "Marcus Oskarsson"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["My great coleagues", "The MxCuBE colaboration"]

__version__ = "0.1"
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Beta"


class Session(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.session_id = None
        self.proposal_code = None
        self.proposal_number = None
        self.proposal_id = None
        self.in_house_users = []
        self._is_inhouse = None
        
        self.endstation_name = None

        self.default_precision = '04'
        self.suffix = None
        self.base_directory = None
        self.base_process_directory = None
        self.raw_data_folder_name = None
        self.processed_data_folder_name = None

      
    # Framework-2 method, inherited from HardwareObject and called
    # by the framework after the object has been initialized.
    def init(self):
        self.bl_config_hwobj = self.getObjectByRole("bl_config")
        self.endstation_name = self.bl_config_hwobj.getProperty('endstation_name')  
        self.suffix = self.bl_config_hwobj["file_info"].getProperty('file_suffix')
        self.base_directory = self.bl_config_hwobj["file_info"].getProperty('base_directory')
        
        self.base_process_directory = self.bl_config_hwobj["file_info"].\
                                      getProperty('processed_data_base_directory')

        self.raw_data_folder_name = self.bl_config_hwobj["file_info"].\
                                    getProperty('raw_data_folder_name')

        self.processed_data_folder_name = self.bl_config_hwobj["file_info"].\
                                          getProperty('processed_data_folder_name')

        inhouse_proposals = self.bl_config_hwobj["inhouse_users"]["proposal"]

        for prop in inhouse_proposals:
            self.in_house_users.append((prop.getProperty('code'),
                                        str(prop.getProperty('number'))))




    def get_base_data_directory(self):
        """
        Returns the base data directory taking the 'contextual' information
        into account, such as if the current user is inhouse.


        :returns: The base data path.
        :rtype: str
        """
        user_category = ''
        directory = ''

        #import sys; sys.stdout = sys.__stdout__;import pdb; pdb.set_trace()
        
        if self.is_inhouse():
            user_category = 'inhouse'
            directory = os.path.join(self.base_directory,
                                     self.endstation_name,
                                     user_category, self.get_proposal(),
                                     time.strftime("%Y%m%d"))
        else:
            user_category = 'visitor' 
            directory = os.path.join(self.base_directory,
                                     user_category, self.get_proposal(),
                                     self.endstation_name,
                                     time.strftime("%Y%m%d"))

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


    def get_image_directory(self, data_node):
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

        sub_dir = data_node.get_full_name()[0:-1]
        sub_dir.reverse()
        sub_dir = os.path.join(*sub_dir)
        sub_dir = sub_dir.replace(' ','').replace(':','-')
        directory = self.get_base_image_directory()
        
        if sub_dir:
            directory = os.path.join(directory, sub_dir)

        return directory


    def get_process_directory(self, data_node, sub_dir = None):
        """
        Returns the full path to processed data, using the name of each of
        data_nodes parents as sub directories.

        :param data_node: The data node to get additional
                          information from, (which will be added
                          to the path). 
        :type data_node: TaskNode

        :returns: The full path to images.
        """

        sub_dir = data_node.get_full_name()[0:-1]
        sub_dir.reverse()
        sub_dir = os.path.join(*sub_dir)
        sub_dir = sub_dir.replace(' ','').replace(':','-')
        directory = self.get_base_process_directory()
       
        if sub_dir:
            directory = os.path.join(directory, sub_dir)

        return directory


    def get_default_prefix(self, sample_data_node):
        """
        Returns the default prefix, using sample data such as the acronym
        as parts in the prefix.

        :param sample_data_node: The data node to get additional
                                 information from, (which will be added
                                 to the prefix).
        :type sample_data_node: Sample


        :returns: The default prefix.
        :rtype: str
        """
        proposal = self.get_proposal()

        if not proposal:
            proposal = "local-user"
        
        if sample_data_node.has_lims_data():
            prefix = sample_data_node.crystals[0].protein_acronym + \
                '-' + sample_data_node.name     
        else:
            prefix = proposal
            
        return prefix


    def get_proposal(self):
        """
        :returns: The proposal, 'local-user' if no proposal is available
        :rtype: str
        """
        proposal = 'local-user'
        
        if self.proposal_code and self.proposal_number:
            if self.proposal_code == 'ifx':
                self.proposal_code = 'fx'

            proposal = "%s%s" % (self.proposal_code, self.proposal_number)

        return proposal


    def is_inhouse(self, proposal_code = None, proposal_number = None):
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
        return self.in_house_users[0]


    def set_inhouse(self, state):
        if state:
            self.is_inhouse = True
        else:
            self.is_inhouse = False


    # UNUSED ?
    # def get_image_paths(self, acquisition):
    #     paths = []
                            
    #     for i in range(acquisition.first_image, 
    #                    acquisition.num_images + acquisition.first_image):
            
    #         paths.append(self.build_image_path(parameters) % i)

    #     return paths


#     def add_path_template(self, path_template):
#         if path_template.prefix in self._path_template_dict:
#             self._path_template_dict[path_template.prefix].\
#                 append(path_template)
#         else:
#             self._path_template_dict[path_template.prefix] = []
#             self._path_template_dict[path_template.prefix].\
#                 append(path_template)


#     def remove_path_template(self, path_template):
#         if path_template.prefix in self._path_template_dict:
#             pt_list = self._path_template_dict[path_template.prefix]
#             del pt_list[pt_list.index(path_template)]
            

#     def get_free_run_number(self, prefix, directory):
#         path_template_list = self._path_template_dict.get(prefix,
#                                                            [])
#         largest = 0
#         for path_template in path_template_list:
#             if path_template.directory == directory:
#                 if path_template.run_number > largest:
#                     largest = path_template.run_number

#         return largest + 1


#     def _sample_name_path(self, sample_data_node):
#         path = sample_data_node.loc_str.replace(':', '-')

#         if sample_data_node.has_lims_data():
#             path = os.path.join(sample_data_node.crystals[0].\
#                                 protein_acronym, sample_data_node.name)
        
#         return path
