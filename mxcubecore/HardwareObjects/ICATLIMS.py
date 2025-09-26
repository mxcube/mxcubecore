import json
import logging
import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional
from zoneinfo import ZoneInfo

import requests
from pyicat_plus.client.main import IcatClient

if TYPE_CHECKING:
    from pyicat_plus.client.models.session import Session as ICATSession

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractLims import AbstractLims
from mxcubecore.model.lims_session import (
    Download,
    Lims,
    LimsSessionManager,
    SampleInformation,
    SampleSheet,
    Session,
)

logger = logging.getLogger("HWR")


class ICATLIMS(AbstractLims):
    """
    ICAT+ client.
    """

    def __init__(self, name):
        super().__init__(name)
        HardwareObject.__init__(self, name)
        self.investigations = None
        self.icatClient = None
        self.lims_rest = None
        self.ingesters = None

    def init(self):
        self.url = self.get_property("ws_root")
        self.ingesters = self.get_property("queue_urls")
        self.investigations = []
        self.samples = []

        # Initialize ICAT client
        self.icatClient = IcatClient(
            icatplus_restricted_url=self.url,
            metadata_urls=["bcu-mq-01:61613"],
            reschedule_investigation_urls=["bcu-mq-01:61613"],
        )

    def get_lims_name(self) -> List[Lims]:
        return [
            Lims(name="DRAC", description="Data Repository for Advancing open sCience"),
        ]

    def login(
        self,
        user_name: str,
        password: str,
        session_manager: Optional[LimsSessionManager],
    ) -> LimsSessionManager:
        msg = f"authenticate {user_name}"
        logger.debug(msg)

        self.icat_session: ICATSession = self.icatClient.do_log_in(password)

        if self.icatClient is None or self.icatClient is None:
            msg = "Error initializing icatClient: "
            msg += f"icatClient={self.url}"
            logger.error(msg)
            raise RuntimeError("Could not initialize icatClient")

        # Connected to metadata icatClient
        msg = "Connected succesfully to icatClient: "
        msg += f"fullName={self.icat_session['fullName']}, url={self.url}"
        logger.debug(msg)

        # Retrieving user's investigations
        sessions = self.to_sessions(self.__get_all_investigations())

        if len(sessions) == 0:
            msg = f"No sessions available for user {user_name}"
            raise RuntimeError(msg)

        msg = f"Successfully retrieved {len(sessions)} sessions"
        logger.debug(msg)

        # This is done because ICATLims can be used standalone or from ESRFLims
        if session_manager is not None:
            self.session_manager = session_manager

        # Check if there is currently a session in use and if user have
        # access to that session
        if self.session_manager.active_session:
            session_found = False
            session_id = self.session_manager.active_session.session_id
            for session in sessions:
                if session.session_id == session_id:
                    session_found = True
                    break

            if not session_found:
                msg = f"Current session in-use (with id {session_id}) "
                msg += f"not avaialble for user {user_name}"
                raise RuntimeError(msg)

        return self.session_manager, self.icat_session["name"], sessions

    def is_user_login_type(self) -> bool:
        return True

    def get_proposals_by_user(self, user_name):
        msg = f"get_proposals_by_user {user_name}\n"
        msg += f"[ICATCLient] Read {len(self.lims_rest.investigations)} investigations"
        logger.debug(msg)

        return self.lims_rest.to_sessions(self.lims_rest.investigations)

    def _get_loaded_pucks(self, parcels) -> list:
        """Retrieve all pucks from the parcels that have a defined
            'sampleChangerLocation'.
            A puck is considered "loaded" if it contains the key
            'sampleChangerLocation'.
            Iterates through all parcels and collects such pucks.
        Returns:
            A list of pucks (dicts) that have 'sampleChangerLocation' defined.
        """
        loaded_pucks = []

        if parcels:
            for parcel in parcels:
                pucks = parcel.get("content", [])
                for puck in pucks:
                    if "sampleChangerLocation" in puck:
                        # Add information about the parcel
                        puck["parcelName"] = parcel.get("name")
                        puck["parcelId"] = parcel.get("id")
                        loaded_pucks.append(puck)

        return loaded_pucks

    def get_samples(self, lims_name: str) -> list:
        """Retrieve and process sample information from LIMS based on the
            provided name:
            - Retrieves parcel data (containers like UniPucks or SpinePucks).
            - Retrieves sample sheet data.
            - Identifies and processes only loaded pucks
              (those with a 'sampleChangerLocation').
            - Converts each sample in the pucks into internal queue samples
              using `__to_sample`.
        Args:
            The LIMS name or identifier used to fetch sample-related data.

        Returns:
            A list of processed sample objects ready for queuing.
        """

        self.samples = []

        try:
            session = self.session_manager.active_session
            logger.debug(
                "[ICATClient] get_samples: session_id=%s, proposal_name=%s",
                session.session_id,
                session.proposal_name,
            )

            # Load parcels (pucks)
            self.parcels = self.get_parcels()

            # Load sample sheets
            self.sample_sheets = self.get_samples_sheets()
            logger.debug(
                "[ICATClient] %d sample sheets retrieved", len(self.sample_sheets)
            )

            # Filter for loaded pucks
            self.loaded_pucks = self._get_loaded_pucks(self.parcels)
            msg = f"[ICATClient] {len(self.loaded_pucks)} loaded pucks found"
            logger.debug(msg)

            # Extract and process samples from loaded pucks
            for puck in self.loaded_pucks:
                tracking_samples = puck.get("content", [])
                puck_name = puck.get("name", "Unnamed")
                location = puck.get("sampleChangerLocation", "Unknown")
                msg = f"[ICATClient] Found puck {puck_name} at position "
                msg += f"{location}, containing {len(tracking_samples)} samples"
                logger.debug(msg)
                for tracking_sample in tracking_samples:
                    sample = self.__to_sample(tracking_sample, puck, self.sample_sheets)
                    self.samples.append(sample)
        except RuntimeError:
            logger.exception("[ICATClient] Error retrieving samples: %s")
        else:
            msg = f"[ICATClient] Total {len(self.samples)} samples read"
            logger.debug(msg)
            return self.samples
        return []

    def get_sample_sheet_by_id(
        self, samples: List[SampleSheet], sample_id: int
    ) -> Optional[SampleSheet]:
        """
        Retrieve a sample sheet by its unique ID.

        Args:
            samples (List[SampleSheet]): A list of Sample objects.
            sample_id (int): The unique identifier of the sample sheet to retrieve.

        Returns:
            Optional[Sample]: The Sample object if found, otherwise None.
        """
        return next((sample for sample in samples if sample.id == sample_id), None)

    def objectid_to_int(self, oid_str):
        return int(oid_str, 16)

    def int_to_objectid(self, i):
        return hex(i)[2:].zfill(24)

    def __add_download_path_to_processing_plan(
        self, processing_plan, downloads: List[Download]
    ):
        # Build a lookup for file_path by filename
        file_path_lookup = {d.filename: d.path for d in downloads}
        group_paths = defaultdict(list)
        for d in downloads:
            if d.groupName is not None:
                group_paths[d.groupName].append(d.path)

        # Enrich the processing_plan
        for item in processing_plan:
            if item["key"] == "Advanced_processing":
                for pipeline in item["value"]:
                    # Update reference
                    ref = pipeline.get("reference")
                    if ref in file_path_lookup:
                        pipeline["reference"] = {"filepath": file_path_lookup[ref]}

                    # Update search_models
                    if "search_models" in pipeline:
                        models = json.loads(pipeline["search_models"])
                        for model in models:
                            group = model.get("pdb_group")
                            if group in group_paths:
                                model["file_paths"] = group_paths[group]
                        pipeline["search_models"] = models

    def _safe_json_loads(self, json_str):
        try:
            return json.loads(json_str)
        except Exception:
            return str(json_str)

    def __to_sample(
        self, tracking_sample: dict, puck: dict, sample_sheets: List[SampleSheet]
    ) -> dict:
        """
        Convert a tracking sample and associated metadata into the internal
        sample data structure.
        - Extracts relevant sample metadata.
        - Resolves protein acronym from the sample sheet if available.
        - Maps experiment plan details into a diffraction plan dictionary.
        - Assembles all relevant fields into a structured sample dictionary.

        Args:
            tracking_sample (dict): The raw sample data from tracking.
            puck (dict): The puck (container) metadata associated with the sample.
            sample_sheets (List[SampleSheet]): List of sample sheets used for lookup.

        Returns:
            dict: A dictionary representing the standardized internal sample format.
        """
        # Basic identifiers
        sample_name = str(tracking_sample.get("name"))

        # MXCuBE needs to be an integer while in DRAC is a ObjectId
        # Mongo @BES needs to be smaller then 8 bytes
        sample_id = int(str(self.objectid_to_int(tracking_sample.get("id")))[-6:])
        # id to the sample sheet declared in the user portal
        sample_sheet_id = tracking_sample.get("sampleId")
        # identifier that points to the sample tracking
        tracking_sample_id = tracking_sample.get("_id")

        msg = f"[ICATClient] Sample ids sample_id={sample_id} "
        msg += f"sample_sheet_id={sample_sheet_id} "
        msg += f"tracking_sample_id={tracking_sample_id}"
        logger.debug(msg)

        sample_location = tracking_sample.get("sampleContainerPosition")
        puck_location = str(puck.get("sampleChangerLocation", "Unknown"))
        puck_name = puck.get("name", "UnknownPuck")
        parcel_name = puck.get("parcelName")
        parcel_id = puck.get("parcelId")
        # Determine protein acronym using sample sheet if available
        protein_acronym = sample_name  # Default fallback

        sample_sheet = self.get_sample_sheet_by_id(sample_sheets, sample_sheet_id)
        if sample_sheet:
            protein_acronym = sample_sheet.name

        # This converts to key-value pairs
        experiment_plan = {
            item["key"]: item["value"]
            for item in tracking_sample.get("experimentPlan", {})
        }

        processing_plan = tracking_sample.get("processingPlan", [])
        downloads: List[Download] = []
        if processing_plan:
            for item in processing_plan:
                # when possible this converts the string to json
                item["value"] = self._safe_json_loads(item["value"])

            sample_information = None
            try:
                sample_information: SampleInformation = (
                    self.__get_sample_information_by(sample_sheet_id)
                )
                if sample_information is not None:
                    if len(HWR.beamline.session.get_full_path("", "")) > 0:
                        destination_folder = HWR.beamline.session.get_full_path("", "")[
                            0
                        ]
                        msg = "Download restource: "
                        msg += f"sample_sheet_id={sample_sheet_id} "
                        msg += f"destination_folder={destination_folder}"
                        logger.debug(msg)
                        downloads = self._download_resources(
                            sample_sheet_id,
                            sample_information.resources,
                            destination_folder,
                            sample_name,
                        )
                        msg = f"downloaded {len(downloads)} resources"
                        logger.debug(msg)
                        if len(downloads) > 0:
                            try:
                                self.__add_download_path_to_processing_plan(
                                    processing_plan, downloads
                                )
                            except RuntimeError:
                                logger.exception(
                                    "Failed __add_download_path_to_processing_plan"
                                )

                processing_plan = {
                    item["key"]: item["value"] for item in processing_plan
                }

            except RuntimeError as e:
                msg = f"error getting sample information {e}"
                logger.warning(msg)

        comments = tracking_sample.get("comments")

        return {
            "sampleName": sample_name,
            "sampleId": sample_id,
            "sample_sheet_id": sample_sheet_id,
            "trackingSampleId": tracking_sample_id,
            "proteinAcronym": protein_acronym,
            "sampleLocation": sample_location,
            "containerCode": puck_name,
            "containerSampleChangerLocation": puck_location,
            "SampleTrackingParcel_name": parcel_name,
            "SampleTrackingParcel_id": parcel_id,
            "SampleTrackingContainer_id": puck_name,
            "SampleTrackingContainer_name": parcel_id,
            "smiles": None,  # Placeholder for future chemical structure info
            "experimentType": experiment_plan.get("workflowType"),
            "crystalSpaceGroup": experiment_plan.get("forceSpaceGroup"),
            "diffractionPlan": {
                # "diffractionPlanId": 457980, TODO: do we need this?
                "experimentKind": experiment_plan.get("experimentKind"),
                "numberOfPositions": experiment_plan.get("numberOfPositions"),
                "observedResolution": experiment_plan.get("observedResolution"),
                "preferredBeamDiameter": experiment_plan.get("preferredBeamDiameter"),
                "radiationSensitivity": experiment_plan.get("radiationSensitivity"),
                "requiredCompleteness": experiment_plan.get("requiredCompleteness"),
                "requiredMultiplicity": experiment_plan.get("requiredMultiplicity"),
                "requiredResolution": experiment_plan.get("requiredResolution"),
            },
            "cellA": experiment_plan.get("unit_cell_a"),
            "cellB": experiment_plan.get("unit_cell_b"),
            "cellC": experiment_plan.get("unit_cell_c"),
            "cellAlpha": experiment_plan.get("unit_cell_alpha"),
            "cellBeta": experiment_plan.get("unit_cell_beta"),
            "cellGamma": experiment_plan.get("unit_cell_gamma"),
            "experimentPlan": experiment_plan,
            "processingPlan": processing_plan,
            "comments": comments,
        }

    def create_session(self, session_dict):
        pass

    def _store_data_collection_group(self, group_data):
        pass

    @property
    def only_staff_session_selection(self) -> bool:
        return bool(
            self.get_property("only_staff_session_selection", default_value=False)
        )

    def store_robot_action(self, proposal_id: str):
        raise NotImplementedError

    @property
    def filter(self):
        return self.get_property("filter", None)

    @property
    def override_beamline_name(self):
        return self.get_property(
            "override_beamline_name", HWR.beamline.session.beamline_name
        )

    @property
    def compatible_beamlines(self):
        return self.get_property(
            "compatible_beamlines", HWR.beamline.session.beamline_name
        )

    @property
    def data_portal_url(self):
        return self.get_property("data_portal_url", None)

    @property
    def user_portal_url(self):
        return self.get_property("user_portal_url", None)

    @property
    def logbook_url(self):
        return self.get_property("logbook_url", None)

    @property
    def before_offset_days(self):
        return self.get_property("before_offset_days", "1")

    @property
    def after_offset_days(self):
        return self.get_property("after_offset_days", "1")

    def _string_to_format_date(self, date: str, fmt: str) -> str:
        if date is not None:
            date_time = self._tz_aware_fromisoformat(date)
            if date_time is not None:
                return date_time.strftime(fmt)
        return ""

    def _string_to_date(self, date: str) -> str:
        return self._string_to_format_date(date, "%Y%m%d")

    def _string_to_time(self, date: str) -> str:
        return self._string_to_format_date(date, "%H:%M:%S")

    def _tz_aware_fromisoformat(self, date: str) -> datetime:
        try:
            return datetime.fromisoformat(date).astimezone()
        except (TypeError, ValueError):
            return None

    def set_active_session_by_id(self, session_id: str) -> Session:
        logger.debug(f"set_active_session_by_id: {session_id}")

        if self.is_session_already_active(self.session_manager.active_session):
            return self.session_manager.active_session

        sessions = self.session_manager.sessions

        logger.debug(f"Sessions: {len(sessions)}")

        if len(sessions) == 0:
            logger.warning("Session list is empty. No session candidates")
            raise RuntimeError("No sessions available")

        if len(sessions) == 1:
            self.session_manager.active_session = sessions[0]
            logger.debug(
                "Session list contains a single session. proposal_name=%s",
                self.session_manager.active_session.proposal_name,
            )
            return self.session_manager.active_session

        session_list = [obj for obj in sessions if obj.session_id == session_id]
        if len(session_list) != 1:
            raise RuntimeError(
                "Session not found in the local list of sessions. session_id="
                + session_id
            )
        self.session_manager.active_session = session_list[0]
        return self.session_manager.active_session

    def allow_session(self, session: Session):
        self.active_session = session
        logger.debug("allow_session investigationId=%s", session.session_id)
        self.icatClient.reschedule_investigation(session.session_id)

    def get_session_by_id(self, sid: str):
        msg = f"get_session_by_id investigationId={sid} "
        msg += f"investigations={len(self.investigations)}"
        logger.debug(msg)

        investigation_list = list(filter(lambda p: p["id"] == sid, self.investigations))
        if len(investigation_list) == 1:
            self.investigation = investigation_list[0]
            return self.__to_session(investigation_list[0])

        logger.warning("No investigation found")
        return None

    def __get_all_investigations(self):
        """Returns all investigations by user. An investigation corresponds to
        one experimental session. It returns an empty array in case of error"""
        self.investigations = []
        try:
            msg = f"__get_all_investigations before={self.before_offset_days} "
            msg += f"after={self.after_offset_days} "
            msg += f"beamline={self.override_beamline_name} "
            msg += (
                f"isInstrumentScientist={self.icat_session['isInstrumentScientist']} "
            )
            msg += f"isAdministrator={self.icat_session['isAdministrator']} "
            msg += f"compatible_beamlines={self.compatible_beamlines}"
            logger.debug(msg)

            if self.icat_session is not None and (
                self.icat_session["isAdministrator"]
                or self.icat_session["isInstrumentScientist"]
            ):
                # Setting up of the session done by admin or staff
                self.investigations = self.icatClient.get_investigations_by(
                    start_date=datetime.today()
                    - timedelta(days=float(self.before_offset_days)),
                    end_date=datetime.today()
                    + timedelta(days=float(self.after_offset_days)),
                    instrument_name=self.compatible_beamlines,
                )
            elif self.only_staff_session_selection:
                if self.session_manager.active_session is None:
                    # print warning an return no investigations
                    # if no session selected and only staff is allowed
                    logger.warning(
                        "No session selected. Only staff can select a session"
                    )
                    return []

                self.investigations = self.icatClient.get_investigations_by(
                    ids=[self.session_manager.active_session.session_id]
                )
            else:
                self.investigations = self.icatClient.get_investigations_by(
                    filter=self.filter,
                    instrument_name=self.compatible_beamlines,
                    start_date=datetime.today()
                    - timedelta(days=float(self.before_offset_days)),
                    end_date=datetime.today()
                    + timedelta(days=float(self.after_offset_days)),
                )
        except Exception:
            self.investigations = []
            logger.exception("Failed on __get_all_investigations")
        else:
            msg = "__get_all_investigations retrieved "
            msg += f"{len(self.investigations)} investigations"
            logger.debug(msg)

        return self.investigations

    def __get_proposal_number_by_investigation(self, investigation):
        """
        Given an investigation it returns the proposal number.
        Example: investigation["name"] = "MX-1234"
        returns: 1234

        TODO: this might not work for all type of proposals (example: TEST proposals)
        """
        return (
            investigation["name"]
            .replace(investigation["type"]["name"], "")
            .replace("-", "")
        )

    def _get_data_portal_url(self, investigation):
        try:
            return (
                self.data_portal_url.replace("{id}", str(investigation["id"]))
                if self.data_portal_url is not None
                else ""
            )
        except Exception:
            return ""

    def _get_logbook_url(self, investigation):
        try:
            return (
                self.logbook_url.replace("{id}", str(investigation["id"]))
                if self.logbook_url is not None
                else ""
            )
        except Exception:
            return ""

    def _get_user_portal_url(self, investigation):
        try:
            return (
                self.user_portal_url.replace(
                    "{id}", str(investigation["parameters"]["Id"])
                )
                if self.user_portal_url is not None
                and investigation["parameters"]["Id"] is not None
                else ""
            )
        except Exception:
            return ""

    def __get_investigation_parameter_by_name(
        self, investigation: dict, parameter_name: str
    ) -> str:
        """
        Gets the metadata of the parameters in an investigation
        Returns the value of the specified parameter if it exists,
        otherwise returns an empty string.
        """
        return investigation.get("parameters", {}).get(parameter_name, None)

    def __to_session(self, investigation) -> Session:
        """This methods converts a ICAT investigation into a session"""

        actual_start_date = (
            investigation["parameters"]["__actualStartDate"]
            if "__actualStartDate" in investigation["parameters"]
            else investigation["startDate"]
        )
        actual_end_date = (
            investigation["parameters"]["__actualEndDate"]
            if "__actualEndDate" in investigation["parameters"]
            else investigation.get("endDate", None)
        )

        instrument_name = investigation["instrument"]["name"]

        # If session has been rescheduled new date is overwritten
        return Session(
            code=investigation["type"]["name"],
            number=self.__get_proposal_number_by_investigation(investigation),
            title=f"{investigation['title']}",
            session_id=investigation["id"],
            proposal_id=investigation["id"],
            proposal_name=investigation["name"],
            beamline_name=instrument_name,
            comments="",
            start_datetime=investigation.get(
                "startDate", None
            ),  # self._string_to_date(investigation.get("startDate", None)),
            start_date=self._string_to_date(investigation.get("startDate", None)),
            start_time=self._string_to_time(investigation.get("startDate", None)),
            end_datetime=investigation.get("endDate", None),
            end_date=self._string_to_date(
                investigation.get("endDate", None)
            ),  # self._string_to_time(investigation.get("endDate", None)),
            end_time=self._string_to_time(investigation.get("endDate", None)),
            actual_start_date=self._string_to_date(actual_start_date),
            actual_start_time=self._string_to_time(actual_start_date),
            actual_end_date=self._string_to_date(actual_end_date),
            actual_end_time=self._string_to_time(actual_end_date),
            nb_shifts=3,
            scheduled=self.is_scheduled_on_host_beamline(instrument_name),
            is_scheduled_time=self.is_scheduled_now(actual_start_date, actual_end_date),
            is_scheduled_beamline=self.is_scheduled_on_host_beamline(instrument_name),
            data_portal_URL=self._get_data_portal_url(investigation),
            user_portal_URL=self._get_user_portal_url(investigation),
            logbook_URL=self._get_logbook_url(investigation),
            is_rescheduled=bool("__actualEndDate" in investigation["parameters"]),
            volume=self.__get_investigation_parameter_by_name(
                investigation, "__volume"
            ),
            sample_count=self.__get_investigation_parameter_by_name(
                investigation, "__sampleCount"
            ),
            dataset_count=self.__get_investigation_parameter_by_name(
                investigation, "__datasetCount"
            ),
        )

    def get_full_user_name(self):
        return self.icat_session["fullName"]

    def get_user_name(self):
        return self.icat_session["username"]

    def to_sessions(self, investigations):
        return [self.__to_session(investigation) for investigation in investigations]

    def get_parcels(self):
        """Returns the parcels associated to an investigation"""
        try:
            session_id = self.session_manager.active_session.session_id
            msg = f"Retrieving parcels by investigation_id {session_id}"
            logger.debug(msg)
            parcels = self.icatClient.get_parcels_by(session_id)
        except Exception:
            logger.exception("Failed on get_parcels_by_investigation_id")
        else:
            msg = f"Successfully retrieved {len(parcels)} parcels"
            logger.debug(msg)
            return parcels

        return []

    def get_samples_sheets(self) -> List[SampleSheet]:
        """Returns the samples sheets associated to an investigation"""
        try:
            msg = "Retrieving samples by investigation_id "
            msg += f"{self.session_manager.active_session.session_id}"
            logger.debug(msg)
            samples = self.icatClient.get_samples_by(
                self.session_manager.active_session.session_id
            )
        except Exception:
            logger.exception("Failed on get_samples_by_investigation_id")
        else:
            msg = f"Successfully retrieved {len(samples)} samples"
            logger.debug(msg)
            # Convert to object
            return [SampleSheet.parse_obj(sample) for sample in samples]
        return []

    def echo(self):
        """Mockup for the echo method."""
        return True

    def is_connected(self):
        return self.login_ok

    def add_beamline_configuration_metadata(self, metadata, beamline_config):
        """
        This is the mapping betweeh the beamline_config dict and the ICAt keys
        in case they exist then they will be added to the metadata of the dataset
        """
        if beamline_config is not None:
            key_mapping = {
                "detector_px": "InstrumentDetector01_beam_center_x",
                "detector_py": "InstrumentDetector01_beam_center_y",
                "beam_divergence_vertical": "InstrumentBeam_vertical_incident_beam_divergence",
                "beam_divergence_horizontal": "InstrumentBeam_horizontal_incident_beam_divergence",
                "polarisation": "InstrumentBeam_final_polarization",
                "detector_model": "InstrumentDetector01_model",
                "detector_manufacturer": "InstrumentDetector01_manufacturer",
                "synchrotron_name": "InstrumentSource_name",
                "monochromator_type": "InstrumentMonochromatorCrystal_type",
                "InstrumentDetector01_type": "detector_type",
            }

            for config_key, metadata_key in key_mapping.items():
                if hasattr(beamline_config, config_key):
                    metadata[metadata_key] = getattr(beamline_config, config_key)

    def find_sample_by_sample_id(self, sample_id):
        return next(
            (
                sample
                for sample in self.samples
                if str(sample["limsID"]) == str(sample_id)
            ),
            None,
        )

    def _get_sample_position(self) -> tuple:
        """Return the position of the puck in the samples changer
        and the position of the sample within the puck,
        """
        try:
            queue_entry = HWR.beamline.queue_manager.get_current_entry()
            sample_node = queue_entry.get_data_model().get_sample_node()
            location = sample_node.location  # Example: (8,2,5)

            if len(location) == 3:
                (cell, puck, sample_position) = location
            else:
                cell = 1
                (puck, sample_position) = location

            position = None
            if None not in (cell, puck):
                position = int(cell * 3) + int(puck)
        except Exception:
            logger.exception("Cannot retrieve sample position")
        return position, sample_position

    def store_beamline_setup(self, session_id: str, bl_config_dict: dict):
        pass

    def store_image(self, image_dict: dict):
        pass

    def store_common_data(self, datacollection_dict: dict) -> dict:
        """Fill in a dictionary with the common for all the
           data collection tecjniques meta data.
        Args:
            datacollection_dict(dict): dictionarry from the data collection.
        """
        sample_id = datacollection_dict.get("blSampleId")
        msg = f"SampleId is: {sample_id}"
        logging.getLogger("HWR").debug(msg)
        try:
            sample = HWR.beamline.lims.find_sample_by_sample_id(sample_id)
            sample_name = sample.get("sampleName")
        except (AttributeError, TypeError):
            sample_name = "unknown"
            msg = f"Sample {sample_id} not found"
            logging.getLogger("HWR").debug(msg)

        start_time = datacollection_dict.get("startTime", "")
        end_time = datacollection_dict.get("endTime", "")

        try:
            dt_aware = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=ZoneInfo("Europe/Paris")
            )
            dt_aware_end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=ZoneInfo("Europe/Paris")
            )

            start_time = dt_aware.isoformat(timespec="microseconds")
            end_time = dt_aware_end.isoformat(timespec="microseconds")
        except TypeError:
            logging.getLogger("HWR").exception("Cannot parse start and end time")
        bsx, bsy, shape, _ = HWR.beamline.beam.get_value()
        flux_end = datacollection_dict.get("flux_end") or HWR.beamline.flux.get_value()

        transmission = (
            datacollection_dict.get("transmission")
            or HWR.beamline.transmission.get_value()
        )

        energy = datacollection_dict.get("energy") or HWR.beamline.energy.get_value()
        wavelength = (
            datacollection_dict.get("wavelength")
            or HWR.beamline.energy.get_wavelength()
        )

        machine_info = HWR.beamline.machine_info.get_value()

        return {
            "sampleId": sample_id,
            "Sample_name": sample_name,
            "startDate": start_time,
            "endDate": end_time,
            "MX_beamShape": shape.value,
            "MX_beamSizeAtSampleX": bsx,
            "MX_beamSizeAtSampleY": bsy,
            "MX_xBeam": bsx,
            "MX_yBeam": bsy,
            "MX_flux": datacollection_dict.get("flux"),
            "MX_fluxEnd": flux_end,
            "MX_transmission": transmission,
            "InstrumentMonochromator_wavelength": wavelength,
            "InstrumentMonochromator_energy": energy,
            "InstrumentSource_current": machine_info.get("current"),
            "InstrumentSource_mode": machine_info.get("fill_mode"),
        }

    def store_energy_scan(self, energyscan_dict: dict):
        try:
            metadata = self.store_common_data(energyscan_dict)
            try:
                beamline = self._get_scheduled_beamline()
                msg = f"Dataset Beamline={beamline} "
                msg += f"Current Beamline={HWR.beamline.session.beamline_name}"
                logging.getLogger("HWR").info(msg)
            except Exception:
                logging.getLogger("HWR").exception(
                    "Failed to get _get_scheduled_beamline",
                )
            _session = HWR.beamline.session
            proposal = f"{_session.proposal_code}{_session.proposal_number}"

            directory = Path(energyscan_dict["scanFileFullPath"]).parent

            metadata.update(
                {
                    "scanType": "energy_scan",
                    "MX_directory": str(directory),
                    "MX_exposureTime": energyscan_dict.get("exposureTime"),
                    "InstrumentDetector01_model": energyscan_dict.get(
                        "fluorescenceDetector"
                    ),
                    "MX_element": energyscan_dict.get("element"),
                    "MX_edgeEnergy": energyscan_dict.get("edgeEnergy"),
                    "MX_startEnergy": energyscan_dict.get("startEnergy"),
                    "MX_endEnergy": energyscan_dict.get("endEnergy"),
                    "MX_peakEnergy": energyscan_dict.get("endEnergy"),
                    "MX_inflectioEnergy": energyscan_dict.get("inflectioEnergy"),
                    "MX_remoteEnergy": energyscan_dict.get("remoteEnergy"),
                    "MX_peakFPrime": energyscan_dict.get("peakFPrime"),
                    "MX_peakFDoublePrime": energyscan_dict.get("peakFDoublePrime"),
                    "MX_inflectionFPrime": energyscan_dict.get("inflectionFPrime"),
                    "MX_inflectionFDoublePrime": energyscan_dict.get(
                        "inflectionFDoublePrime"
                    ),
                    "MX_comments": energyscan_dict.get("comments"),
                }
            )

            self.icatClient.store_dataset(
                beamline=beamline,
                proposal=proposal,
                dataset=str(directory.name),
                path=str(directory),
                metadata=metadata,
            )
        except Exception:
            logging.getLogger("ispyb_client").exception()

    def store_xfe_spectrum(self, xfespectrum_dict: dict):
        status = {"xfeFluorescenceSpectrumId": -1}
        try:
            metadata = self.store_common_data(xfespectrum_dict)
            try:
                beamline = self._get_scheduled_beamline()
                msg = f"Dataset Beamline={beamline} "
                msg += f"Current Beamline={HWR.beamline.session.beamline_name}"
                logging.getLogger("HWR").info(msg)
            except Exception:
                logging.getLogger("HWR").exception(
                    "Failed to get _get_scheduled_beamline",
                )
            _session = HWR.beamline.session
            proposal = f"{_session.proposal_code}{_session.proposal_number}"

            directory = Path(xfespectrum_dict["filename"]).parent

            metadata.update(
                {
                    "scanType": "xrf",
                    "MX_directory": str(directory),
                    "MX_exposureTime": xfespectrum_dict.get("exposureTime"),
                }
            )

            self.icatClient.store_dataset(
                beamline=beamline,
                proposal=proposal,
                dataset=str(directory.name),
                path=str(directory),
                metadata=metadata,
            )
        except Exception:
            logging.getLogger("ispyb_client").exception()

        return status

    def store_workflow(self, workflow_dict: dict):
        pass

    def store_data_collection(self, datacollection_dict, beamline_config_dict=None):
        """Store the dictionary with the information about the beamline
        to be sent when a dataset is produced.
        """
        self.beamline_config = beamline_config_dict

    def update_data_collection(self, datacollection_dict: dict):
        """Update data collection."""

    def _get_oscillation_end(self, oscillation_sequence):
        return float(oscillation_sequence["start"]) + (
            float(oscillation_sequence["range"])
            - float(oscillation_sequence["overlap"])
        ) * float(oscillation_sequence["number_of_images"])

    def _get_rotation_axis(self, oscillation_sequence):
        if "kappaStart" in oscillation_sequence:
            if (
                oscillation_sequence["kappaStart"] != 0
                and oscillation_sequence["kappaStart"] != -9999
            ):
                return "Omega"
        return "Phi"

    def __get_sample_information_by(
        self, sample_id: str
    ) -> Optional[SampleInformation]:
        """
        Fetches sample metadata and associated resources based on the sample ID.

        Parameters:
            sample_id (str): The unique identifier for the sample.

        Returns:
            Optional[SampleInformation]: Returns a SampleInformation object or None.
        """
        try:
            token = self.icat_session["sessionId"]
            url = f"{self.url}/catalogue/{token}/files?sampleId={sample_id}"
            response = requests.get(url, timeout=3)
            response.raise_for_status()  # Raise an exception for bad status codes
            return SampleInformation(
                **response.json(),
            )  # Parse the response into a SampleInformation model
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info("Sample %s not found (404)", sample_id)
            else:
                logger.exception("HTTP error for sample %s", sample_id)

        except requests.exceptions.RequestException:
            logger.exception("Request error for sample %s", sample_id)
        return None

    def _download_resources(
        self, sample_id, resources, output_folder: str, sample_name: str
    ) -> List[Download]:
        """
        Download resources related to a given sample and save them to the
        specified directory.

        Argss:
            sample_id (str): Sample identifier.
            output_folder (str): Directory where storefiles will be saved.

        Returns:
            List containing the paths of the downloaded files.
        """
        downloaded_files: List[Download] = []
        for resource in resources:
            resource_folder = Path(output_folder) / sample_name
            resource_folder = Path(resource_folder) / (
                resource.groupName if resource.groupName else ""
            )
            resource_folder.mkdir(
                parents=True,
                exist_ok=True,
            )  # Make sure the folder exists

            try:
                token = self.icat_session["sessionId"]
                url = f"{self.url}/catalogue/{token}/files/download?sampleId={sample_id}&resourceId={resource.id}"
                response = requests.get(url, stream=True, timeout=3)
                response.raise_for_status()

                file_path = resource_folder / resource.filename
                with file_path.open("wb") as file:
                    for chunk in response.iter_content(
                        chunk_size=8192,
                    ):  # Efficient chunked download
                        file.write(chunk)

                # Create a new Download instance with updated path
                downloaded = Download(
                    path=str(file_path),
                    filename=resource.filename,
                    groupName=resource.groupName,
                )
                downloaded_files.append(downloaded)
                logger.info("Downloaded %s to %s", resource.filename, downloaded.path)

            except requests.exceptions.RequestException:
                logger.exception("Failed to download %s", resource.filename)

        return downloaded_files

    def finalize_data_collection(self, datacollection_dict):
        logger.info("Storing datacollection in ICAT")

        metadata = self.store_common_data(datacollection_dict)

        try:
            fileinfo = datacollection_dict["fileinfo"]
            directory = Path(fileinfo["directory"])
            dataset_name = directory.name
            # Determine the scan type
            scan_types = ["mesh", "line", "characterisation", "datacollection"]
            scan_type = datacollection_dict["experiment_type"]
            for nam in scan_types:
                if dataset_name.endswith(nam):
                    scan_type = nam

            workflow_params = datacollection_dict.get("workflow_parameters", {})
            workflow_type = workflow_params.get("workflow_type")

            if workflow_type is None and not directory.name.startswith("run"):
                dataset_name = fileinfo["prefix"]

            if datacollection_dict["sample_reference"]["acronym"]:
                sample_name = (
                    datacollection_dict["sample_reference"]["acronym"]
                    + "-"
                    + datacollection_dict["sample_reference"]["sample_name"]
                )
            else:
                sample_name = datacollection_dict["sample_reference"][
                    "sample_name"
                ].replace(":", "-")

            logger.info(f"LIMS sample name {sample_name}")
            oscillation_sequence = datacollection_dict["oscillation_sequence"][0]

            beamline = HWR.beamline.session.beamline_name.lower()
            distance = HWR.beamline.detector.distance.get_value()
            proposal = f"{HWR.beamline.session.proposal_code}"
            proposal += f"{HWR.beamline.session.proposal_number}"

            try:
                dt_aware = datetime.strptime(
                    datacollection_dict.get("collection_start_time"),
                    "%Y-%m-%d %H:%M:%S",
                ).replace(tzinfo=ZoneInfo("Europe/Paris"))
                start_time = dt_aware.isoformat(timespec="microseconds")
            except RuntimeError:
                logger.warning("Failed to parse start and end time")

            metadata.update(
                {
                    "MX_dataCollectionId": datacollection_dict.get("collection_id"),
                    "MX_detectorDistance": distance,
                    "MX_directory": str(directory),
                    "MX_exposureTime": oscillation_sequence["exposure_time"],
                    "MX_positionName": datacollection_dict.get("position_name"),
                    "MX_numberOfImages": oscillation_sequence["number_of_images"],
                    "MX_oscillationRange": oscillation_sequence["range"],
                    "MX_axis_start": oscillation_sequence["start"],
                    "MX_oscillationOverlap": oscillation_sequence["overlap"],
                    "MX_resolution": datacollection_dict.get("resolution"),
                    "MX_resolution_at_corner": datacollection_dict.get(
                        "resolutionAtCorner"
                    ),
                    "scanType": scan_type,
                    "MX_startImageNumber": oscillation_sequence["start_image_number"],
                    "MX_template": fileinfo["template"],
                    "Sample_name": sample_name,
                    "Workflow_name": workflow_params.get("workflow_name"),
                    "Workflow_type": workflow_params.get("workflow_type"),
                    "Workflow_id": workflow_params.get("workflow_uid"),
                    "MX_kappa_settings_id": workflow_params.get(
                        "workflow_kappa_settings_id"
                    ),
                    "MX_characterisation_id": workflow_params.get(
                        "workflow_characterisation_id"
                    ),
                    "MX_position_id": workflow_params.get("workflow_position_id"),
                    "group_by": workflow_params.get("workflow_group_by"),
                    "startDate": start_time,
                }
            )

            # This forces the ingester to associate the dataset
            # to the experiment by ID
            if self.session_manager.active_session.session_id:
                metadata["investigationId"] = (
                    self.session_manager.active_session.session_id
                )

            metadata["SampleTrackingContainer_type"] = "UNIPUCK"
            metadata["SampleTrackingContainer_capacity"] = "16"
            (position, sample_position) = self._get_sample_position()
            metadata["SampleChanger_position"] = position
            metadata["SampleTrackingContainer_position"] = sample_position
            # Find sample by sampleId
            sample = HWR.beamline.lims.find_sample_by_sample_id(
                datacollection_dict.get("blSampleId")
            )

            try:
                metadata["lims"] = HWR.beamline.lims.get_active_lims()
            except Exception:
                logger.exception("Failed to read get_active_lims.")

            try:
                if sample is not None:
                    metadata["SampleProtein_acronym"] = sample.get("proteinAcronym")
                    metadata["SampleTrackingContainer_id"] = sample.get(
                        "containerCode"
                    )  # containerCode instead of sampletrackingcontainer_id
                    # for ISPyB's compatiblity
                    metadata["SampleTrackingParcel_id"] = sample.get(
                        "SampleTrackingParcel_id"
                    )
                    metadata["SampleTrackingParcel_name"] = sample.get(
                        "SampleTrackingParcel_name"
                    )
            except RuntimeError as e:
                logger.warning("Failed to add sample metadata.%s", e)

            try:
                self.add_beamline_configuration_metadata(metadata, self.beamline_config)
            except RuntimeError as e:
                logger.warning("Failed to add_beamline_configuration_metadata.%s", e)

            # MX_axis_end
            try:
                metadata["MX_axis_end"] = self._get_oscillation_end(
                    oscillation_sequence
                )
            except RuntimeError:
                logger.warning("Failed to get MX_axis_end")

            # MX_axis_end
            try:
                metadata["MX_axis_range"] = self._get_rotation_axis(
                    oscillation_sequence
                )
            except RuntimeError:
                logger.warning("Failed to get MX_axis_end")

            icat_metadata_path = Path(directory) / "metadata.json"
            with Path(icat_metadata_path).open("w") as f:
                # We add the processing and experiment plan only in the metadata.json
                # it will not work thought pyicat-plus
                merged = metadata.copy()
                try:
                    if sample is not None:
                        merged["experimentPlan"] = sample.get("experimentPlan")
                        merged["processingPlan"] = sample.get("processingPlan")
                except RuntimeError as e:
                    logger.warning("Failed to get merged sample plan. %s", e)

                f.write(json.dumps(merged, indent=4))

            # Create ICAT gallery
            try:
                gallery_path = directory / "gallery"
                gallery_path.mkdir(mode=0o755, exist_ok=True)
                for snapshot_index in range(1, 5):
                    key = f"xtalSnapshotFullPath{snapshot_index}"
                    if key in datacollection_dict:
                        snapshot_path = Path(datacollection_dict[key])
                        if snapshot_path.exists():
                            msg = f"Copying snapshot index {snapshot_index} to gallery"
                            logger.debug(msg)
                            shutil.copy(snapshot_path, gallery_path)
            except RuntimeError as e:
                logger.warning("Failed to create gallery. %s", e)

            try:
                beamline = self._get_scheduled_beamline()
                msg = f"Dataset Beamline={beamline} "
                msg += f"Current Beamline={HWR.beamline.session.beamline_name}"
                logger.info(msg)
            except RuntimeError as err:
                msg = f"Failed to get _get_scheduled_beamline {err}"
                logger.warning(msg)

            # __actualInstrument is a dataset parameter that indicates
            # where the dataset has been actually collected
            # only filled when it does not match the scheduled beamline
            try:
                if (
                    self.active_session is None
                    or not self.active_session.is_scheduled_beamline
                ):
                    metadata["__actualInstrument"] = HWR.beamline.session.beamline_name
            except RuntimeError as e:
                logger.warning("Failed to set __actualInstrument. %s", e)

            self.icatClient.store_dataset(
                beamline=beamline,
                proposal=proposal,
                dataset=dataset_name,
                path=str(directory),
                metadata=metadata,
            )
            logger.debug("Done uploading to ICAT")
        except Exception as e:
            logger.warning("Failed uploading to ICAT. %s", e)

    def _get_scheduled_beamline(self) -> str:
        """Return the name of the beamline as set in the properties or the
        name of the beamline where the session has been scheduled
        (in case of a different beamline)
        """
        active_session = self.session_manager.active_session

        if active_session is None or active_session.is_scheduled_beamline:
            return HWR.beamline.session.beamline_name.lower()

        beamline = str(active_session.beamline_name.lower())
        msg = f"Session have been moved to another beamline: {beamline}"
        logger.info(msg)
        return beamline

    def update_bl_sample(self, bl_sample: str):
        """
        Creates or stos a BLSample entry.
        # NBNB update doc string
        :param sample_dict: A dictionary with the properties for the entry.
        :type sample_dict: dict
        """
