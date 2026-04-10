# ruff: noqa: TD003, FIX002, ERA001

import logging
from datetime import datetime, timedelta
from typing import Dict, List

from mxcubecore.HardwareObjects.MAXIV import PyISPyBRestClient
from mxcubecore.model.lims_session import LimsSessionManager, Proposal, Session


class PyISPyBDataAdapter:
    """Adapter to convert data from PyISPyB REST API."""

    def __init__(
        self,
        client: PyISPyBRestClient,
        beamline_name: str,
        new_session_duration_days: int = 2,
    ):
        self.client = client
        self.beamline_name = beamline_name
        self.new_session_duration_days = new_session_duration_days
        self.logger = logging.getLogger("pyispyb_adapter")

    # =========================
    #  USER DATA
    # =========================

    def get_current_user_data(self) -> Dict:
        """Fetches current user details."""
        return self.client.get("user/current")

    # =========================
    #  PROPOSALS
    # =========================

    def get_proposals(self) -> List[Proposal]:
        """Returns proposals to which authenticated user has access."""
        return [
            self.__to_proposal(proposal)
            for proposal in self.client.get("proposals").get("results", [])
        ]

    def find_proposal(self, code: str, number: str) -> Proposal:
        """Finds a proposal by its code and number."""
        return self.__to_proposal(
            self.client.get("proposals?proposal=%s%s" % (code, number))
        )

    # =========================
    #  SESSIONS
    # =========================

    def get_sessions_by_code_and_number(
        self, code: str, number: str, beamline: str
    ) -> LimsSessionManager:
        """Finds a session by its proposal code and number and beamline name."""
        return LimsSessionManager(
            sessions=[
                self.__to_session(session)
                for session in self.client.get(
                    "sessions?proposal=%s%s&beamLineName=%s" % (code, number, beamline)
                ).get("results", [])
            ]
        )

    def find_sessions_by_proposal_and_beamline_for_today(
        self, code: str, number: str, beamline: str
    ) -> List[Session]:
        """Finds todays sessions by proposal code, number and beamline name."""
        # TODO@dominikatrojanowska: add ``day`` to the url when implemented in py-ispyb,
        # Until then fetch all sessions for month and year, next filter by day in mxcube
        today = datetime.today()  # noqa: DTZ002
        month, year = today.month, today.year
        return [
            self.__to_session(session)
            for session in self.client.get(
                "sessions?proposal=%s%s&beamLineName=%s&year=%s&month=%s"
                % (code, number, beamline, year, month)
            ).get("results", [])
            if self.__is_time_between(
                datetime.fromisoformat(session.get("startDate")),
                datetime.fromisoformat(session.get("endDate")),
            )
        ]

    def get_sessions_by_username(
        self,
        username: str = "",
        beamline_name: str = "",
    ) -> LimsSessionManager:
        """Get the list of sessions for the authenticated user and current beamline.

        Py-ISPyB returns only proposals accessible to the authenticated user.
        For each proposal, the method fetches sessions for the current month and
        picks one overlapping with the current time. If no such session exists,
        a new one is created.
        Args:
            username: Username to fetch sessions for (left for consistency)
            beamline_name: Beamline name to fetch sessions for (left for consistency)

        Returns:
            LimsSessionManager: A manager containing the list of sessions
        """
        sessions: List[Session] = []
        for proposal in self.get_proposals():
            try:
                session = self.find_sessions_by_proposal_and_beamline_for_today(
                    proposal.code, proposal.number, self.beamline_name
                )[0]
            except IndexError:
                self.logger.info(
                    "No sessions planned for proposal %s. Creating new session.",
                    proposal.name,
                )
                session = self.create_session(proposal)
            sessions.append(session)
        return LimsSessionManager(sessions=sessions)

    def create_session(self, proposal: Proposal) -> Session:
        """Creates new session via PyISPyB REST API for the given proposal."""
        # TODO@SOLEIL: This is the closest implementation to current IPSYBAdapter.
        # Ensure session creation is correct (session data, posting to PY-ISPYB).
        # Which part can be common for SOLEIL and MAX IV?
        # TODO@dominikatrojanowska: check if response is ok and handle errors
        #  NOT TESTED
        start_time = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)  # noqa: DTZ002
        end_time = start_time + timedelta(
            days=self.new_session_duration_days, hours=7, minutes=59, seconds=59
        )
        payload = {
            "proposalId": proposal.proposal_id,
            "startDate": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "endDate": end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "beamLineName": self.beamline_name,
            "comments": "Session created by the BCM",
            "scheduled": False,
        }
        return self.__to_session(self.client.post("sessions", json=payload), proposal)

    # =========================
    #  HELPER METHODS
    # =========================

    def __to_proposal(self, proposal: Dict[str, str]) -> Proposal:
        """
        Converts proposal data received from PyISPyB REST API to a Proposal object.
        """
        return Proposal(
            code=proposal.get("proposalCode").upper(),
            number=proposal.get("proposalNumber"),
            proposal_id=proposal.get("proposalId"),
            title=proposal.get("title"),
            type=proposal.get("type", ""),
            name=proposal.get("proposal"),
            state=proposal.get("state", "").capitalize(),
        )

    def __to_session(self, session: Dict, proposal: Proposal = None) -> Session:
        """Converts session data received from PyISPyB REST API to a Session object."""
        if proposal:
            proposal_name = proposal.name
            proposal_code = proposal.code
            proposal_number = proposal.number
            title = proposal.title
        else:
            proposal_name = session.get("proposal")
            proposal_code = "".join([c for c in proposal_name if not c.isdigit()])
            proposal_number = proposal_name[len(proposal_code) :]
            title = session.get("title", "")
        start_datetime = datetime.fromisoformat(session.get("startDate"))
        end_datetime = datetime.fromisoformat(session.get("endDate"))
        return Session(
            code=proposal_code,
            number=proposal_number,
            proposal_name=proposal_name,
            proposal_id=session.get("proposalId"),
            session_id=session.get("sessionId"),
            beamline_name=session.get("beamLineName", self.beamline_name),
            title=title,
            comments=session.get("comments"),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            # TODO@dominikatrojanowska: check if needed
            # start_date=datetime.strftime(start_datetime, "%Y%m%d"),
            # end_date=datetime.strftime(end_datetime, "%Y%m%d"),
            # start_time=start_datetime,
            # end_time=end_datetime,
            # nbShifts can be None, convert to empty string for consistency
            nb_shifts=session.get("nbShifts", "") or "",
            scheduled=session.get("scheduled", "False"),
            is_scheduled_time=self.__is_time_between(start_datetime, end_datetime),
            is_scheduled_beamline=True,  # MAX IV does not care about this value
        )

    def __is_time_between(
        self, start_datetime: datetime, end_datetime: datetime
    ) -> bool:
        """Checks if the current time is between start and end."""
        today = datetime.today()  # noqa: DTZ002
        try:
            return start_datetime <= today <= end_datetime
        except TypeError:
            self.logger.exception(
                "Invalid date format. start: %s, end: %s, now: %s",
                start_datetime,
                end_datetime,
                today,
            )
            return False
