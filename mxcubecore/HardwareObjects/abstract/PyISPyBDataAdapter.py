# ruff: noqa: TD003, FIX002, ERA001
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from mxcubecore.model.lims_session import LimsSessionManager, Session


class NoScheduledSessionException(Exception):
    """Exception raised when no session is planned for the current day."""


class PyISPyBDataAdapter:
    """Adapter to convert data from PyISPyB REST API."""

    def __init__(
        self,
        client,
        beamline_name: str,
    ):
        self.client = client
        # pyispyb rest client, call get/post methods to interact with PyISPyB REST API
        self.beamline_name = beamline_name
        self.new_session_duration_days = 2
        self.logger = logging.getLogger("pyispyb_adapter")

    def get_proposals(self):
        """Returns only the proposals to which authenticated user has access."""
        return self.client.get("proposals").get("results", [])

    def get_sessions_by_username(
        self,
        username: str = "",
        beamline_name: str = "",
    ) -> LimsSessionManager:
        """Get the list of sessions for the authenticated user and current beamline.

        Args:
            username: Username to fetch sessions for (left for consistency)
            beamline_name: Beamline name to fetch sessions for (left for consistency)

        Returns:
            LimsSessionManager: A manager containing the list of sessions
        """
        # TODO@dominikatrojanowska: add day to the url when implemented in py-ispyb,
        # now fetch all sessions for the month and year and filter by the day in mxcube
        now = datetime.now()  # noqa: DTZ005
        month, year = now.month, now.year
        sessions: List[Session] = []
        for proposal in self.get_proposals():
            proposal_name = proposal.get("proposal")
            try:
                session = self.__to_session(
                    self.client.get(
                        f"sessions?proposal={proposal_name}&beamlineName={self.beamline_name}&year={year}&month={month}"
                    ).get("results", [])[0],
                    proposal,
                )
                if not (session.start_datetime <= now <= session.end_datetime):
                    err = f"No session planned for proposal {proposal_name} today"
                    raise NoScheduledSessionException(err)
            except (IndexError, NoScheduledSessionException):
                self.logger.info(
                    "No sessions planned for %s for proposal %s. Creating new session.",
                    now.date(),
                    proposal_name,
                )
                session = self.create_session(proposal)

            self.logger.info(  # debug
                f"Sessions for proposal {proposal_name}: {session}"
            )
            sessions.append(session)

        return LimsSessionManager(sessions=sessions)

    def create_session(self, proposal: Dict) -> Session:
        """Creates a new Session object for the given proposal."""
        # TODO@SOLEIL: This is the closest implementation to current IPSYBAdapter.
        # Ensure session creation is correct (session data, posting to PY-ISPYB).
        # Which part can be common for SOLEIL and MAX IV?
        # TODO@dominikatrojanowska: check if response is ok and handle errors
        #  NOT TESTED
        start_time = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_time = start_time + timedelta(
            days=self.new_session_duration_days, hours=7, minutes=59, seconds=59
        )
        payload = {
            "proposalId": proposal["proposalId"],
            "startDate": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "endDate": end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "beamlineName": self.beamline_name,
            "comments": "Session created by the BCM",
            "scheduled": False,
        }
        return self.__to_session(self.client.post("sessions", json=payload), proposal)

    def __to_session(self, session: Dict, proposal=None) -> Session:
        """Converts session data received from PyISPyB REST API to a Session object."""
        proposal_name = session.get("proposal")
        if proposal:
            proposal_code = proposal.get("proposalCode")
            proposal_number = proposal.get("proposalNumber")
            title = proposal.get("title")
        else:
            # TODO@dominikatrojanowska: maybe else can be removed at all
            proposal_code = "".join([c for c in proposal_name if not c.isdigit()])
            proposal_number = proposal_name[len(proposal_code) :]
            title = session.get("title", "")
        start_datetime = session.get("startDate")
        end_datetime = session.get("endDate")
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
            nb_shifts=session.get("nbShifts"),
            scheduled=session.get("scheduled", "False"),
            is_scheduled_time=True,  # MAX IV does not care about this value
            is_scheduled_beamline=True,  # MAX IV does not care about this value
        )
