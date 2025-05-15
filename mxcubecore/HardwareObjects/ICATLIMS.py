import json
import logging
import pathlib
import shutil
from datetime import (
    datetime,
    timedelta,
)
from time import strftime
from typing import (
    List,
    Optional,
)

from pyicat_plus.client.main import IcatClient
from pyicat_plus.client.models.session import Session as ICATSession

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractLims import AbstractLims
from mxcubecore.model.lims_session import (
    Lims,
    LimsSessionManager,
    SampleSheet,
    Session,
)


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
        logging.getLogger("HWR").debug("[ICAT] authenticate %s" % (user_name))

        self.icat_session: ICATSession = self.icatClient.do_log_in(password)

        if self.icatClient is None or self.icatClient is None:
            logging.getLogger("HWR").error(
                "[ICAT] Error initializing icatClient. icatClient=%s" % (self.url)
            )
            raise RuntimeError("Could not initialize icatClient")

        # Connected to metadata icatClient
        logging.getLogger("HWR").debug(
            "[ICAT] Connected succesfully to icatClient. fullName=%s url=%s"
            % (self.icat_session["fullName"], self.url)
        )

        # Retrieving user's investigations
        sessions = self.to_sessions(self.__get_all_investigations())

        if len(sessions) == 0:
            raise Exception("No sessions available for user %s" % (user_name))

        logging.getLogger("HWR").debug(
            "[ICAT] Successfully retrieved %s sessions" % (len(sessions))
        )

        # This is done because ICATLims can be used standalone or from ESRFLims
        if session_manager is not None:
            self.session_manager = session_manager

        # Check if there is currently a session in use and if user have
        # access to that session
        if self.session_manager.active_session:
            session_found = False

            for session in sessions:
                if session.session_id == self.session_manager.active_session.session_id:
                    session_found = True
                    break

            if not session_found:
                raise Exception(
                    "Current session in-use (with id %s) not avaialble to user %s"
                    % (self.session_manager.active_session.session_id, user_name)
                )
        return self.session_manager, self.icat_session["name"], sessions

    def is_user_login_type(self) -> bool:
        return True

    def get_proposals_by_user(self, user_name):
        logging.getLogger("HWR").debug("get_proposals_by_user %s" % user_name)

        logging.getLogger("HWR").debug(
            "[ICATCLient] Read %s investigations" % len(self.lims_rest.investigations)
        )
        return self.lims_rest.to_sessions(self.lims_rest.investigations)

    def _get_loaded_pucks(self):
        """
        Retrieves all pucks from the parcels that have a defined 'sampleChangerLocation'.

        A puck is considered "loaded" if it contains the key 'sampleChangerLocation'.
        Iterates through all parcels and collects such pucks.

        Returns:
            list: A list of pucks (dicts) that have 'sampleChangerLocation' defined.
        """
        loaded_pucks = []

        if self.parcels:
            for parcel in self.parcels:
                pucks = parcel.get("content", [])
                for puck in pucks:
                    if "sampleChangerLocation" in puck:
                        # Add information about the parcel
                        puck["parcelName"] = parcel.get("name")
                        puck["parcelId"] = parcel.get("id")
                        loaded_pucks.append(puck)

        return loaded_pucks

    def get_samples(self, lims_name):
        """
        Retrieves and processes sample information from LIMS based on the provided name.

        This method:
        - Retrieves parcel data (containers like UniPucks or SpinePucks).
        - Retrieves sample sheet data.
        - Identifies and processes only loaded pucks (those with a 'sampleChangerLocation').
        - Converts each sample in the pucks into internal queue samples using `__to_sample`.

        Args:
            lims_name (str): The LIMS name or identifier used to fetch sample-related data.

        Returns:
            list: A list of processed sample objects ready for queuing.
        """
        logger = logging.getLogger("HWR")
        queue_samples = []

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
            self.loaded_pucks = self._get_loaded_pucks()
            logger.debug("[ICATClient] %d loaded pucks found", len(self.loaded_pucks))

            # Extract and process samples from loaded pucks
            for puck in self.loaded_pucks:
                tracking_samples = puck.get("content", [])
                puck_name = puck.get("name", "Unnamed")
                location = puck.get("sampleChangerLocation", "Unknown")

                logger.debug(
                    "[ICATClient] Found puck '%s' at position '%s' containing %d samples",
                    puck_name,
                    location,
                    len(tracking_samples),
                )

                for tracking_sample in tracking_samples:
                    sample = self.__to_sample(tracking_sample, puck, self.sample_sheets)
                    queue_samples.append(sample)

        except Exception as e:
            logger.error("[ICATClient] Error retrieving samples: %s", str(e))
            return []

        logger.debug("[ICATClient] Total %d samples read", len(queue_samples))
        self.samples = queue_samples
        return queue_samples

    def find(self, arr, atribute_name):
        for x in arr:
            if x["key"] == atribute_name:
                return x["value"]
        return ""

    def get_sample_sheet_by_id(
        self, samples: List[SampleSheet], sample_id: int
    ) -> Optional[SampleSheet]:
        """
        Retrieves a sample sheet by its unique ID.

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

    def __to_sample(
        self, tracking_sample: dict, puck: dict, sample_sheets: List[SampleSheet]
    ) -> dict:
        """
        Converts a tracking sample and associated metadata into the internal sample data structure.

        This method:
        - Extracts relevant sample metadata.
        - Resolves protein acronym from the sample sheet if available.
        - Maps experiment plan details into a diffraction plan dictionary.
        - Assembles all relevant fields into a final structured sample dictionary.

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
        sample_id = self.objectid_to_int(tracking_sample.get("id"))
        # id to the sample sheet declared in the user portal
        sample_sheet_id = tracking_sample.get("sampleId")
        # identifier that points to the sample tracking
        trackingSampleId = tracking_sample.get("_id")

        logging.getLogger("HWR").debug(
            "[ICATClient] Sample ids sample_id=%s sample_sheet_id=%s trackingSampleId=%s",
            sample_id,
            sample_sheet_id,
            trackingSampleId,
        )

        sample_location = tracking_sample.get("sampleContainerPosition")
        puck_location = str(puck.get("sampleChangerLocation", "Unknown"))
        puck_name = puck.get("name", "UnknownPuck")
        parcel_name = puck.get("parcelName")
        parcel_id = puck.get("parcelId")
        # Determine protein acronym using sample sheet if available
        protein_acronym = sample_name  # Default fallback
        sample_sheet = self.get_sample_sheet_by_id(sample_sheets, sample_id)
        if sample_sheet:
            protein_acronym = sample_sheet.name

        experiment_plan = tracking_sample.get("experimentPlan", {})
        processing_plan = tracking_sample.get("processingPlan", {})
        comments = tracking_sample.get("comments")

        return {
            "sampleName": sample_name,
            "sampleId": sample_id,
            "sample_sheet_id": sample_sheet_id,
            "trackingSampleId": trackingSampleId,
            "proteinAcronym": protein_acronym,
            "sampleLocation": sample_location,
            "containerCode": puck_name,
            "containerSampleChangerLocation": puck_location,
            "SampleTrackingParcel_name": parcel_name,
            "SampleTrackingParcel_id": parcel_id,
            "SampleTrackingContainer_id": puck_name,
            "SampleTrackingContainer_name": parcel_id,
            "smiles": None,  # Placeholder for future chemical structure info
            "experimentType": self.find(experiment_plan, "workflowType"),
            "crystalSpaceGroup": self.find(experiment_plan, "forceSpaceGroup"),
            "diffractionPlan": {
                # "diffractionPlanId": 457980, TODO: do we need this?
                "experimentKind": self.find(experiment_plan, "experimentKind"),
                "numberOfPositions": self.find(experiment_plan, "numberOfPositions"),
                "observedResolution": self.find(experiment_plan, "observedResolution"),
                "preferredBeamDiameter": self.find(
                    experiment_plan, "preferredBeamDiameter"
                ),
                "radiationSensitivity": self.find(
                    experiment_plan, "radiationSensitivity"
                ),
                "requiredCompleteness": self.find(
                    experiment_plan, "requiredCompleteness"
                ),
                "requiredMultiplicity": self.find(
                    experiment_plan, "requiredMultiplicity"
                ),
                "requiredResolution": self.find(experiment_plan, "requiredResolution"),
            },
            "cellA": self.find(experiment_plan, "unit_cell_a"),
            "cellB": self.find(experiment_plan, "unit_cell_b"),
            "cellC": self.find(experiment_plan, "unit_cell_c"),
            "cellAlpha": self.find(experiment_plan, "unit_cell_alpha"),
            "cellBeta": self.find(experiment_plan, "unit_cell_beta"),
            "cellGamma": self.find(experiment_plan, "unit_cell_gamma"),
            "experimentPlan": experiment_plan,
            "processingPlan": processing_plan,
            "comments": comments,
        }

    def create_session(self, session_dict):
        pass

    def _store_data_collection_group(self, group_data):
        pass

    def store_robot_action(self, proposal_id: str):
        raise Exception("Not implemented")

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

    def _string_to_format_date(self, date: str, format: str) -> str:
        if date is not None:
            date_time = self._tz_aware_fromisoformat(date)
            if date_time is not None:
                return date_time.strftime(format)
        return ""

    def _string_to_date(self, date: str) -> str:
        return self._string_to_format_date(date, "%Y%m%d")

    def _string_to_time(self, date: str) -> str:
        return self._string_to_format_date(date, "%H:%M:%S")

    def _tz_aware_fromisoformat(self, date: str) -> datetime:
        try:
            return datetime.fromisoformat(date).astimezone()
        except Exception:
            return None

    def set_active_session_by_id(self, session_id: str) -> Session:
        if self.is_session_already_active(self.session_manager.active_session):
            return self.session_manager.active_session

        sessions = self.session_manager.sessions

        if len(sessions) == 0:
            logging.getLogger("HWR").error(
                "Session list is empty. No session candidates"
            )
            raise Exception("No sessions available")

        if len(sessions) == 1:
            self.session_manager.active_session = sessions[0]
            logging.getLogger("HWR").debug(
                "Session list contains a single session. proposal_name=%s",
                self.session_manager.active_session.proposal_name,
            )
            return self.session_manager.active_session

        session_list = [obj for obj in sessions if obj.session_id == session_id]
        if len(session_list) != 1:
            raise Exception(
                "Session not found in the local list of sessions. session_id="
                + session_id
            )
        self.session_manager.active_session = session_list[0]
        return self.session_manager.active_session

    def allow_session(self, session: Session):
        self.active_session = session
        logging.getLogger("HWR").debug(
            "[ICAT] allow_session investigationId=%s", session.session_id
        )
        self.icatClient.reschedule_investigation(session.session_id)

    def get_session_by_id(self, id: str):
        logging.getLogger("HWR").debug(
            "[ICAT] get_session_by_id investigationId=%s investigations=%s",
            id,
            str(len(self.investigations)),
        )
        investigation_list = list(filter(lambda p: p["id"] == id, self.investigations))
        if len(investigation_list) == 1:
            self.investigation = investigation_list[0]
            return self.__to_session(investigation_list[0])
        logging.getLogger("HWR").warn(
            "[ICAT] No investigation found. get_session_by_id investigationId=%s investigations=%s",
            id,
            str(len(self.investigations)),
        )
        return None

    def __get_all_investigations(self):
        """Returns all investigations by user. An investigation corresponds to
        one experimental session. It returns an empty array in case of error"""
        try:
            self.investigations = []
            logging.getLogger("HWR").debug(
                "[ICAT] __get_all_investigations before=%s after=%s beamline=%s isInstrumentScientist=%s isAdministrator=%s compatible_beamlines=%s"
                % (
                    self.before_offset_days,
                    self.after_offset_days,
                    self.override_beamline_name,
                    self.icat_session["isInstrumentScientist"],
                    self.icat_session["isAdministrator"],
                    self.compatible_beamlines,
                )
            )

            if self.icat_session is not None and (
                self.icat_session["isAdministrator"]
                or self.icat_session["isInstrumentScientist"]
            ):
                self.investigations = self.icatClient.get_investigations_by(
                    start_date=datetime.today()
                    - timedelta(days=float(self.before_offset_days)),
                    end_date=datetime.today()
                    + timedelta(days=float(self.after_offset_days)),
                    instrument_name=self.compatible_beamlines,
                )
            else:
                self.investigations = self.icatClient.get_investigations_by(
                    filter=self.filter,
                    instrument_name=self.override_beamline_name,
                    start_date=datetime.today()
                    - timedelta(days=float(self.before_offset_days)),
                    end_date=datetime.today()
                    + timedelta(days=float(self.after_offset_days)),
                )
            logging.getLogger("HWR").debug(
                "[ICAT] __get_all_investigations retrieved %s investigations"
                % len(self.investigations)
            )
            return self.investigations
        except Exception as e:
            self.investigations = []
            logging.getLogger("HWR").error("[ICAT] __get_all_investigations %s " % e)
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
            is_rescheduled=(
                True if "__actualEndDate" in investigation["parameters"] else False
            ),
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
            logging.getLogger("HWR").debug(
                "[ICAT] Retrieving parcels by investigation_id %s "
                % (self.session_manager.active_session.session_id)
            )
            parcels = self.icatClient.get_parcels_by(
                self.session_manager.active_session.session_id
            )
            logging.getLogger("HWR").debug(
                "[ICAT] Successfully retrieved %s parcels" % (len(parcels))
            )
            return parcels
        except Exception as e:
            logging.getLogger("HWR").error(
                "[ICAT] get_parcels_by_investigation_id %s " % (str(e))
            )
        return []

    def get_samples_sheets(self) -> List[SampleSheet]:
        """Returns the samples sheets associated to an investigation"""
        try:
            logging.getLogger("HWR").debug(
                "[ICAT] Retrieving samples by investigation_id %s "
                % (self.session_manager.active_session.session_id)
            )
            samples = self.icatClient.get_samples_by(
                self.session_manager.active_session.session_id
            )
            logging.getLogger("HWR").debug(
                "[ICAT] Successfully retrieved %s samples" % (len(samples))
            )
            # Convert to object
            return [SampleSheet.parse_obj(sample) for sample in samples]
        except Exception as e:
            logging.getLogger("HWR").error(
                "[ICAT] get_samples_by_investigation_id %s " % (str(e))
            )
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
            (sample for sample in self.samples if sample["limsID"] == sample_id),
            None,
        )

    def _get_sample_position(self):
        """
        Returns the position of the puck in the samples changer and the position f the sample within the puck
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
            try:
                if cell is not None and puck is not None:
                    position = int(cell * 3) + int(puck)
            except Exception as e:
                logging.getLogger("HWR").exception(e)
            return position, sample_position
        except Exception as e:
            logging.getLogger("HWR").exception(e)

    def store_beamline_setup(self, session_id: str, bl_config_dict: dict):
        pass

    def store_image(self, image_dict: dict):
        pass

    def store_energy_scan(self, energyscan_dict: dict):
        pass

    def store_xfe_spectrum(self, xfespectrum_dict: dict):
        pass

    def store_workflow(self, workflow_dict: dict):
        pass

    def store_data_collection(self, mx_collection, bl_config=None):
        # stores the dictionay with the information about the beamline to be sent when a dataset is produced
        self.beamline_config = bl_config

    def update_data_collection(self, mx_collection):
        pass

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

    def finalize_data_collection(self, collection_parameters):
        logging.getLogger("HWR").info("Storing datacollection in ICAT")

        try:
            fileinfo = collection_parameters["fileinfo"]
            directory = pathlib.Path(fileinfo["directory"])
            dataset_name = directory.name
            # Determine the scan type
            if dataset_name.endswith("mesh"):
                scanType = "mesh"
            elif dataset_name.endswith("line"):
                scanType = "line"
            elif dataset_name.endswith("characterisation"):
                scanType = "characterisation"
            elif dataset_name.endswith("datacollection"):
                scanType = "datacollection"
            else:
                scanType = collection_parameters["experiment_type"]

            workflow_params = collection_parameters.get("workflow_parameters", {})
            workflow_type = workflow_params.get("workflow_type")

            if workflow_type is None:
                if not directory.name.startswith("run"):
                    dataset_name = fileinfo["prefix"]

            start_time = collection_parameters.get(
                "collection_start_time", strftime("%Y-%m-%d %H:%M:%S")
            )

            if collection_parameters["sample_reference"]["acronym"]:
                sample_name = (
                    collection_parameters["sample_reference"]["acronym"]
                    + "-"
                    + collection_parameters["sample_reference"]["sample_name"]
                )
            else:
                sample_name = collection_parameters["sample_reference"][
                    "sample_name"
                ].replace(":", "-")

            logging.getLogger("HWR").info(f"LIMS sample name {sample_name}")
            oscillation_sequence = collection_parameters["oscillation_sequence"][0]

            beamline = HWR.beamline.session.beamline_name.lower()
            distance = HWR.beamline.detector.distance.get_value()
            proposal = f"{HWR.beamline.session.proposal_code}{HWR.beamline.session.proposal_number}"
            metadata = {
                "MX_beamShape": collection_parameters.get("beamShape"),
                "sampleId": collection_parameters.get("blSampleId"),
                "MX_beamSizeAtSampleX": collection_parameters.get("beamSizeAtSampleX"),
                "MX_beamSizeAtSampleY": collection_parameters.get("beamSizeAtSampleY"),
                "MX_dataCollectionId": collection_parameters.get("collection_id"),
                "MX_detectorDistance": distance,
                "MX_directory": str(directory),
                "MX_exposureTime": oscillation_sequence["exposure_time"],
                "MX_flux": collection_parameters.get("flux"),
                "MX_fluxEnd": collection_parameters.get("flux_end"),
                "MX_positionName": collection_parameters.get("position_name"),
                "MX_numberOfImages": oscillation_sequence["number_of_images"],
                "MX_oscillationRange": oscillation_sequence["range"],
                "MX_axis_start": oscillation_sequence["start"],
                "MX_oscillationOverlap": oscillation_sequence["overlap"],
                "MX_resolution": collection_parameters.get("resolution"),
                "MX_resolution_at_corner": collection_parameters.get(
                    "resolutionAtCorner"
                ),
                "scanType": scanType,
                "MX_startImageNumber": oscillation_sequence["start_image_number"],
                "MX_template": fileinfo["template"],
                "MX_transmission": collection_parameters.get("transmission"),
                "MX_xBeam": collection_parameters.get("xBeam"),
                "MX_yBeam": collection_parameters.get("yBeam"),
                "Sample_name": sample_name,
                "InstrumentMonochromator_wavelength": collection_parameters.get(
                    "wavelength"
                ),
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
                "endDate": strftime("%Y-%m-%d %H:%M:%S"),
            }

            # This forces the ingester to associate the dataset to the experiment by ID
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
                collection_parameters.get("blSampleId")
            )
            if sample is not None:
                metadata["SampleProtein_acronym"] = sample.get("proteinAcronym")
                metadata["SampleTrackingContainer_id"] = sample.get(
                    "SampleTrackingContainer_id"
                )
                metadata["SampleTrackingParcel_id"] = sample.get(
                    "SampleTrackingParcel_id"
                )
                metadata["SampleTrackingParcel_name"] = sample.get(
                    "SampleTrackingParcel_name"
                )

            self.add_beamline_configuration_metadata(metadata, self.beamline_config)

            # MX_axis_end
            try:
                metadata["MX_axis_end"] = self._get_oscillation_end(
                    oscillation_sequence
                )
            except RuntimeError:
                logging.getLogger("HWR").exception("Failed to get MX_axis_end")

            # MX_axis_end
            try:
                metadata["MX_axis_range"] = self._get_rotation_axis(
                    oscillation_sequence
                )
            except RuntimeError:
                logging.getLogger("HWR").exception("Failed to get MX_axis_end")

            icat_metadata_path = pathlib.Path(directory) / "metadata.json"
            with open(icat_metadata_path, "w") as f:
                f.write(json.dumps(metadata, indent=4))
            # Create ICAT gallery
            gallery_path = directory / "gallery"
            gallery_path.mkdir(mode=0o755, exist_ok=True)
            for snapshot_index in range(1, 5):
                key = f"xtalSnapshotFullPath{snapshot_index}"
                if key in collection_parameters:
                    snapshot_path = pathlib.Path(collection_parameters[key])
                    if snapshot_path.exists():
                        logging.getLogger("HWR").debug(
                            f"Copying snapshot index {snapshot_index} to gallery"
                        )
                        shutil.copy(snapshot_path, gallery_path)

            try:
                beamline = self._get_scheduled_beamline()
                logging.getLogger("HWR").info(
                    f"Dataset Beamline={beamline} Current Beamline={HWR.beamline.session.beamline_name}"
                )
            except Exception:
                logging.getLogger("HWR").exception(
                    "Failed to get _get_scheduled_beamline"
                )

            # __actualInstrument is a dataset parameter that indicates where the dataset has been actually collected
            # only filled when it does not match the scheduled beamline
            try:
                if (
                    self.active_session is None
                    or not self.active_session.is_scheduled_beamline
                ):
                    metadata["__actualInstrument"] = HWR.beamline.session.beamline_name
            except Exception:
                logging.getLogger("HWR").exception("")

            self.icatClient.store_dataset(
                beamline=beamline,
                proposal=proposal,
                dataset=dataset_name,
                path=str(directory),
                metadata=metadata,
            )
            logging.getLogger("HWR").debug("Done uploading to ICAT")
        except Exception as e:
            logging.getLogger("HWR").exception("Failed uploading to ICAT")

    def _get_scheduled_beamline(self):
        """
        This returns the beamline where the session has been scheduled (in case of a different beamline)
        otherwise it returns the name of the beamline as set in the properties
        """
        active_session = self.session_manager.active_session

        if active_session is None or active_session.is_scheduled_beamline:
            return HWR.beamline.session.beamline_name.lower()

        beamline = str(active_session.beamline_name.lower())
        logging.getLogger("HWR").info(
            f"Session have been moved to another beamline: {beamline}"
        )
        return beamline

    def update_bl_sample(self, bl_sample: str):
        """
        Creates or stos a BLSample entry.
        # NBNB update doc string
        :param sample_dict: A dictonary with the properties for the entry.
        :type sample_dict: dict
        """
        pass
