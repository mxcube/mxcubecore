import logging
from datetime import datetime, timedelta

from mxcubecore.HardwareObjects.abstract.PyISPyBRestClient import (
    PyISPyBRestClient,
    PyISPyBUnsuccessfulResponse,
)
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

    def __to_proposal(self, proposal: dict[str, str]) -> Proposal:
        """
        Converts proposal data received from PyISPyB REST API to a Proposal object.
        """
        return Proposal(
            code=proposal.get("proposalCode").upper(),
            number=proposal.get("proposalNumber"),
            proposal_id=str(proposal.get("proposalId")),
            title=proposal.get("title"),
            type=proposal.get("type", ""),
            name=proposal.get("proposal"),
            state=proposal.get("state", "").capitalize(),
        )

    def __to_session(self, session: dict) -> Session:
        """Converts session data received from PyISPyB REST API to a Session object."""
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
            proposal_id=str(session.get("proposalId")),
            session_id=str(session.get("sessionId")),
            beamline_name=session.get("beamLineName", self.beamline_name),
            title=title,
            comments=session.get("comments"),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            nb_shifts=str(session.get("nbShifts", "")),
            scheduled=str(session.get("scheduled", "False")),
            is_scheduled_time=self.__is_time_between(start_datetime, end_datetime),
            is_scheduled_beamline=True,  # MAX IV does not care about this value
        )

    def __find_proposal_by_id(self, proposal_id: int) -> Proposal:
        return self.__to_proposal(
            self.client.get("proposals?proposalId=%s" % (proposal_id))[0]
        )

    def get_current_user_data(self) -> dict:
        """Fetches current user details."""
        return self.client.get("user/current")

    def get_proposals(self) -> list[Proposal]:
        """Returns proposals to which authenticated user has access."""
        return [
            self.__to_proposal(proposal) for proposal in self.client.get("proposals")
        ]

    def find_proposal(self, code: str, number: str) -> Proposal:
        """Finds a proposal by its code and number."""
        return self.__to_proposal(
            self.client.get("proposals?search=%s%s" % (code, number))[0]
        )

    def get_sessions_by_code_and_number(
        self, code: str, number: str, beamline: str
    ) -> LimsSessionManager:
        """Finds a session by its proposal code and number and beamline name."""
        return LimsSessionManager(
            sessions=[
                self.__to_session(session)
                for session in self.client.get(
                    "sessions?proposal=%s%s&beamLineName=%s" % (code, number, beamline)
                )
            ]
        )

    def find_sessions_by_proposal_and_beamline_for_today(
        self, code: str, number: str, beamline: str
    ) -> list[Session]:
        """Finds todays sessions by proposal code, number and beamline name."""
        today = datetime.today()  # noqa: DTZ002
        day, month, year = today.day, today.month, today.year
        return [
            self.__to_session(session)
            for session in self.client.get(
                "sessions?proposal=%s%s&beamLineName=%s&year=%s&month=%s&day=%s"
                % (code, number, beamline, year, month, day)
            )
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

        PyISPyB returns only proposals accessible to the authenticated user.
        For each proposal, the method fetches sessions for the current month and
        picks one overlapping with the current time. If no such session exists,
        a new one is created.
        Args:
            username: Username to fetch sessions for (left for consistency)
            beamline_name: Beamline name to fetch sessions for (left for consistency)

        Returns:
            LimsSessionManager: A manager containing the list of sessions
        """
        sessions: list[Session] = []
        for proposal in self.get_proposals():
            try:
                session = self.find_sessions_by_proposal_and_beamline_for_today(
                    proposal.code, proposal.number, self.beamline_name
                )[0]
            except IndexError:
                self.logger.info(
                    "No sessions planned for proposal %s%s. Creating new session.",
                    proposal.code,
                    proposal.number,
                )
                session = self.create_session(proposal)
            sessions.append(session)
        return LimsSessionManager(sessions=sessions)

    def create_session(self, proposal: Proposal) -> Session:
        """Creates new session via PyISPyB REST API for the given proposal."""
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
        return self.__to_session(self.client.post("sessions", json=payload))

    def _store_data_collection_group(self, group_data: dict) -> dict:
        """Stores data collection group in PyISPyB and returns the group id.

        Args:
            group_data: A dictionary containing data collection group information.

        Returns:
            Response from PyISPyB: {
                "dataCollectionGroupId": 0,
                "experimentType": "string",
                "blSampleId": 0,
                "sessionId": 0,
                "workflowId": 0
            }
        """
        return self.client.post("datacollections/group", json=group_data)

    def _update_data_collection(self, mx_collection: dict) -> tuple[int, int]:
        """Updates data collection in PyISPyB.

        Args:
            mx_collection: A dictionary containing data collection information.
                Expected to contain "collection_id" key.

        Returns:
            Tuple containing data collection id and data collection group id.
        """
        dc_id, dc_group_id = 0, 0
        if "collection_id" in mx_collection:
            group_id = self._store_data_collection_group(mx_collection)[
                "dataCollectionGroupId"
            ]
            try:
                dc_id, dc_group_id, *_ = self.client.post(
                    "datacollections/datacollection",
                    json={**mx_collection, "group_id": group_id},
                )
            except PyISPyBUnsuccessfulResponse:
                self.logger.exception("Error in _update_data_collection")
        else:
            self.logger.error(
                "Error in _update_data_collection: collection-id missing, "
                "the PyISPyB data-collection is not updated."
            )
        return dc_id, dc_group_id

    def store_image(self, image_dict: dict) -> int:
        """Stores a data collection image in PyISPyB.

        Args:
            image_dict: A dictionary containing image information (paths and properties
                of data collection). Expected to contain "dataCollectionId" key.

        Returns:
            The id of the stored image. 0 if failed or dataCollectionId is missing.
        """
        self.logger.info("Storing image in LIMS")
        image_id = 0
        if "dataCollectionId" in image_dict:
            try:
                response = self.client.post("images/image", json=image_dict)
                self.logger.debug("PyISPYB store image response: %s", response)
                image_id = response["imageId"]
            except PyISPyBUnsuccessfulResponse:
                self.logger.exception("Exception in store_image")
            else:
                self.logger.info("Storing image in LIMS completed, id : %s", image_id)
        else:
            self.logger.error(
                "Error in store_image: data_collection_id missing, "
                "could not store image in LIMS"
            )
        return image_id

    def get_samples(self, proposal_id: int) -> list[dict]:
        """Fetches samples for the given proposal id from PyISPyB."""
        try:
            proposal = self.__find_proposal_by_id(proposal_id)

            return self.client.get(
                "samples?proposal=%s%s&beamLineName=%s"
                % (proposal.code, proposal.number, self.beamline_name),
                timeout=10,
            )
        except PyISPyBUnsuccessfulResponse:
            self.logger.exception("Error in get_samples")
            return []

    def store_robot_action(self, robot_action: dict) -> int:
        """Stores robot action.

        Args:
            robot_action: A dictionary containing robot action information.
                Expected to contain "sampleId" key.

        Returns:
            The id of the robot action. 0 if failed or required keys are missing.
        """
        self.logger.info("Storing robot actions in LIMS")
        robot_action_id = 0
        try:
            robot_action["blSampleId"] = robot_action.pop("sampleId")
        except KeyError:
            self.logger.exception(
                "Error in store_robot_action: missing required keys in robot_action"
                "dictionary, could not store robot action in LIMS"
            )
        else:
            robot_action["startTimestamp"] = robot_action.pop("startTime", "")
            robot_action["endTimestamp"] = robot_action.pop("endTime", "")
            try:
                robot_action_id = self.client.post(
                    "events/robot-action", json=robot_action
                )
            except PyISPyBUnsuccessfulResponse:
                self.logger.exception("Exception in store_robot_action")
        return robot_action_id

    def associate_bl_sample_and_energy_scan(self, entry_dict: dict) -> int:
        """Associates bl sample and energy scan in PyISPyB.

        Args:
            entry_dict: A dictionary containing energy scan and bl sample information.

        Returns:
            The id of the association. -1 if association failed.
        """
        payload = {
            "energyScanId": entry_dict["energyScanId"],
            "blSampleId": entry_dict["blSampleId"],
        }
        try:
            assoc_id = self.client.patch(
                "events/energyscan/associate-bl-sample", json=payload
            )
        except Exception:
            self.logger.exception(
                "Failed to associate bl sample and energy scan in PyISPyB"
            )
            assoc_id = -1
        return assoc_id

    def get_data_collection(self, data_collection_id: int) -> dict:
        """Fetches data collection details from PyISPyB.

        Args:
            data_collection_id: The id of the data collection to fetch.

        Returns:
            Dictionary containing data collection details or empty if fetching failed.
        """
        try:
            dc = self.client.get(f"datacollections/{data_collection_id}")
        except Exception:
            self.logger.exception("Failed to get data collection from PyISPyB")
            return {}
        if not dc:
            return {}
        dc["startTime"] = datetime.fromisoformat(dc["startTime"]).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        dc["endTime"] = datetime.fromisoformat(dc["endTime"]).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return dc

    def find_detector(
        self,
        manufacturer,
        model,
        mode,
        type="",  # noqa: A002
    ) -> dict | None:
        """Finds detector by its type, manufacturer, model and mode.

        Gives the first matching detector or None if no match is found.
        Args:
            manufacturer: The manufacturer of the detector.
            model: The model of the detector.
            mode: The mode of the detector.
            type: The type of the detector (optional).

        Returns:
            A dictionary containing detector details.
        """
        try:
            return self.client.get(
                "detectors?manufacturer=%s&model=%s&mode=%s&type=%s"
                % (
                    manufacturer,
                    model,
                    mode,
                    type if type else "",
                )
            )
        except PyISPyBUnsuccessfulResponse:
            self.logger.exception("`Exception in find_detector")
            return None

    def update_session(self, session: dict) -> dict:
        """Updates Beamline Setup of existing session.

        Returns dictionary containing updated session details from PyISPyB.
        If updating failed, returns empty dictionary.
        """
        try:
            session_id = session["sessionId"]
            beamline_setup = session.get("BeamLineSetup") or {}
            beamline_setup_id = beamline_setup.get("beamLineSetupId")
            if not beamline_setup_id:
                msg = "Missing beamLineSetupId"
                raise KeyError(msg)
            return self.client.patch(
                "sessions/%s/associate-beamline-setup?beamLineSetupId=%s"
                % (
                    session_id,
                    beamline_setup_id,
                ),
            )
        except (PyISPyBUnsuccessfulResponse, KeyError):
            self.logger.exception("Failed to store or update session")
            return {}

    def get_session(self, session_id: int) -> dict:
        """Fetches session details from PyISPyB by session id."""
        try:
            session = self.client.get("sessions/%s" % session_id)
        except PyISPyBUnsuccessfulResponse:
            self.logger.exception("Failed to get session from PyISPyB")
            session = {}
        return session

    def store_beamline_setup(self, session_id: int, bl_config: dict) -> int | None:
        """
        Stores beamline setup in PyISPyB and associates it with the session.

        Args:
            session_id: The id of the session to associate the beamline setup with.
            bl_config: A dictionary containing beamline setup information.
        Returns:
            The id of the stored beamline setup. None if failed."""
        beamline_setup_id = None
        session = self.get_session(session_id)
        if session:
            try:
                beamline_setup_id = self.client.post(
                    "beamline-setups/beamline-setup", json=bl_config
                )
            except PyISPyBUnsuccessfulResponse:
                self.logger.exception(
                    "Failed to store or update beamline setup in PyISPyB"
                )
            bl_config["beamlineSetupId"] = beamline_setup_id
            session["BeamLineSetup"] = bl_config
            self.update_session(session)
        return beamline_setup_id

    def store_data_collection(self, mx_collection, bl_config=None):
        self.logger.info("Storing datacollection in PyISPyB")
        return self._store_data_collection(mx_collection, bl_config)

    def update_data_collection(self, mx_collection):
        self.logger.info("Updating datacollection in PyISPyB")
        return self._update_data_collection(mx_collection)

    def finalize_data_collection(self, mx_collection):
        return self.update_data_collection(mx_collection)

    def _store_data_collection(self, mx_collection: dict, bl_config: dict | None):
        """Stores data collection group in PyISPyB and returns the group id.

        Args:
            mx_collection: A dictionary containing data collection information.
            bl_config: A dictionary containing beamline setup information (optional).

        Returns:
            Store data collection id and detector id if found, otherwise 0.
        """
        detector_id = 0
        if bl_config:
            bl_config["synchrotronMode"] = bl_config.get(
                "synchrotronMode", mx_collection.get("synchrotronMode", "")
            )
            self.store_beamline_setup(mx_collection["sessionId"], bl_config)
            detector = self.find_detector(
                bl_config.get("detector_manufacturer", ""),
                bl_config.get("detector_model", ""),
                bl_config.get("detector_binning_mode", ""),
                bl_config.get("detector_type", ""),
            )
            if detector:
                detector_id = detector.get("detectorId", 0)

        response = self.client.post(
            "datacollections/datacollection",
            json={**mx_collection, "detectorId": detector_id}
            if detector_id
            else mx_collection,
        )
        collection_id = response["dataCollectionId"]
        return collection_id, detector_id

    def store_energy_scan(self, energyscan: dict) -> dict[str, int]:
        """Stores energy scan in PyISPyB

        Args:
            energyscan: A dictionary containing energy scan information.

        Returns:
            Dictionary {"energyScanId": number}, where number is the id of the stored
            energy scan.
        """
        try:
            return {
                "energyScanId": self.client.post("events/energyscan", json=energyscan)
            }

        except PyISPyBUnsuccessfulResponse:
            self.logger.exception("Failed to store energy scan in PyISPyB")
            return {"energyScanId": -1}

    def store_xfe_spectrum(self, xfe_spectrum: dict) -> dict[str, int]:
        """Stores XFE fluorescence spectrum in PyISPyB

        Args:
            xfe_spectrum: A dictionary containing XFE fluorescence spectrum information.

        Returns:
            Dictionary {"xfeFluorescenceSpectrumId": number}, where number is the id
            of the stored XFE fluorescence spectrum.
        """
        try:
            return {
                "xfeFluorescenceSpectrumId": self.client.post(
                    "events/xfe-fluorescence-spectrum", json=xfe_spectrum
                )
            }
        except PyISPyBUnsuccessfulResponse:
            self.logger.exception(
                "Failed to store XFE fluorescence spectrum in PyISPyB"
            )
            return {"xfeFluorescenceSpectrumId": -1}

    def update_bl_sample(self, bl_sample: dict) -> dict:
        """Updates beamline sample in PyISPyB.

        Args:
            bl_sample: A dictionary containing beamline sample information.
                Expected to contain "blSampleId" key.
        Returns:
            Response from PyISPyB - a dictionary containing updated beamline sample
            details or empty if updating failed.
        """
        try:
            bl_sample_id = bl_sample.get("blSampleId")
            if bl_sample_id is None:
                self.logger.error("Missing blSampleId")
                return {}
            return self.client.patch("samples/%s" % bl_sample_id, json=bl_sample)
        except PyISPyBUnsuccessfulResponse:
            self.logger.exception("Failed to update beamline sample in PyISPyB")
        return {}
