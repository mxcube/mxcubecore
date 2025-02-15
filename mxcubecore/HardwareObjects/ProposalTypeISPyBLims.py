from __future__ import print_function

import itertools
import uuid

from mxcubecore.HardwareObjects.abstract.ISPyBAbstractLims import ISPyBAbstractLIMS
from mxcubecore.model.lims_session import (
    LimsSessionManager,
    Proposal,
    Session,
)

"""
A client for ISPyB Webservices.
"""

import logging


class ProposalTypeISPyBLims(ISPyBAbstractLIMS):
    """
    ISPyB proposal-based client
    """

    def __init__(self, name):
        super().__init__(name)

    def is_user_login_type(self):
        return False

    def get_proposals_by_user(self, login_id: str):
        raise Exception("Not implemented")

    def get_full_user_name(self):
        return self.get_user_name()

    def get_user_name(self):
        """
        Because it is a proposal based it returns the proposal plus the uuid4
        """
        return f"{self.user_name}-{str(uuid.uuid4())}"

    def _authenticate(self, user_name, psd):
        """
        Authentication step based on the authServerType
        """

        if self.authServerType == "ldap":
            logging.getLogger("HWR").debug(
                "Starting LDAP authentication %s" % user_name
            )
            ok = self.ldap_login(user_name, psd)
        elif self.authServerType == "ispyb":
            logging.getLogger("HWR").debug("ISPyB login")
            ok, _ = self.ispyb_login(user_name, psd)
        else:
            raise Exception("Authentication server type is not defined")

        if not ok:
            # refuse Login
            logging.getLogger("HWR").error(
                "Authentication with %s failed" % self.authServerType
            )
            raise Exception("Authentication failed")

        logging.getLogger("HWR").debug(
            "User %s logged in %s" % (user_name, self.authServerType)
        )

    def is_session_already_active_by_code(self, code: str, number: str) -> bool:
        # If curent selected session is already selected no need to do
        # anything else
        active_session = self.session_manager.active_session
        if active_session is not None:
            if (
                code.upper() == active_session.code.upper()
                and number.upper() == active_session.number.upper()
            ):
                return True
        return False

    def set_active_session_by_id(self, proposal_name: str) -> Session:
        """
        Given a proposal name it will select a session that is scheduled on this beamline in the current timeslot
        """
        if self.is_session_already_active(self.session_manager.active_session):
            logging.getLogger("HWR").debug("[ISPYB] is_session_already_active")
            return self.session_manager.active_session

        if len(self.session_manager.sessions) == 0:
            logging.getLogger("HWR").error(
                "Session list is empty. No session candidates"
            )
            raise Exception("No sessions available")

        if len(self.session_manager.sessions) == 1:
            self.session_manager.active_session = self.session_manager.sessions[0]
            logging.getLogger("HWR").debug(
                "Session list contains a single session. proposal_name=%s",
                self.session_manager.active_session.proposal_name,
            )
            return self.session_manager.active_session

        session_list = [
            obj
            for obj in self.session_manager.sessions
            if (
                obj.proposal_name.upper() == proposal_name.upper()
                and obj.is_scheduled_beamline
                and obj.is_scheduled_time
            )
        ]
        if len(session_list) > 1:
            logging.getLogger("HWR").warning(
                "Session not found in the local list of sessions. Found %s sessions. proposal_name=%s"
                % (len(session_list), proposal_name)
            )
        self.session_manager.active_session = session_list[0]
        return self.session_manager.active_session

    def _get_proposal_code_and_number_by_proposal_name(self, proposal_name):
        code = "".join(itertools.takewhile(lambda c: not c.isdigit(), proposal_name))
        number = proposal_name[len(code) :]
        return [code, number]

    def get_session_manager_by_code_number(
        self, code: str, number: str, is_local_host: bool
    ) -> LimsSessionManager:
        logging.getLogger("HRW").debug("[ISPyB] get_session_manager_by_code_number")

        self.session_manager = self.adapter.get_sessions_by_code_and_number(
            code, number, self.beamline_name
        )
        proposal_name = code + number
        # If there is no session then a session is created
        if len(self.session_manager.sessions) == 0 and is_local_host:
            logging.getLogger("HRW").debug(
                "No sessions found for proposal=%s" % proposal_name
            )
            logging.getLogger("HRW").debug(
                "Creating session for proposal=%s" % proposal_name
            )
            proposal: Proposal = self.adapter.find_proposal(code, number)
            self.create_session(proposal.proposal_id)
            self.session_manager = self.adapter.get_sessions_by_code_and_number(
                code, number, self.beamline_name
            )
            logging.getLogger("HRW").debug(
                "Sessions count=%s" % len(self.session_manager.sessions)
            )

        self.set_active_session_by_id(proposal_name)

        return self.session_manager

    def get_session_manager_by_proposal_name(
        self, proposal_name: str, is_local_host: bool
    ) -> LimsSessionManager:
        code_number = self._get_proposal_code_and_number_by_proposal_name(proposal_name)
        code = self._translate(
            code_number[0],
            "ispyb",
        )
        number = code_number[1]

        return self.get_session_manager_by_code_number(code, number, is_local_host)

    def login(
        self, user_name: str, password: str, is_local_host: bool
    ) -> LimsSessionManager:
        logging.getLogger("HRW").debug(
            "Login on ISPyBLims proposal=%s is_local_host=%s"
            % (user_name, str(is_local_host)),
        )
        self.session_manager = LimsSessionManager()
        # For porposal login, split the loginID to code and numbers
        code = self._get_proposal_code_and_number_by_proposal_name(user_name)[0]
        number = self._get_proposal_code_and_number_by_proposal_name(user_name)[1]

        # if translation of the loginID is needed, need to be tested by ESRF
        if self.loginTranslate is True:
            user_name = self._translate(code, "ldap") + str(number)

        # Authentication
        try:
            self._authenticate(user_name, password)
            self.user_name = user_name
        except Exception as e:
            raise e

        return self.get_session_manager_by_proposal_name(user_name, is_local_host)
