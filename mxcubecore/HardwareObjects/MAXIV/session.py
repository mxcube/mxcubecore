"""MAXIV Session hardware object."""

import time
from pathlib import Path

from sdm import storage

import mxcubecore.HardwareObjects.Session
from mxcubecore.model.queue_model_objects import PathTemplate


class Session(mxcubecore.HardwareObjects.Session.Session):
    def init(self):
        super().init()
        self.is_commissioning = False

        # We initialize with an empty archive_folder,
        # to be set once proposal is selected.
        PathTemplate.set_archive_path(self.base_archive_directory, "")

    def set_in_commissioning(self, proposal_info):
        self.proposal_code = proposal_info["Proposal"]["code"]
        self.proposal_number = proposal_info["Proposal"]["number"]
        self.is_commissioning = True

    def get_proposal(self) -> str:
        """
        Returns:
            The proposal, 'local-user' if no proposal is available
        """
        proposal = "local-user"

        if self.proposal_code and self.proposal_number:
            if self.proposal_code == "ifx":
                self.proposal_code = "fx"

            proposal = str(self.proposal_number)

        return proposal

    def get_base_data_directory(self) -> str:
        """Get base data directory.

        Figure out the base data directory taking the 'contextual'
        information into account, such as if the current user
        is in-house.

        Returns:
            The base data path.
        """
        # /data/(user-type)/(beamline)/(proposal)/(visit)/raw
        if self.session_start_date:
            start_time = self.session_start_date.split(" ")[0].replace("-", "")
        else:
            start_time = time.strftime("%Y%m%d")
        _proposal = self.get_proposal()

        if not self.is_commissioning:
            if self.is_proprietary():
                directory = Path(
                    self.base_directory,
                    "proprietary",
                    self.beamline_name.lower(),
                    _proposal,
                    start_time,
                )
            else:
                directory = Path(
                    self.base_directory,
                    "visitors",
                    self.beamline_name.lower(),
                    _proposal,
                    start_time,
                )
        else:
            # /data/staff/biomax/commissioning/date
            directory = Path(
                self.base_directory,
                "staff",
                self.beamline_name.lower(),
                "commissioning",
                time.strftime("%Y%m%d"),
            )

        self.log.info(
            "Data directory for proposal %s: %s",
            self.get_proposal(),
            directory,
        )

        return str(directory)

    def prepare_directories(self, session):
        self.log.info("Preparing Data directory for session: %s", session)
        start_date = session.start_datetime.date().isoformat().replace("-", "")
        self.set_session_start_date(start_date)

        self.log.info("Preparing Data directory for proposal %s", self.get_proposal())
        if self.is_commissioning:
            category = "staff"
        elif self.is_proprietary():
            category = "proprietary"
        else:
            category = "visitors"

        try:
            self.storage = storage.Storage(
                user_type=category, beamline=self.endstation_name
            )
        except Exception:
            self.log.exception("error setting up SDM")

        # This creates the path for the data and ensures proper permissions
        # e.g. /data/visitors/biomax/<proposal>/<visit>/{raw, process}
        if self.is_commissioning:
            group = self.beamline_name.lower()
        else:
            group = self.storage.get_proposal_group(session.number)
        try:
            _raw_path = self.storage.create_path(
                session.number, group, self.get_session_start_date()
            )

            self.log.info("SDM Data directory created: %s", _raw_path)
        except Exception as exc:  # noqa: BLE001
            self.log.warning("SDM Data directory creation failed. %s", exc)
            self.log.info("SDM Data directory trying to create again after failure")
            time.sleep(0.1)
            try:
                _raw_path = self.storage.create_path(
                    session.number, group, self.get_session_start_date()
                )

                self.log.info("SDM Data directory created: %s", _raw_path)
            except Exception:
                self.log.exception("SDM Data directory creation failed.")
                raise

        if self.base_archive_directory:
            archive_folder = "{}/{}".format(category, self.beamline_name.lower())
            PathTemplate.set_archive_path(self.base_archive_directory, archive_folder)
            _archive_path = Path(self.base_archive_directory, archive_folder)
            self.log.info("Archive directory configured: %s", _archive_path)

    def is_proprietary(self) -> bool:
        """Determines if current proposal is considered to be proprietary.

        Returns:
            True if the proposal is proprietary, otherwise False.
        """
        return self.proposal_code == "IN"

    def clear_session(self):
        self.session_id = None
        self.proposal_code = None
        self.proposal_number = None
        self.proposal_id = None
        self.is_commissioning = False
