import json
import logging
from json.decoder import JSONDecodeError
from typing import (
    Dict,
    List,
    Optional,
)
from urllib.parse import urljoin

import requests
from suds import WebFault

from mxcubecore.HardwareObjects.abstract.ISPyBDataAdapter import ISPyBDataAdapter
from mxcubecore.HardwareObjects.UserTypeISPyBLims import UserTypeISPyBLims
from mxcubecore.model.lims_session import (
    LimsSessionManager,
    Session,
)

log = logging.getLogger("ispyb_client")

LAZY_SESSION_PREFIX = "lazy"


def _get_lazy_session_id(proposal: Dict) -> str:
    prop_id = proposal["proposalId"]
    return f"{LAZY_SESSION_PREFIX}{prop_id}"


def _is_lazy_session_id(session_id: str) -> bool:
    return session_id.startswith(LAZY_SESSION_PREFIX)


def _check_ispyb_error_message(response):
    def _expected_ispyb_err_msg(error_msg):
        import re

        match = re.match("^JBAS011843: Failed instantiate.*ldap.*ispyb", error_msg)
        return match is not None

    #
    # check that we got the 'expected' error message on invalid credentials,
    # otherwise log the error message, so we don't swallow new error messages
    #
    if _expected_ispyb_err_msg(response.text):
        # all is fine
        return

    log.warning(
        "unexpected response from ISPyB\n"
        + f"{response.status_code} {response.reason}\n{response.text}"
    )


class ISPyBRestClient:
    def __init__(self, rest_root: str):
        self._rest_root = rest_root

    def authenticate(self, user_name: str, password: str):
        """
        authenticate with REST services

        Args:
            user_name: Username
            password: Password
        """
        token = None

        auth_url = urljoin(self._rest_root, "authenticate?site=MAXIV")
        response = requests.post(
            auth_url, data={"login": user_name, "password": password}
        )

        try:
            # if authentication is successful, we will get
            # JSON response containing an auth token
            token = response.json().get("token", None)
        except JSONDecodeError:
            # on invalid credentials, some ISPyB systems will reply with
            # an internal error message, as plain text
            _check_ispyb_error_message(response)

        if token is None:
            # we failed to obtain the auth token, thus we failed to authenticate
            raise Exception("invalid credentials")


def _create_session_object(proposal, session_id: str, beamline_name: str) -> Session:
    return Session(
        proposal_id=proposal["proposalId"],
        code=proposal["code"],
        number=proposal["number"],
        session_id=session_id,
        beamline_name=beamline_name,
        title=proposal["title"],
        #
        # At MAXIV we don't care if a session is scheduled
        # or not, mark all sessions as scheduled.
        #
        is_scheduled_time=True,
        is_scheduled_beamline=True,
    )


class CustomISPyBDataAdapter(ISPyBDataAdapter):
    """
    Extend the standard ISPyB data adapter with MAXIV specific logic of how to
    deal with proposal sessions.
    """

    def _get_proposals(self, username: str):
        proposals = json.loads(
            self._shipping.service.findProposalsByLoginName(username)
        )

        for proposal in proposals:
            if proposal["type"].upper() not in ["MX", "MB"]:
                continue
            if proposal.get("state", "Open") != "Open":
                continue

            yield proposal

    def _get_sessions(self, username: str, beamline_name: str) -> List[Session]:
        def list_sessions():
            for proposal in self._get_proposals(username):
                sessions = self._collection.service.findSessionsByProposalAndBeamLine(
                    proposal["code"], proposal["number"], beamline_name
                )

                for sesssion in sessions:
                    yield _create_session_object(
                        proposal, sesssion["sessionId"], beamline_name
                    )

                #
                # A hack to lazily create new sessions.
                #
                # At MAXIV we don't schedule sessions for proposals ahead of time. Instead, we
                # lazily create them as needed.
                #
                # If a proposal does not contain any active session, create a Session object
                # with a special session ID.
                #
                # If user selects such a session, then we will ask ISPyB to create this session.
                #
                if len(sessions) == 0:
                    yield _create_session_object(
                        proposal, _get_lazy_session_id(proposal), beamline_name
                    )

        return sorted(list_sessions(), key=lambda s: f"{s.code}{s.number}")

    def get_sessions_by_username(
        self, username: str, beamline_name: str
    ) -> LimsSessionManager:
        try:
            sessions = list(self._get_sessions(username, beamline_name))
            return LimsSessionManager(sessions=sessions)
        except WebFault as e:
            log.exception(e.message)


class ISPyBLims(UserTypeISPyBLims):
    def init(self):
        super().init()

        self._rest_client = ISPyBRestClient(self.get_property("rest_root"))

    def _create_data_adapter(self) -> ISPyBDataAdapter:
        return CustomISPyBDataAdapter(
            self.ws_root.strip(),
            self.proxy,
            self.ws_username,
            self.ws_password,
            self.beamline_name,
        )

    def ispyb_login(self, user_name: str, password: str):
        try:
            self._rest_client.authenticate(user_name, password)
            return True, None
        except Exception as ex:
            return False, str(ex)

    def set_active_session_by_id(self, session_id: str) -> Session:
        """
        Sets session with session_id to active session

        Args:
            session_id: session id
        """

        def find_session() -> Optional[Session]:
            for session in self.session_manager.sessions:
                if session.session_id == session_id:
                    self.session_manager.active_session = session

                    return session

            # session not found
            return None

        def replace_lazy(sessions: List[Session], new_session: Session):
            def gen():
                for session in sessions:
                    if session.session_id == session_id:
                        yield new_session
                    else:
                        yield session

            return list(gen())

        session = find_session()
        if session is None:
            raise Exception(f"no session with ID {session_id} found")

        #
        # user selected a session that does not exist yet,
        # ask ISPyB to create it
        #
        if _is_lazy_session_id(session_id):
            session = self.adapter.create_session(
                session.proposal_id, session.beamline_name
            )
            # replace the old lazy-session object,
            # with the new proper-session object
            self.session_manager.sessions = replace_lazy(
                self.session_manager.sessions, session
            )

        return session

    def get_full_user_name(self) -> str:
        person = self.adapter.get_person_by_username(self.user_name)

        given_name = person["givenName"]
        family_name = person["familyName"]

        return f"{given_name} {family_name}"
