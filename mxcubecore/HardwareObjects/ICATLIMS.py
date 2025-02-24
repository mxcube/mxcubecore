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

    def get_samples(self, lims_name):
        try:
            logging.getLogger("HWR").debug(
                "[ICATClient] get_samples %s %s lims_name=%s",
                self.session_manager.active_session.session_id,
                self.session_manager.active_session.proposal_name,
                lims_name,
            )
            parcels = self.get_parcels()

            sample_sheets = self.get_samples_sheets()

            queue_samples = []
            for parcel in parcels:
                pucks = parcel["content"]
                logging.getLogger("HWR").debug(
                    "[ICATClient] Reading parcel '%s' with '%s' pucks"
                    % (parcel["name"], len(pucks))
                )
                # Parcels contains pucks: unipucks and spine pucks
                for puck in pucks:
                    tracking_samples = puck["content"]
                    if "sampleChangerLocation" in puck:
                        logging.getLogger("HWR").debug(
                            "[ICATClient] Processing puck '%s' within parcel '%s' at position '%s'. Number of samples '%s'"
                            % (
                                puck["name"],
                                parcel["name"],
                                puck["sampleChangerLocation"],
                                len(tracking_samples),
                            )
                        )
                        for tracking_sample in tracking_samples:
                            queue_samples.append(
                                self.__to_sample(tracking_sample, puck, sample_sheets)
                            )

        except Exception as e:
            logging.getLogger("HWR").error(e)
            return []

        logging.getLogger("HWR").debug(
            "[ICATClient] Read %s samples" % (len(queue_samples))
        )

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

    def __to_sample(self, tracking_sample, puck, sample_sheets: List[SampleSheet]):
        """Converts the sample tracking into the expected sample data structure"""

        sample_name = str(tracking_sample["name"])
        protein_acronym = sample_name
        sample_sheet = self.get_sample_sheet_by_id(
            sample_sheets, tracking_sample["sampleId"]
        )
        if sample_sheet is not None:
            protein_acronym = sample_sheet.name

        experiment_plan = tracking_sample["experimentPlan"]
        return {
            "cellA": self.find(experiment_plan, "unit_cell_a"),
            "cellAlpha": self.find(experiment_plan, "unit_cell_alpha"),
            "cellB": self.find(experiment_plan, "unit_cell_b"),
            "cellBeta": self.find(experiment_plan, "unit_cell_beta"),
            "cellC": self.find(experiment_plan, "unit_cell_c"),
            "cellGamma": self.find(experiment_plan, "unit_cell_gamma"),
            "containerSampleChangerLocation": str(puck["sampleChangerLocation"]),
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
            "experimentType": self.find(experiment_plan, "workflowType"),
            "proteinAcronym": protein_acronym,
            "sampleId": tracking_sample["sampleId"],
            "sampleLocation": tracking_sample["sampleContainerPosition"],
            "sampleName": sample_name,
            "smiles": None,
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

    def __add_protein_acronym(self, sample_node, metadata):
        """
        Fills the sample acronym that should match with the acronym defined in the sample sheet
        """
        if sample_node is not None:
            if sample_node.crystals is not None:
                if len(sample_node.crystals) > 0:
                    crystal = sample_node.crystals[0]
                    if crystal.protein_acronym is not None:
                        metadata["SampleProtein_acronym"] = crystal.protein_acronym

    def __add_sample_changer_position(self, cell, puck, metadata):
        """
        Adds to the sample changer position based on the cell and the puck number

        Args:
            cell(str): cell position of the puck in the sample changer
            puck(str): position of the puck within the cell
            metadata(dict): metadata to be pushed to ICAT
        """
        try:
            if cell is not None and puck is not None:
                position = int(cell * 3) + int(puck)
                metadata["SampleChanger_position"] = position
        except Exception as e:
            logging.getLogger("HWR").exception(e)

    def add_beamline_configuration_metadata(self, metadata, beamline_config):
        """
        This is the mapping betweeh the beamline_config dict and the ICAt keys
        in case they exist then they will be added to the metadata of the dataset
        """
        if beamline_config is not None:
            key_mapping = {
                "detector_px": "InstrumentDetector01_x_pixel_size",
                "detector_py": "InstrumentDetector01_y_pixel_size",
                "beam_divergence_vertical": "InstrumentBeam_vertical_incident_beam_divergence",
                "beam_divergence_horizontal": "InstrumentBeam_horizontal_incident_beam_divergence",
                "polarisation": "InstrumentBeam_final_polarization",
                "detector_model": "InstrumentDetector01_model",
                "detector_manufacturer": "InstrumentDetector01_manufacturer",
            }

            for config_key, metadata_key in key_mapping.items():
                if hasattr(beamline_config, config_key):
                    metadata[metadata_key] = getattr(beamline_config, config_key)

    def add_sample_metadata(self, metadata, collection_parameters):
        """
        Adds to the metadata dictionary the metadata concerning sample position, container and tracking

        Args:
            metadata(dict): metadata to be pushed to ICAT
            collection_parameters(dict): Data collection parameters
        """
        try:
            queue_entry = HWR.beamline.queue_manager.get_current_entry()
            sample_node = queue_entry.get_data_model().get_sample_node()
            # sample_node.name this is name of the sample

            location = sample_node.location  # Example: (8,2,5)

            if len(location) == 3:
                (cell, puck, sample_position) = location
            else:
                cell = 1
                (puck, sample_position) = location

            self.__add_sample_changer_position(cell, puck, metadata)
            metadata["SampleTrackingContainer_position"] = sample_position
            metadata["SampleTrackingContainer_type"] = (
                "UNIPUCK"  # this could be read from the configuration file somehow
            )
            metadata["SampleTrackingContainer_capacity"] = (
                "16"  # this could be read from the configuration file somehow
            )

            self.__add_protein_acronym(sample_node, metadata)

            if HWR.beamline.lims is not None:
                sample = HWR.beamline.lims.find_sample_by_sample_id(
                    collection_parameters.get("blSampleId")
                )
                if sample is not None:
                    if "containerCode" in sample:
                        metadata["SampleTrackingContainer_id"] = sample["containerCode"]
                    else:
                        metadata["SampleTrackingContainer_id"] = (
                            str(cell) + "_" + str(puck)
                        )  # Fake identifier that needs to be replaced by container code

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
                "MX_beamShape": collection_parameters["beamShape"],
                "MX_beamSizeAtSampleX": collection_parameters["beamSizeAtSampleX"],
                "MX_beamSizeAtSampleY": collection_parameters["beamSizeAtSampleY"],
                "MX_dataCollectionId": collection_parameters["collection_id"],
                "MX_detectorDistance": distance,
                "MX_directory": str(directory),
                "MX_exposureTime": oscillation_sequence["exposure_time"],
                "MX_flux": collection_parameters["flux"],
                "MX_fluxEnd": collection_parameters["flux_end"],
                "MX_positionName": collection_parameters["position_name"],
                "MX_numberOfImages": oscillation_sequence["number_of_images"],
                "MX_oscillationRange": oscillation_sequence["range"],
                "MX_oscillationStart": oscillation_sequence["start"],
                "MX_oscillationOverlap": oscillation_sequence["overlap"],
                "MX_resolution": collection_parameters["resolution"],
                "scanType": scanType,
                "MX_startImageNumber": oscillation_sequence["start_image_number"],
                "MX_template": fileinfo["template"],
                "MX_transmission": collection_parameters["transmission"],
                "MX_xBeam": collection_parameters["xBeam"],
                "MX_yBeam": collection_parameters["yBeam"],
                "Sample_name": sample_name,
                "InstrumentMonochromator_wavelength": collection_parameters[
                    "wavelength"
                ],
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

            # Store metadata on disk
            self.add_sample_metadata(metadata, collection_parameters)
            self.add_beamline_configuration_metadata(metadata, self.beamline_config)

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
