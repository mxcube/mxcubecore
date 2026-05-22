# ruff: noqa: TD003, FIX002, ERA001
from mxcubecore.HardwareObjects.abstract.PyISPyBRestClient import PyISPyBRestClient
from mxcubecore.HardwareObjects.MAXIV.MAXIVPyISPYyBDataAdapter import (
    LAZY_SESSION_PREFIX,
    MAXIVPyISPyBDataAdapter,
)
from mxcubecore.HardwareObjects.UserTypeISPyBLims import UserTypeISPyBLims
from mxcubecore.model.lims_session import Session


class NoSessionException(Exception):
    """Exception raised when no expected session found."""


class ISPyBLims(UserTypeISPyBLims):
    def init(self):
        pyispyb_rest_root = self.get_property("pyispyb_rest_root")
        self._rest_client = PyISPyBRestClient(pyispyb_rest_root)
        super().init()

    def _create_data_adapter(self) -> MAXIVPyISPyBDataAdapter:
        return MAXIVPyISPyBDataAdapter(
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
