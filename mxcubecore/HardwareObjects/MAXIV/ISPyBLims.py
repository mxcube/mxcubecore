# ruff: noqa: TD003, FIX002, ERA001
import logging

try:
    # duo is a part of sdm package that lives at MaxIV private repository
    from duo.UO import RestDuo
    from sdm.config import DUOPASSWORD, DUOUSER
except ImportError:
    RestDuo = None
    DUOPASSWORD = None
    DUOUSER = None

from mxcubecore.HardwareObjects.abstract.PyISPyBDataAdapter import PyISPyBDataAdapter
from mxcubecore.HardwareObjects.abstract.PyISPyBRestClient import PyISPyBRestClient
from mxcubecore.HardwareObjects.UserTypeISPyBLims import UserTypeISPyBLims
from mxcubecore.model.lims_session import Proposal, Session

DUO_API_URL = "https://duo-api.maxiv.lu.se"
LAZY_SESSION_PREFIX = "lazy"

log = logging.getLogger("ispyb_client")


class NoSessionException(Exception):
    """Exception raised when no expected session found."""


class CustomISPyBDataAdapter(PyISPyBDataAdapter):
    """Extend the standard ISPyB data adapter with MAXIV specific logic."""

    def get_proposals(self):
        """Override method to filter proposals by the type, state and beamline name.

        Include proposals: of type ``MX`` or ``MB`` in ``Open`` state and assigned
        to the current beamline. The last is checked via DUO API.
        """
        duo = RestDuo(DUO_API_URL)
        duo.login(DUOUSER, DUOPASSWORD)
        beamline_proposals_ids = set(duo.get_beamline_proposals(self.beamline_name))
        return [
            proposal
            for proposal in super().get_proposals()
            if proposal.code in ["MX", "MB"]
            and proposal.state == "Open"
            and int(proposal.number) in beamline_proposals_ids
        ]

    def create_session(self, proposal: Proposal) -> Session:
        """Create a new Session object for the given proposal and beamline.

        This is a lazy session creation, done automatically on the fly in case
        no appropriate session is found for the user, proposal and current day.
        This session is labelled with ``lazy`` prefix and is not posted to
        Py-ISPYB service until it is selected.

        Args:
            proposal: Proposal object to create session for

        Returns:
            Session: Created session object
        """
        return Session(
            code=proposal.code,
            number=proposal.number,
            proposal_name=proposal.name,
            proposal_id=proposal.proposal_id,
            session_id=f"{LAZY_SESSION_PREFIX}{proposal.proposal_id}",
            beamline_name=self.beamline_name,
            title=proposal.title,
            # At MAXIV we don't care if a session is scheduled, set True as default
            is_scheduled_time=True,
            is_scheduled_beamline=True,
            # TODO@dominikatrojanowska: check if we should set start and end time for the session created on fly, and if so, what time should be set. For now, we just set empty string, and let ISPyB handle it.
            # "startDate": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            # "endDate": end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )


class ISPyBLims(UserTypeISPyBLims):
    def init(self):
        pyispyb_rest_root = self.get_property("pyispyb_rest_root")
        self._rest_client = PyISPyBRestClient(pyispyb_rest_root)
        super().init()

    def _create_data_adapter(self) -> CustomISPyBDataAdapter:
        return CustomISPyBDataAdapter(
            self._rest_client,
            self.beamline_name,
        )

    def ispyb_login(self, user_name: str, password: str):
        """Authenticate with ISPyB REST services.

        In fact password is an access token obtained from Keycloak, but we call it
        password to keep the interface consistent with other LIMS implementations.

        Args:
            user_name: Username to authenticate with
            password: Password (access token) to authenticate with
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing a boolean indicating
            success or failure, and an optional error message.
        """
        try:
            self._rest_client.authenticate(user_name, token=password)
        except Exception as ex:
            return False, str(ex)
        return True, None

    def set_active_session_by_id(self, session_id: str) -> Session:
        """Sets session with session_id to active session.

        It is possible that user picks the session that does not exist in the database yet, so called lazy session created on the fly. In that case the session POST request is sent to the server in order to create the session in the database and get the proper session id.

        Args:
            session_id: session id
        """
        session_to_activate = None
        for _idx, session in enumerate(self.session_manager.sessions):
            if session.session_id == session_id:
                session_to_activate = session
                break
        else:
            err = f"No session with ID {session_id} found."
            raise NoSessionException(err)

        if session_id.startswith(LAZY_SESSION_PREFIX):
            payload = {
                "proposalId": session_to_activate.proposal_id,
                "startDate": session_to_activate.start_datetime.strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"
                ),
                "endDate": session_to_activate.end_datetime.strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"
                ),
                "beamLineName": session_to_activate.beamline_name,
                "comments": "Session created by the BCM",
                # At MAXIV we consider session created on fly as scheduled
                "scheduled": True,
            }
            new_session = self.adapter.client.post("sessions", json=payload)
            session_to_activate.session_id = new_session.get("sessionId")
            self.session_manager.sessions[_idx] = session_to_activate

        self.session_manager.active_session = session_to_activate

        return session_to_activate

    def get_full_user_name(self) -> str:
        person = self.adapter.get_current_user_data()
        return "%s %s" % (person["givenName"], person["familyName"])

    def xrf_spectrum_results_url(self, spectrum_id: int) -> str:
        return self._rest_client.get_xrf_graph_url(spectrum_id)
