import logging
from typing import List

from mxcubecore.HardwareObjects.abstract.AbstractLims import AbstractLims
from mxcubecore.model.lims_session import (
    Lims,
    LimsSessionManager,
    Session,
)


class ESRFLIMS(AbstractLims):
    """
    ESRF client (ICAT+ and IPyB).
    """

    def __init__(self, name):
        super().__init__(name)

    def init(self):
        self.drac = self.get_object_by_role("drac")
        self.ispyb = self.get_object_by_role("ispyb")

        self.is_local_host = False

    def get_lims_name(self) -> List[Lims]:
        return self.drac.get_lims_name() + self.ispyb.get_lims_name()

    def get_session_id(self) -> str:
        logging.getLogger("HWR").debug(
            "Setting up drac session_id=%s" % (self.drac.get_session_id())
        )
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
        session_manager, lims_username, sessions = self.drac.login(
            user_name, token, self.session_manager
        )
        logging.getLogger("HWR").debug(
            "%s sessions found. user=%s" % (len(sessions), user_name)
        )

        self.session_manager = self.drac.session_manager
        self.add_user_and_shared_sessions(lims_username, sessions)

        # In case there is a single available session then it is selected automatically
        if self.is_single_session_available():
            single_session = self.session_manager.sessions[0]
            logging.getLogger("HWR").debug(
                "Single session available which will be selected automatically. session_id=%s"
                % (single_session.session_id)
            )
            self.set_active_session_by_id(single_session.session_id)

        if session_manager.active_session is None:
            logging.getLogger("HWR").debug(
                "DRAC no session selected then no activation of session in ISPyB"
            )
        else:
            self.ispyb.get_session_manager_by_code_number(
                session_manager.active_session.code,
                session_manager.active_session.number,
                self.is_local_host,
            )
        return self.session_manager

    def is_user_login_type(self) -> bool:
        return True

    def get_samples(self, lims_name):
        logging.getLogger("HWR").debug("[ESRFLIMS] get_samples %s" % lims_name)

        drac_lims = [
            lims for lims in self.drac.get_lims_name() if lims.name == lims_name
        ]
        if len(drac_lims) == 1:
            return self.drac.get_samples(lims_name)
        else:
            return self.ispyb.get_samples(lims_name)

    def get_proposals_by_user(self, login_id: str):
        raise Exception("Not implemented")

    def create_session(self, session_dict):
        pass

    def _store_data_collection_group(self, group_data):
        group_data["sessionId"] = self.ispyb.get_session_id()
        return self.ispyb._store_data_collection_group(group_data)

    def store_data_collection(self, mx_collection, bl_config=None):
        logging.getLogger("HWR").info("Storing datacollection")
        mx_collection["sessionId"] = self.ispyb.get_session_id()
        self.drac.store_data_collection(mx_collection, bl_config)
        return self.ispyb.store_data_collection(mx_collection, bl_config)

    def update_data_collection(self, mx_collection):
        logging.getLogger("HWR").info("Updating datacollection")
        mx_collection["sessionId"] = self.ispyb.get_session_id()
        self.drac.update_data_collection(mx_collection)
        return self.ispyb.update_data_collection(mx_collection)

    def finalize_data_collection(self, mx_collection):
        logging.getLogger("HWR").info("Storing datacollection")
        mx_collection["sessionId"] = self.ispyb.get_session_id()
        self.drac.finalize_data_collection(mx_collection)
        return self.ispyb.finalize_data_collection(mx_collection)

    def store_image(self, image_dict):
        self.ispyb.store_image(image_dict)

    def find_sample_by_sample_id(self, sample_id):
        return self.ispyb.find_sample_by_sample_id(sample_id)

    def store_robot_action(self, robot_action_dict):
        robot_action_dict["sessionId"] = self.ispyb.get_session_id()
        return self.ispyb.store_robot_action(robot_action_dict)

    def is_session_already_active(self, session_id: str) -> bool:
        return self.drac.is_session_already_active(session_id)

    def set_active_session_by_id(self, session_id: str) -> Session:
        logging.getLogger("HWR").debug(
            "set_active_session_by_id. session_id=%s", str(session_id)
        )

        if self.drac.session_manager.active_session is not None:
            if self.ispyb.session_manager.active_session is not None:
                if self.drac.session_manager.active_session.session_id == session_id:
                    return self.drac.session_manager.active_session

        session = self.drac.set_active_session_by_id(session_id)

        # Check that session is not active already

        if self.ispyb.is_session_already_active_by_code(
            self.drac.session_manager.active_session.code,
            self.drac.session_manager.active_session.number,
        ):
            return self.drac.session_manager.active_session

        if session is not None:
            self.ispyb.get_session_manager_by_code_number(
                self.drac.session_manager.active_session.code,
                self.drac.session_manager.active_session.number,
                self.is_local_host,
            )

            if (
                self.drac.session_manager.active_session is not None
                and self.ispyb.session_manager.active_session is not None
            ):
                logging.getLogger("HWR").info(
                    "[ESRFLIMS] MXCuBE succesfully connected to DRAC:(%s, %s) ISPYB:(%s,%s)"
                    % (
                        self.drac.session_manager.active_session.proposal_name,
                        self.drac.session_manager.active_session.session_id,
                        self.ispyb.session_manager.active_session.proposal_name,
                        self.ispyb.session_manager.active_session.session_id,
                    )
                )
            else:
                logging.getLogger("HWR").warning(
                    "[ESRFLIMS] Problem when set_active_session_by_id. DRAC:(%s) ISPYB:(%s)"
                    % (
                        self.drac.session_manager.active_session.proposal_name,
                        self.ispyb.session_manager.active_session,
                    )
                )
            return self.drac.session_manager.active_session
        else:
            raise Exception("Any candidate session was found")

    def allow_session(self, session: Session):
        return self.drac.allow_session(session)

    def get_session_by_id(self, id: str):
        return self.drac.get_session_by_id(id)

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
        self.ispyb.update_bl_sample(bl_sample)

    def store_beamline_setup(self, session_id, bl_config):
        self.ispyb.store_beamline_setup(session_id, bl_config)

    def store_energy_scan(self, energyscan_dict):
        energyscan_dict["sessionId"] = self.ispyb.get_session_id()
        return self.ispyb.store_energy_scan(energyscan_dict)

    def store_xfe_spectrum(self, xfespectrum_dict):
        xfespectrum_dict["sessionId"] = self.ispyb.get_session_id()
        return self.ispyb.store_xfe_spectrum(xfespectrum_dict)

    def store_workflow(self, *args, **kwargs):
        pass
