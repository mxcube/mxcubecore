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

""" """

import abc
import logging
from datetime import datetime
from typing import (
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
)

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.model.lims_session import (
    Lims,
    LimsSessionManager,
    LimsUser,
    Session,
)

__credits__ = ["MXCuBE collaboration"]

StoreEvent = Literal["CREATE", "UPDATE", "END"]


class AbstractLims(HardwareObject, abc.ABC):
    """Interface for LIMS integration"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        super().__init__(name)

        # current lims session
        self.active_session = None

        self.beamline_name = "unknown"

        self.sessions = []

        self.session_manager = LimsSessionManager()

    def is_session_already_active(self, session_id: str) -> bool:
        # If current selected session is already selected no need to do
        # anything else
        active_session = self.session_manager.active_session
        if active_session is not None:
            if active_session.session_id == session_id:
                return True
        return False

    @abc.abstractmethod
    def get_lims_name(self) -> List[Lims]:
        """
        Returns the LIMS used, name and description
        """
        raise Exception("Abstract class. Not implemented")

    def get_session_id(self) -> str:
        """
        Returns the currently active LIMS session id
        """
        return self.session_manager.active_session.session_id

    @abc.abstractmethod
    def get_user_name(self) -> str:
        """
        Returns the user name of the current user
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def get_full_user_name(self) -> str:
        """
        Returns the user name of the current user
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def login(
        self, login_id: str, password: str, create_session: bool
    ) -> List[Session]:
        """
        Login to LIMS, returns a list of Session objects for login_id

        Args:
            login_id: username
            password: password
            create_session: True if session should be created by LIMS if it
                            does not exist otherwise False

        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def is_user_login_type(self) -> bool:
        """
        Returns True if the login type is user based (not done with proposal)
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def echo(self) -> bool:
        """
        Returns True of LIMS is responding
        """
        raise Exception("Abstract class. Not implemented")

    def init(self) -> None:
        """
        Method inherited from baseclass
        """
        self.beamline_name = HWR.beamline.session.beamline_name

    @abc.abstractmethod
    def get_proposals_by_user(self, login_id: str) -> List[Dict]:
        """
        Returns a list with proposal dictionaries for login_id

        Proposal dictionary structure:
            {
                "Proposal": proposal,
                "Person": ,
                "Laboratory":,
                "Session":,
            }

        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def create_session(self, proposal_tuple: LimsSessionManager) -> LimsSessionManager:
        """
        TBD
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def get_samples(self, lims_name: str) -> List[Dict]:
        """
        Returns a list of sample dictionaries for the current user from lims_name

        Structure of sample dictionary:
        {
            "containerCode": str,
            "containerSampleChangerLocation": int,
            "crystalId": int,
            "crystalSpaceGroup": str,
            "diffractionPlan": {
                "diffractionPlanId": int
             },
            "proteinAcronym": "str,
            "sampleId": int,
            "sampleLocation": int,
            "sampleName": str
        }
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def store_robot_action(self, robot_action_dict: dict):
        """
        Stores the robot action dictionary.

        Structure of robot_action_dictionary:
        {
            "actionType":str,
            "containerLocation": str,
            "dewarLocation":str,
            "message":str,
            "sampleBarcode":str,
            "sessionId":int,
            "sampleId":int.
            "startTime":str,
            "endTime":str,
            "xtalSnapshotAfter:str",
            "xtalSnapshotBefore:str",
        }

        Args:
            robot_action_dict: robot action dictionary as defined above
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def store_beamline_setup(self, session_id: str, bl_config_dict: dict) -> int:
        """
        Stores the beamline setup dict bl_config_dict for session_id

        Args:
            session_id: The session id that the beamline_setup should be
                        associated with.

            bl_config_dict: The dictonary with beamline settings.

        Returns:
            The id of the beamline setup.
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def store_image(self, image_dict: dict) -> None:
        """
        Stores (image parameters) <image_dict>

        Args:
            image_dict: A dictonary with image pramaters.
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def store_energy_scan(self, energyscan_dict: dict) -> None:
        """
        Store energyscan data

        Args:
            energyscan_dict: Energyscan data to store.

        Returns:
            Dictonary with the energy scan id {"energyScanId": int}
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def store_xfe_spectrum(self, xfespectrum_dict: dict):
        """
        Stores a XFE spectrum.

        Args:
            xfespectrum_dict: XFE scan data to store.

        Returns:
            Dictonary with the XFE scan id {"xfeFluorescenceSpectrumId": int}
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def store_workflow(self, workflow_dict: dict) -> Tuple[int, int, int]:
        """
        Stores worklflow data workflow_dict

        Structure of workflow_dict:
        {
            "workflow_id": int,
            "workflow_type": str,
            "comments": str,
            "log_file_path": str,
            "result_file_path": str,
            "status": str,
            "title": str,
            "grid_info_id": int,
            "dx_mm": float,
            "dy_mm": float,
            "mesh_angle": float,
            "steps_x": float,
            "steps_y": float,
            "xOffset": float,
            "yOffset": float,
        }

        Args:
            workflow_dict: worklflow data on the format above

        Returns:
            Tuple of ints workflow_id, workflow_mesh_id, grid_info_id
        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def store_data_collection(
        self,
        datacollection_dict: dict,
        beamline_config_dict: Optional[Dict],
    ) -> Tuple[int, int]:
        """
        Stores a datacollection, datacollection_dict, and beamline configuration, beamline_config_dict, at the time of collection

        Structure of datacollection_dict:
        {
            "oscillation_sequence":[{}
                "start": float,
                "range": float,
                "overlap": float,
                "number_of_imaages": float,
                "start_image_number": float
                "exposure_time", float,
                "kappaStart": float,
                "phiStart": float,
            }],
            "fileinfo:{
                "direcotry: str,
                "prefix": str
                "suffix": str,
                "template: str,
                "run_number" int
            }
            "status": str,
            "collection_id: int,
            "wavelenght: float,
            "resolution":{
                "lower": float,
                "upper": float
            },
            "resolutionAtCorner": float,
            "detectorDistance": float
            "xBeam": float,
            "yBeam": float,
            "beamSizeAtSampleX": float
            "beamSizeAtSampleY": float,
            "beamShape": str,
            "slitGapHorizontal": float,
            "slitGapVertical": float,
            "synchrotronMode", float,
            "flux": float,
            "flux_end": float,
            "transmission" float,
            "undulatorGap1": float
            "undulatorGap2": float
            "undulatorGap3": float
            "xtalSnapshotFullPath1": str,
            "xtalSnapshotFullPath2": str,
            "xtalSnapshotFullPath3": str,
            "xtalSnapshotFullPath4": str,
            "centeringMethod": str,
            "actualCenteringPosition" str
            "group_id: int,
            "detector_id": int,
            "screening_sub_wedge_id": int,
            "collection_start_time": str #"%Y-%m-%d %H:%M:%S"
        }

        Structure of beamline_config_dict:
        {
            "synchrotron_name":str,
            "directory_prefix":str,
            "default_exposure_time":str,
            "minimum_exposure_time":str,
            "detector_fileext":str,
            "detector_type":str,
            "detector_manufacturer":str,
            "detector_binning_mode":str,
            "detector_model":str,
            "detector_px":int,
            "detector_py":int,
            "undulators":str,
            "focusing_optic":str,
            "monochromator_type":str,
            "beam_divergence_vertical":float,
            "beam_divergence_horizontal":float,
            "polarisation":float,
            "maximum_phi_speed":float,
            "minimum_phi_oscillation":float,
            "input_files_server":str,
        }

        Args:
            datacollection_dict: As defined above
            beamline_config_dict: As defined above

        Returns:
           Tuple data_collection_id, detector_id


        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def update_data_collection(
        self,
        datacollection_dict: dict,
    ) -> Tuple[int, int]:
        """
        Updates the collection with "collection_id", provided in datacollection_dict.

        Structure of datacollection_dict as defined in store_data_collection above.

        Args:
            datacollection_dict:

        """
        raise Exception("Abstract class. Not implemented")

    @abc.abstractmethod
    def finalize_data_collection(
        self,
        datacollection_dict: dict,
    ) -> Tuple[int, int]:
        """
        Finalizes the collection with "collection_id", provided in datacollection_dict.

        Strucure of datacollection_dict as defined in store_data_collection above.

        Args:
            datacollection_dict:
        """
        raise Exception("Abstract class. Not implemented")

    def is_scheduled_on_host_beamline(self, beamline: str) -> bool:
        """
        TBD
        """
        return beamline.strip().upper() == self.override_beamline_name.strip().upper()

    def is_scheduled_now(self, start_date: str, end_date: str) -> bool:
        """
        TBD
        """
        return self.is_time_between(start_date, end_date)

    def is_time_between(self, start_date: str, end_date: str, check_time=None):
        """
        TBD
        """
        if start_date is None or end_date is None:
            return False

        begin_time = datetime.fromisoformat(start_date).date()
        end_time = datetime.fromisoformat(end_date).date()

        # If check time is not given, default to current UTC time
        check_time = check_time or datetime.utcnow().date()
        if begin_time <= check_time <= end_time:
            return True
        else:
            return False

    def __set_sessions(self, sessions: List[Session]):
        """
        Sets the curent lims session
        :param session: lims session value
        :return:
        """
        logging.getLogger("HWR").debug(
            "%s sessions available for users %s"
            % (len(sessions), self.session_manager.users.keys())
        )
        self.session_manager.sessions = sessions
        self.emit("sessionsChanged", (sessions,))

    def get_active_session(self) -> Session:
        """
        Returns Currently active session
        """
        return self.session_manager.active_session

    def set_active_session_by_id(self, session_id: str) -> Session:
        """
        Sets session with session_id to active session

        Args:
            session_id: session id
        """
        raise Exception("Abstract class. Not implemented")

    def get_shared_sessions(self):
        # Step 1: Collect all session_ids for each user
        session_ids_by_user = {}

        # Step 2: Iterate over users and collect session ids
        for user_name, user in self.session_manager.users.items():
            session_ids_by_user[user_name] = {
                session.session_id for session in user.sessions
            }

        # Step 3: Find the intersection of session_ids (sessions shared by all users)
        if not session_ids_by_user:
            return []  # If no users, return empty list

        # Find the common session ids across all users
        common_session_ids = set.intersection(*session_ids_by_user.values())

        # Step 4: Retrieve the sessions with these common session_ids and ensure uniqueness
        shared_sessions = {}
        for user_name, user in self.session_manager.users.items():
            for session in user.sessions:
                if session.session_id in common_session_ids:
                    # Use session_id as the key to ensure uniqueness
                    shared_sessions[session.session_id] = session

        # Convert the dictionary values (which are unique) into a list
        return list(shared_sessions.values())

    def remove_user(self, user_name: str):
        if user_name in self.session_manager.users:
            del self.session_manager.users[user_name]
            logging.getLogger("HWR").debug("User %s has been removed" % user_name)
            self.__set_sessions(self.get_shared_sessions())

    def add_user_and_shared_sessions(self, user_name: str, sessions: List[Session]):
        """
        Stores the username and the shared sessions in the session manager object.
        The shared sessions represent the intersection of all sessions
        for each user currently connected.
        """
        self.session_manager.users[user_name] = LimsUser(
            user_name=user_name, sessions=sessions
        )
        logging.getLogger("HWR").debug(
            "User added to session manager, user_name=%s sessions=%s"
            % (user_name, len(sessions))
        )

        self.__set_sessions(self.get_shared_sessions())
