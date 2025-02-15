# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """Copyright The MXCuBE Collaboration"""
__license__ = "LGPLv3+"

import glob
import json
import os
import time
from configparser import ConfigParser
from datetime import date
from select import EPOLL_CLOEXEC

import yaml

from mxcubecore.HardwareObjects.Session import Session

PATH_BEAMTIME = "/gpfs/current"
PATH_COMMISSIONING = "/gpfs/commissioning"
PATH_FALLBACK = "/gpfs/local"


class P11Session(Session):
    default_archive_folder = "raw"

    def init(self):
        super().init()

        self.settings_file = self.get_property("p11_settings_file")
        self.operation_mode = self.get_property("mode")
        self.beamtime_info = {}

        parser = ConfigParser()
        parser.read(self.settings_file)
        self.session_file_name = parser["general"]["file_name"]
        self.session_file_name = "mxcube"

        if self.session_start_date:
            self.start_time = self.session_start_date.split(" ")[0].replace("-", "")
        else:
            self.start_time = time.strftime("%Y%m%d")

        self.info_set_defaults()

        # Try to locate the metadata file and process it.
        self.beamtime_metadata_file = self.locate_metadata_file()

        if self.beamtime_metadata_file:
            (
                self.beamline,
                self.beamtime,
                self.remote_data_dir,
                self.user_name,
                self.user_sshkey,
                self.slurm_reservation,
                self.slurm_partition,
                self.slurm_node,
            ) = self.parse_metadata_file(self.beamtime_metadata_file)
        else:
            # Fall back to local paths if no metadata is found
            self.log.debug("Falling back to local directory for saving data.")
            self.select_base_directory(
                "local"
            )  # Use local paths instead of beamtime data

        if self.is_beamtime_open():
            self.read_beamtime_info()
        elif self.is_commissioning_open():
            self.read_commissioning_info()

        self.set_base_data_directories(
            self.base_directory,
            self.base_directory,
            self.base_directory,
            raw_folder=self.raw_data_folder_name,
            process_folder=self.processed_data_folder_name,
            archive_folder=self.default_archive_folder,
        )

    def info_set_defaults(self):
        self.beamtime_info["beamtimeId"] = None
        self.beamtime_info["proposalType"] = None
        self.beamtime_info["proposalId"] = None
        self.beamtime_info["rootPath"] = PATH_FALLBACK

    def is_beamtime_open(self):
        self.log.debug("=========== CHECKING IF BEAMTIME ID IS OPEN... ============")
        if self.is_writable_dir(os.path.join(PATH_BEAMTIME, self.raw_data_folder_name)):
            self.log.debug(
                "=========== BEAMTIME IS OPEN (/gpfs/current exists) ============"
            )
        else:
            logging.getLogger("GUI").error(
                "No beamtime ID is open (check /gpfs/current)"
            )

        return self.is_writable_dir(
            os.path.join(PATH_BEAMTIME, self.raw_data_folder_name)
        )

    def is_commissioning_open(self):
        return self.is_writable_dir(
            os.path.join(PATH_COMMISSIONING, self.raw_data_folder_name)
        )

    def is_writable_dir(self, folder):
        return os.path.isdir(folder) and os.access(folder, os.F_OK | os.W_OK)

    def get_current_beamtime_id(self):
        if self.is_beamtime_open():
            info = self.get_beamtime_info()
            return info["beamtimeId"]

    def get_current_proposal_code(self):
        if self.is_beamtime_open():
            info = self.get_beamtime_info()
            return info["proposalType"]

    def get_current_proposal_number(self):
        if self.is_beamtime_open():
            info = self.get_beamtime_info()
            return info["proposalId"]

    def get_beamtime_info(self):
        return self.beamtime_info

    def read_beamtime_info(self):
        self.log.debug("=========== READING BEAMTIME INFO ============")
        if os.path.exists(PATH_BEAMTIME):
            if os.scandir(PATH_BEAMTIME):
                for ety in os.scandir(PATH_BEAMTIME):
                    if ety.is_file() and ety.name.startswith("beamtime-metadata"):
                        info = self.read_load_info(ety.path)
                        self.log.debug(f"BEAMTIME INFO from {ety.path} is " + str(info))
                        if info is not None:
                            self.beamtime_info.update(self.read_load_info(ety.path))
                        self.beamtime_info["rootPath"] = PATH_BEAMTIME
        else:
            self.log.debug(f"No beamtime ID is open, using local path {PATH_FALLBACK}.")
            self.beamtime_info["rootPath"] = PATH_FALLBACK

    def read_commissioning_info(self):
        for ety in os.scandir(PATH_COMMISSIONING):
            if ety.is_file() and ety.name.startswith("commissioning-metadata"):
                fname = ety.path
                break
            else:
                return None

        return self.read_load_info(fname)

    def read_load_info(self, filename):
        try:
            with open(filename, encoding="utf-8") as file:
                json_str = file.read()
                return json.loads(json_str)
        except (ValueError, FileNotFoundError):
            return None

    def select_base_directory(self, mode="beamtime"):
        self.base_directory = self.beamtime_info["rootPath"]

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

    def get_archive_directory(self):
        """
        :returns: The base path for procesed data.
        :rtype: str
        """
        return os.path.join(self.get_base_data_directory(), self.default_archive_folder)

    def path_to_ispyb(self, path):
        ispyb_template = self["file_info"].get_property("ispyb_directory_template")
        bid = self.beamtime_info["beamtimeId"]
        year = date.today().year
        ispyb_path = ispyb_template.format(beamtime_id=bid, year=year)
        return path

    def is_writable_dir(self, folder):
        return os.path.isdir(folder) and os.access(folder, os.F_OK | os.W_OK)

    def locate_metadata_file(self, root_dir="/gpfs"):
        try:
            beamtime_dirs = [
                path
                for path in [
                    os.path.join(root_dir, entry) for entry in os.listdir(root_dir)
                ]
                if os.path.isdir(path) and not path.endswith("local")
            ]
        except OSError as e:
            print(e)
            self.log.debug("Root directory does not exist: " + str(root_dir))
            return None  # Fall back if the root directory doesn't exist.

        self.log.debug(f"Scanning directories: {beamtime_dirs}")

        metadata_files = []
        for curr_dir in beamtime_dirs + [root_dir]:
            curr_dir_metadata_files = glob.glob("{0}/*metadata*.json".format(curr_dir))
            metadata_files.extend(curr_dir_metadata_files)
            self.log.debug(
                f"Found metadata files in {curr_dir}: {curr_dir_metadata_files}"
            )

        if len(metadata_files) != 1:
            self.log.debug(
                "Unique metadata JSON file not found. Falling back to /gpfs/local."
            )
            return None  # Return None to indicate no metadata file was found.

        return metadata_files[0]

    def parse_metadata_file(self, metadatafile_path):
        beamline = ""
        beamtime = ""
        coredatadir = ""
        temp_user_name = ""
        temp_user_sshkeyfile = ""
        slurm_reservation = ""
        slurm_partition = ""
        reserved_nodes = []
        with open(metadatafile_path, "r") as mdfile:
            try:
                md = yaml.safe_load(mdfile)
                if "beamline" in md:
                    beamline = str(md["beamline"])
                if "beamtimeId" in md:
                    beamtime = str(md["beamtimeId"])
                elif "id" in md:
                    beamtime = str(md["id"])
                if "corePath" in md:
                    coredatadir = str(md["corePath"])
                if "onlineAnalysis" in md:
                    temp_user_name = str(md["onlineAnalysis"]["userAccount"])
                    temp_user_sshkeyfile = str(
                        md["onlineAnalysis"]["sshPrivateKeyPath"]
                    )
                    slurm_reservation = str(md["onlineAnalysis"]["slurmReservation"])
                    slurm_partition = str(md["onlineAnalysis"]["slurmPartition"])
                    reserved_nodes = md["onlineAnalysis"]["reservedNodes"]
            except:
                raise RuntimeError(
                    "JSON parsing of metadata file failed", metadatafile_path
                )

        if not beamline:
            raise RuntimeError("Beamline ID not found", metadatafile_path)
        if not beamtime:
            raise RuntimeError("Beamtime ID not found", metadatafile_path)
        if not coredatadir:
            raise RuntimeError(
                "Data location on remote filesystem unknown", metadatafile_path
            )
        if not temp_user_name:
            raise RuntimeError(
                "Temporary account for online analysis unknown ", metadatafile_path
            )
        if not temp_user_sshkeyfile:
            raise RuntimeError(
                "SSH key for online analysis account not found", metadatafile_path
            )
        if not slurm_reservation:
            raise RuntimeError(
                "Slurm reservation for online analysis not found", metadatafile_path
            )
        if not slurm_partition:
            raise RuntimeError(
                "Slurm partition for online analysis not found", metadatafile_path
            )
        if not reserved_nodes:
            raise RuntimeError(
                "Reserved node(s) for online analysis not found", metadatafile_path
            )
        else:
            temp_user_sshkeyfile = os.path.join(
                os.path.dirname(metadatafile_path), temp_user_sshkeyfile
            )
            slurm_node = str(reserved_nodes[0])

        return (
            beamline,
            beamtime,
            coredatadir,
            temp_user_name,
            temp_user_sshkeyfile,
            slurm_reservation,
            slurm_partition,
            slurm_node,
        )

    def get_beamtime_metadata(self, root_dir="/gpfs"):
        try:
            metadata_file = self.locate_metadata_file(root_dir)
            return self.parse_metadata_file(metadata_file)
        except:
            self.log.debug(
                "Metadata file can not be parsed. Check if beamtime is open."
            )
            return None

    def get_ssh_command(self):
        ssh_command = "/usr/bin/ssh"
        ssh_opts_general = "-o BatchMode=yes -o CheckHostIP=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o GSSAPIDelegateCredentials=no -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o PreferredAuthentications=publickey -o ConnectTimeout=10"
        ssh_opts_user = "-l {0}".format(self.user_name)
        ssh_opts_key = "-i {0}".format(self.user_sshkey)
        ssh_opts_host = self.slurm_node
        ssh_command += " {0} {1} {2} {3}".format(
            ssh_opts_general, ssh_opts_key, ssh_opts_user, ssh_opts_host
        )
        return ssh_command

    def get_sbatch_command(
        self, jobname_prefix="onlineanalysis", logfile_path="/dev/null"
    ):
        sbatch_command = "/usr/bin/sbatch"
        sbatch_opts_jobname = "{0}_{1.beamline}_{1.beamtime}".format(
            jobname_prefix, self
        )

        sbatch_opts_logfile = logfile_path

        sbatch_opts = "--partition={0.slurm_partition} --reservation={0.slurm_reservation} --job-name={1} --output={2}".format(
            self, sbatch_opts_jobname, sbatch_opts_logfile
        )

        sbatch_command += " {0}".format(sbatch_opts)
        return sbatch_command
