
import os
import re
import time
import json
from datetime import date

from Session import Session

from configparser import ConfigParser

# PATH_BEAMTIME="/gpfs/beamtime"
PATH_BEAMTIME="/gpfs/current"
PATH_COMMISSIONING="/gpfs/commissioning"
PATH_FALLBACK="/gpfs/local"

class P11Session(Session):
    default_archive_folder = "raw"

    def __init__(self,*args):
        super(P11Session,self).__init__(*args)

    def init(self):

        super(P11Session,self).init()

        self.settings_file = self.get_property("p11_settings_file")
        self.operation_mode = self.get_property("mode")
        self.beamtime_info = {}

        parser = ConfigParser()
        parser.read(self.settings_file)
        self.session_file_name = parser['general']['file_name']
        self.session_file_name = "mxcube"

        if self.session_start_date:
            self.start_time = self.session_start_date.split(" ")[0].replace("-", "")
        else:
            self.start_time = time.strftime("%Y%m%d")

        self.info_set_defaults()
        if self.is_beamtime_open():
            self.read_beamtime_info()
        elif self.is_commissioning_open():
            self.read_commissioning_info()

        self.select_base_directory(self.operation_mode)

        self.set_base_data_directories(
            self.base_directory,
            self.base_directory,
            self.base_directory,
            raw_folder=self.raw_data_folder_name,
            process_folder=self.processed_data_folder_name,
            archive_folder=self.default_archive_folder,
        )

    def info_set_defaults(self):
        self.beamtime_info['beamtimeId'] = None
        self.beamtime_info['proposalType'] = None
        self.beamtime_info['proposalId'] = None
        self.beamtime_info['rootPath'] = PATH_FALLBACK

    def is_beamtime_open(self):
        return True
        #return self.is_writable_dir( os.path.join(PATH_BEAMTIME, self.raw_data_folder_name) )

    def is_commissioning_open(self):
        return self.is_writable_dir( os.path.join(PATH_COMMISSIONING, self.raw_data_folder_name) )

    def get_current_beamtime_id(self):
        return self.beamtime_info['beamtimeId'] 

    def get_current_proposal_code(self):
        return self.beamtime_info['proposalType'] 

    def get_current_proposal_number(self):
        return self.beamtime_info['proposalId'] 

    def read_beamtime_info(self):
        for ety in os.scandir(PATH_BEAMTIME):
            if ety.is_file() and ety.name.startswith('beamtime-metadata'):
                info = self.load_info(ety.path)
                self.log.debug(f"BEAMTIME INFO from {ety.path} is " + str(info))
                if info is not None:
                    self.beamtime_info.update( self.load_info(ety.path) )
                self.beamtime_info['rootPath'] = PATH_BEAMTIME

    def read_commissioning_info(self):
        for ety in os.scandir(PATH_COMMISSIONING):
            if ety.is_file() and ety.name.startswith('commissioning-metadata'):
                self.beamtime_info.update( self.load_info(ety.path) )
                self.beamtime_info['rootPath'] = PATH_COMMISSIONING

    def load_info(self,filename):
        try:
            return json.loads(open(filename).read())
        except ValueError:
            return None

    def select_base_directory(self, mode="beamtime"):
        self.base_directory = self.beamtime_info['rootPath']

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

        return self.base_directory

        #if self.is_inhouse():
        #    user_category = "inhouse"
        #    directory = os.path.join(
        #        self.base_directory,
        #        self.endstation_name,
        #        user_category,
        #        self.get_proposal(),
        #    )
        #else:
        #    user_category = "visitor"
        #    directory = os.path.join(
        #        self.base_directory,
        #        user_category,
        #        self.get_proposal(),
        #        self.endstation_name,
        #    )
        #
        #return directory


    def get_base_image_directory(self):
        """
        :returns: The base path for images.
        :rtype: str
        """
        return os.path.join(self.get_base_data_directory(), \
                            self.raw_data_folder_name )
                            #self.session_file_name, \
                            #self.start_time)


    def get_base_process_directory(self):
        """
        :returns: The base path for procesed data.
        :rtype: str
        """
        return os.path.join(self.get_base_data_directory(), \
                            self.processed_data_folder_name )
                            # self.session_file_name, \
                            # self.start_time)

    def get_archive_directory(self):
        """
        :returns: The base path for procesed data.
        :rtype: str
        """
        return os.path.join(self.get_base_data_directory(), \
                            self.default_archive_folder )
                            # self.session_file_name, \
                            # self.start_time)

    def path_to_ispyb(self, path):
        ispyb_template = self["file_info"].get_property("ispyb_directory_template")
        bid = self.beamtime_info['beamtimeId'] 
        year = date.today().year
        ispyb_path = ispyb_template.format(beamtime_id=bid,year=year)
        return path

    def is_writable_dir(self, folder):
        return os.path.isdir(folder) and os.access(folder, os.F_OK | os.W_OK )

