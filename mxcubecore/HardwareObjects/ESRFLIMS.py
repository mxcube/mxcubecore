import logging
from typing import List

from mxcubecore.HardwareObjects.abstract.AbstractLims import AbstractLims
from mxcubecore.model.lims_session import (
    Lims,
    LimsSessionManager,
    Session,
)

logger = logging.getLogger("HWR")


class ESRFLIMS(AbstractLims):
    """
    ESRF client (ICAT+/DRAC).
    """

    def __init__(self, name):
        super().__init__(name)

    def init(self):
        self.drac = self.get_object_by_role("drac")

        self.is_local_host = False
        self.active_lims = self.drac.get_lims_name()[0]

    def get_lims_name(self) -> List[Lims]:
        return self.drac.get_lims_name()

    def get_session_id(self) -> str:
        logger.debug("Setting up drac session_id=%s" % (self.drac.get_session_id()))
        return self.drac.get_session_id()

    def is_single_session_available(self):
        """
        True if there is no active session and there is
        a single session available
        """
        return (
            self.session_manager.active_session is None
            and len(self.session_manager.sessions) == 1
        )

    def login(self, user_name, token, is_local_host=False) -> LimsSessionManager:
        self.is_local_host = is_local_host
        _, lims_username, sessions = self.drac.login(
            user_name, token, self.session_manager
        )
        logger.debug("%s sessions found. user=%s" % (len(sessions), user_name))

        self.session_manager = self.drac.session_manager

        self.add_user_and_shared_sessions(lims_username, sessions)

        # In case there is a single available session then it is selected automatically
        if self.is_single_session_available():
            single_session = self.session_manager.sessions[0]
            logger.debug(
                "Single session available which will be selected automatically. session_id=%s"
                % (single_session.session_id)
            )
            self.set_active_session_by_id(single_session.session_id)

        return self.session_manager

    def is_user_login_type(self) -> bool:
        return True

    def is_drac(self):
        """
        Returns true if the lims used for synchronization of the samples is DRAC
        """
        return self.get_active_lims().name == self.drac.get_lims_name()[0].name

    def set_active_lims(self, lims):
        self.active_lims = lims

    def get_active_lims(self):
        return self.active_lims

    def get_samples(self, lims_id):
        """
        lims_id is the identifier of the lims to be used: DRAC
        """
        logger.debug("[ESRFLIMS] get_samples by lims %s" % lims_id)

        lims_list = [i for i in self.get_lims_name() if i.name == lims_id]
        if len(lims_list) == 1:
            active_lims = lims_list[0]
            logger.debug("[ESRFLIMS] Setting active lims %s" % active_lims.name)
            self.set_active_lims(active_lims)

        logger.debug("[ESRFLIMS] get_samples %s" % self.get_active_lims().name)

        return self.drac.get_samples(lims_id)

    def get_proposals_by_user(self, login_id: str):
        raise Exception("Not implemented")

    def create_session(self, session_dict):
        pass

    def _store_data_collection_group(self, group_data):
        group_data["sessionId"] = self.drac.get_session_id()
        return self.drac._store_data_collection_group(group_data)

    def store_data_collection(self, mx_collection, bl_config=None):
        logger.info("Storing datacollection")
        mx_collection["sessionId"] = self.drac.get_session_id()

        return self.drac.store_data_collection(mx_collection, bl_config)

    def update_data_collection(self, mx_collection):
        logger.info("Updating datacollection")
        mx_collection["sessionId"] = self.drac.get_session_id()

        return self.drac.update_data_collection(mx_collection)

    def finalize_data_collection(self, mx_collection):
        logger.info("Storing datacollection")

        mx_collection["sessionId"] = self.drac.get_session_id()
        return self.drac.finalize_data_collection(mx_collection)

    def store_image(self, image_dict):
        self.drac.store_image(image_dict)

    def find_sample_by_sample_id(self, sample_id):
        return self.drac.find_sample_by_sample_id(sample_id)

    def store_robot_action(self, robot_action_dict):
        return self.drac.store_robot_action(robot_action_dict)

    def is_session_already_active(self, session_id: str) -> bool:
        return self.drac.is_session_already_active(session_id)

    def set_active_session_by_id(self, session_id: str) -> Session:
        logger.debug("set_active_session_by_id. session_id=%s", str(session_id))

        if self.drac.session_manager.active_session is not None:
            if self.drac.session_manager.active_session.session_id == session_id:
                return self.drac.session_manager.active_session

        session = self.drac.set_active_session_by_id(session_id)

        if session is not None:
            logger.info(
                "[ESRFLIMS] MXCuBE succesfully connected to DRAC:(%s, %s)"
                % (
                    self.drac.session_manager.active_session.proposal_name,
                    self.drac.session_manager.active_session.session_id,
                )
            )
            return self.drac.session_manager.active_session
        else:
            raise Exception("Any candidate session was found")

    def allow_session(self, session: Session):
        return self.drac.allow_session(session)

    def get_session_by_id(self, sid: str):
        return self.drac.get_session_by_id(sid)

    def get_user_name(self):
        return self.drac.get_user_name()

    def get_full_user_name(self):
        return self.drac.get_full_user_name()

    def authenticate(self, login_id: str, password: str) -> LimsSessionManager:
        return self.drac.authenticate(login_id, password)

    def echo(self):
        """Mockup for the echo method."""
        return True

    def is_connected(self):
        return True

    def update_bl_sample(self, bl_sample):
        self.drac.update_bl_sample(bl_sample)

    def store_beamline_setup(self, session_id, bl_config):
        self.drac.store_beamline_setup(session_id, bl_config)

    def store_energy_scan(self, energyscan_dict):
        energyscan_dict["sessionId"] = self.drac.get_session_id()
        return self.drac.store_energy_scan(energyscan_dict)

    def store_xfe_spectrum(self, xfespectrum_dict):
        xfespectrum_dict["sessionId"] = self.drac.get_session_id()
        return self.drac.store_xfe_spectrum(xfespectrum_dict)

    def store_workflow(self, *args, **kwargs):
        pass
