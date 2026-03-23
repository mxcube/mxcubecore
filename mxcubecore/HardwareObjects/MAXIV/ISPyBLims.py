# ruff: noqa: TD003, FIX002, ERA001
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
from duo.UO import RestDuo  # part of sdm package
from sdm.config import DUOPASSWORD, DUOUSER
from suds import WebFault

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.ISPyBDataAdapter import ISPyBDataAdapter
from mxcubecore.HardwareObjects.abstract.PyISPyBDataAdapter import PyISPyBDataAdapter
from mxcubecore.HardwareObjects.MAXIV.PyISPyBLims import PyISPyBRestClient
from mxcubecore.HardwareObjects.UserTypeISPyBLims import UserTypeISPyBLims
from mxcubecore.model.lims_session import (
    LimsSessionManager,
    Session,
)

DUO_API_URL = "https://duo-api.maxiv.lu.se"
LAZY_SESSION_PREFIX = "lazy"

log = logging.getLogger("ispyb_client")


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
        # EXI uses auth token in the URL path...
        self._rest_token = None

    def authenticate(self, user_name: str, password: str):
        """
        authenticate with REST services

        Args:
            user_name: Username
            password: Password
        """
        auth_url = urljoin(self._rest_root, "authenticate?site=MAXIV")
        response = requests.post(
            auth_url, data={"login": user_name, "password": password}
        )

        try:
            # if authentication is successful, we will get
            # JSON response containing an auth token
            self._rest_token = response.json().get("token", None)
        except JSONDecodeError:
            # on invalid credentials, some ISPyB systems will reply with
            # an internal error message, as plain text
            _check_ispyb_error_message(response)

        if self._rest_token is None:
            # we failed to obtain the auth token, thus we failed to authenticate
            raise Exception("invalid credentials")

    def get_xrf_graph_url(self, spectrum_id: int) -> str:
        if self._rest_token is None:
            raise Exception("not authenticated")

        url = "{rest_root}{token}"
        # note: this is path for the EXI front-end, Py-ISPyB will have
        # different URL and will require token to be sent in a header.
        url += "/proposal/{pcode}{pnumber}/mx/xrfscan/xrfscanId/{spectrum_id}/image/jpegScanFileFullPath/get"
        return url.format(
            rest_root=self._rest_root,
            token=str(self._rest_token),
            pcode=HWR.beamline.session.proposal_code,
            pnumber=HWR.beamline.session.proposal_number,
            spectrum_id=spectrum_id,
        )


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


class CustomISPyBDataAdapter(ISPyBDataAdapter, PyISPyBDataAdapter):
    """Extend the standard ISPyB data adapter with MAXIV specific logic."""

    def _filter_proposals(self, proposals: List[Dict]):
        """Filter proposals by the beamline, state and type.

        Include proposals: of type ``MX`` or ``MB`` in ``Open`` state and assigned to the current beamline. The last is done via DUO API.

        Args:
            proposals: list of proposals to filter
        """
        duo = RestDuo(DUO_API_URL)
        duo.login(DUOUSER, DUOPASSWORD)
        beamline_proposals_ids = set(duo.get_beamline_proposals(self.beamline_name))
        for proposal in proposals:
            # TODO@dominikatrojanowska: "type" field will be added to PyISPyB in the future
            if proposal["proposalCode"].upper() not in ["MX", "MB"]:
                continue
            if proposal.get("state", "Open") != "Open":
                continue
            if int(proposal["proposalNumber"]) not in beamline_proposals_ids:
                continue
            yield proposal

    def get_proposals(self):
        """Override the get_proposals method to filter proposals by the beamline, state and type."""
        return self._filter_proposals(super().get_proposals())

    def create_session(self, proposal: Dict) -> Session:
        """Create a new Session object for the given proposal and beamline.

        This is a lazy session creation, done automatically on the fly in case
        no appropriate session is found for the user, proposal and current day.
        This session is labelled with ``lazy`` prefix and is not posted to
        Py-ISPYB service until it is selected.

        Args:
            proposal: Proposal dictionary to create session for

        Returns:
            Session: Created session object
        """
        return Session(
            code=proposal["proposalCode"],
            number=proposal["proposalNumber"],
            proposal_name=proposal.get("proposal"),
            proposal_id=proposal["proposalId"],
            session_id=_get_lazy_session_id(proposal),
            beamline_name=self.beamline_name,
            title=proposal["title"],
            # At MAXIV we don't care if a session is scheduled, set True as default
            is_scheduled_time=True,
            is_scheduled_beamline=True,
            # TODO@dominikatrojanowska: check if we should set start and end time for the session created on fly, and if so, what time should be set. For now, we just set empty string, and let ISPyB handle it.
            # "startDate": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            # "endDate": end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )

    # TODO@dominikatrojanowska: remove all methods below after dropping an old adapter
    def __init__(  # noqa: PLR0913
        self,
        ws_root,
        proxy,
        ws_username,
        ws_password,
        beamline_name,
        rest_client=None,
    ):
        ISPyBDataAdapter.__init__(
            self, ws_root, proxy, ws_username, ws_password, beamline_name
        )
        PyISPyBDataAdapter.__init__(self, rest_client, beamline_name)

    def _get_proposals(self, username: str, beamline_name: str):
        duo = RestDuo(DUO_API_URL)
        duo.login(DUOUSER, DUOPASSWORD)
        beamline_proposals_ids = set(duo.get_beamline_proposals(beamline_name))
        proposals = json.loads(
            self._shipping.service.findProposalsByLoginName(username)
        )
        for proposal in proposals:
            # only include MX and MB (proprietary) proposals
            if proposal["type"].upper() not in ["MX", "MB"]:
                continue
            # only include 'Open' proposals
            if proposal.get("state", "Open") != "Open":
                continue
            # only include proposals that belong to this beamline
            if int(proposal["number"]) not in beamline_proposals_ids:
                continue
            yield proposal

    def _get_sessions(self, username: str, beamline_name: str) -> List[Session]:
        def list_sessions():
            for proposal in self._get_proposals(username, beamline_name):
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
        PyISPyBDataAdapter.get_sessions_by_username(self)
        try:
            sessions = list(self._get_sessions(username, beamline_name))
            return LimsSessionManager(sessions=sessions)
        except WebFault as e:
            log.exception(e.message)


class ISPyBLims(UserTypeISPyBLims):
    def init(self):
        self._rest_root: str = self.get_property("rest_root")
        self._rest_client = ISPyBRestClient(self._rest_root)
        self._py_rest_client = PyISPyBRestClient(
            "https://py-ispyb-backend.maxiv.lu.se/ispyb/api/v1/"
        )
        super().init()

    def _create_data_adapter(self) -> ISPyBDataAdapter:
        return CustomISPyBDataAdapter(
            self.ws_root.strip(),
            self.proxy,
            self.ws_username,
            self.ws_password,
            self.beamline_name,
            self._py_rest_client,
        )

    def ispyb_login(self, user_name: str, password: str):
        try:
            self._py_rest_client.authenticate(user_name, password)
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

    def xrf_spectrum_results_url(self, spectrum_id: int) -> str:
        return self._rest_client.get_xrf_graph_url(spectrum_id)
