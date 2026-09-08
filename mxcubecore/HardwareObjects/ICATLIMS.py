import json
import logging
import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from importlib.util import find_spec
from pathlib import Path
from typing import Any, List, Optional, Tuple
from zoneinfo import ZoneInfo

from gevent.lock import RLock
from pydantic import ValidationError
from pyicat_plus import errors as icat_errors
from pyicat_plus.client import models as icat_models
from pyicat_plus.client.main import IcatClient

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractLims import (
    AbstractLims,
    LimsMetadataGatherError,
    LimsMetadataUploadError,
    LimsMetadataWriteError,
)
from mxcubecore.model.lims_session import (
    Download,
    Lims,
    LimsSessionManager,
    Session,
)
from mxcubecore.model.tracking_model_objects import LoadedPuck

if find_spec("esrf_ontologies"):
    from esrf_ontologies import technique


logger = logging.getLogger("HWR")

# Attribute names read off the beamline_config object in
# add_beamline_configuration_metadata(). Not ICAT schema keys.
PROTEIN_ACRONYM_KEY = "proteinAcronym"
DETECTOR_PX_KEY = "detector_px"
DETECTOR_PY_KEY = "detector_py"
BEAM_DIVERGENCE_VERTICAL_KEY = "beam_divergence_vertical"
BEAM_DIVERGENCE_HORIZONTAL_KEY = "beam_divergence_horizontal"
POLARISATION_KEY = "polarisation"
DETECTOR_MODEL_KEY = "detector_model"
DETECTOR_MANUFACTURER_KEY = "detector_manufacturer"
SYNCHROTRON_NAME_KEY = "synchrotron_name"
MONOCHROMATOR_TYPE_KEY = "monochromator_type"
DETECTOR_TYPE_KEY = "detector_type"

# No icat_esrf_definitions field exists for these yet.
ACTUAL_INSTRUMENT_KEY = "actualInstrument"


def _optional_str(value: Any) -> Optional[str]:
    """Coerce a value for an ICAT model field typed as plain ``str``.

    Unlike its quantity-typed fields, icat_esrf_definitions' plain ``str``
    fields don't coerce numbers, so numeric values (e.g. a detector position
    or a database id) must be stringified explicitly before assignment.
    """
    return None if value is None else str(value)


class DataCollectionMetadataGatherer:
    """Assembles the metadata for a finished standard MX data collection, in
    the format expected by ICAT (via pyicat-plus) and metadata.json.

    Independent of any LIMS hardware object instance or of how the
    resulting metadata is subsequently written to disk or uploaded - it
    only reads beamline/session/queue state (via HWR) and the arguments
    passed to gather().
    """

    def gather(
        self,
        datacollection_dict: dict,
        beamline_config,
        params: icat_models.IcatDatasetParameters,
        extra: dict,
        scheduled_beamline: Optional[str] = None,
    ) -> dict:
        """Assemble the metadata for a finished data collection

        Args:
            datacollection_dict: the collection's own parameters.
            beamline_config: beamline configuration object/dict used to add
                beamline configuration fields to the gathered metadata.
            params: the partially-filled ``icat_models.IcatDatasetParameters``
                already produced by gather_common_metadata()
            extra: flat ICAT keys with no corresponding model field, as
                returned alongside params by gather_common_metadata().
            scheduled_beamline: name of the beamline the experiment was
                scheduled on

        Returns a dict with keys "metadata", "file_metadata", "directory",
        "dataset_name", "beamline", "proposal" and "snapshot_paths".
        """
        fileinfo = datacollection_dict["fileinfo"]
        directory = Path(fileinfo["directory"])
        dataset_name = directory.name
        # Determine the scan type
        scan_types = ["mesh", "line", "characterisation", "datacollection"]
        scan_type = datacollection_dict["experiment_type"]
        for nam in scan_types:
            if dataset_name.endswith(nam):
                scan_type = nam

        if scan_type == "characterisation":
            # The "complete" entry in metadata must be set to False in order to
            # group multi-wedge reference image data collection for characterisation
            params.complete = False
        elif scan_type == "OSC":
            # In case the experiment_type is "OSC" and doesn't have
            # "datacollection" in the dataset name, we set it to "datacollection".
            # This happens for data collected by GPhL workflows.
            scan_type = "datacollection"

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

        beamline_name = HWR.beamline.session.beamline_name
        beamline = beamline_name.lower()
        distance = HWR.beamline.detector.distance.get_value()
        proposal = f"{HWR.beamline.session.proposal_code}"
        proposal += f"{HWR.beamline.session.proposal_number}"

        mx_kappa_settings_id = None
        diffr = HWR.beamline.diffractometer
        kappa_pos = diffr.kappa.get_value() if hasattr(diffr, "kappa") else None
        kappa_phi_pos = (
            diffr.kappa_phi.get_value() if hasattr(diffr, "kappa_phi") else None
        )
        if None not in (kappa_pos, kappa_phi_pos):
            mx_kappa_settings_id = f"Kappa: {kappa_pos:0.1f}, Phi: {kappa_phi_pos:0.1f}"

        params.title = dataset_name
        params.folder_path = str(directory)
        mx = params.MX
        mx.dataCollectionId = _optional_str(datacollection_dict.get("collection_id"))
        mx.detectorDistance = distance
        mx.directory = str(directory)
        mx.exposureTime = oscillation_sequence["exposure_time"]
        mx.positionName = _optional_str(datacollection_dict.get("position_name"))
        mx.numberOfImages = oscillation_sequence["number_of_images"]
        mx.oscillationRange = oscillation_sequence["range"]
        mx.axis_start = oscillation_sequence["start"]
        mx.oscillationOverlap = oscillation_sequence["offset"]
        mx.resolution = datacollection_dict.get("resolution")
        mx.resolution_at_corner = datacollection_dict.get("resolutionAtCorner")
        mx.scanType = scan_type
        mx.startImageNumber = oscillation_sequence["start_image_number"]
        mx.template = fileinfo["template"]
        mx.kappa_settings_id = mx_kappa_settings_id
        mx.characterisation_id = _optional_str(
            workflow_params.get("workflow_characterisation_id")
        )
        mx.position_id = _optional_str(workflow_params.get("workflow_position_id"))

        params.sample.name = sample_name
        params.workflow.name = _optional_str(workflow_params.get("workflow_name"))
        params.workflow.type = _optional_str(workflow_params.get("workflow_type"))
        params.workflow.id = _optional_str(workflow_params.get("workflow_uid"))
        params.workflow.note = _optional_str(workflow_params.get("workflow_note"))
        params.group_by = workflow_params.get("workflow_group_by")

        position, sample_position = self._get_sample_position()
        params.sample.changer.position = (
            str(position) if position is not None else None
        )
        params.sample.tracking.container.type = "UNIPUCK"
        params.sample.tracking.container.capacity = "16"
        params.sample.tracking.container.position = (
            str(sample_position) if sample_position is not None else None
        )

        # Find sample by sampleId
        sample = HWR.beamline.lims.find_sample_by_sample_id(
            datacollection_dict.get("blSampleId")
        )

        try:
            if sample is not None:
                params.sample.protein.acronym = _optional_str(
                    sample.get(PROTEIN_ACRONYM_KEY)
                )
                # containerCode instead of sampletrackingcontainer_id for ISPyB compatibility
                params.sample.tracking.container.id = _optional_str(
                    sample.get("containerCode")
                )
                params.sample.tracking.parcel.id = _optional_str(
                    sample.get("SampleTrackingParcel_id")
                )
                params.sample.tracking.parcel.name = _optional_str(
                    sample.get("SampleTrackingParcel_name")
                )
        except RuntimeError as e:
            logger.warning("Failed to add sample metadata.%s", e)

        try:
            self._add_beamline_configuration_metadata(
                params.instrument, beamline_config
            )
        except RuntimeError as e:
            logger.warning("Failed to add_beamline_configuration_metadata.%s", e)

        try:
            mx.axis_end = self._get_oscillation_end(oscillation_sequence)
        except RuntimeError:
            logger.warning("Failed to get MX_axis_end")

        # Name of the rotation axis (e.g. "Omega"/"Phi"); axis_range is a
        # numeric field and can't hold this string, unlike rotation_axis.
        try:
            mx.rotation_axis = self._get_rotation_axis(oscillation_sequence)
        except RuntimeError:
            logger.warning("Failed to get MX_axis_end")

        params = params.finalize()
        metadata = params.to_icat_dict()
        metadata.update(extra)

        # metadata.json is a superset of what's sent to ICAT - it additionally
        # includes the experiment/processing plan and a few identifying
        # fields that pyicat-plus itself doesn't accept.
        file_metadata = metadata.copy()

        try:
            if sample is not None:
                file_metadata["experimentPlan"] = sample.get("experimentPlan")
                file_metadata["processingPlan"] = sample.get("processingPlan")
        except RuntimeError as e:
            logger.warning("Failed to get merged sample plan. %s", e)

        # ISPyB sample id
        file_metadata["sample_id"] = datacollection_dict.get("blSampleId")

        # Name of the beamline where the experiment is being conducted
        file_metadata["beamline_name"] = beamline_name
        logger.info(f"Current beamline: {beamline_name}")

        # Name of the beamline where the experiment was scheduled
        if scheduled_beamline is not None:
            file_metadata["scheduled_beamline_name"] = scheduled_beamline
            logger.info(f"Scheduled beamline: {scheduled_beamline}")

        try:
            file_metadata["lims"] = HWR.beamline.lims.get_active_lims().name
        except Exception:
            logger.exception("Failed to read get_active_lims.")

        snapshot_paths = []
        for snapshot_index in range(1, 5):
            key = f"xtalSnapshotFullPath{snapshot_index}"
            if key in datacollection_dict:
                snapshot_path = Path(datacollection_dict[key])
                if snapshot_path.exists():
                    snapshot_paths.append(snapshot_path)

        return {
            "metadata": metadata,
            "file_metadata": file_metadata,
            "directory": directory,
            "dataset_name": dataset_name,
            "beamline": beamline,
            "proposal": proposal,
            "snapshot_paths": snapshot_paths,
        }

    @staticmethod
    def gather_common_metadata(
        datacollection_dict: dict,
        investigation_id: Optional[str] = None,
        investigation_name: Optional[str] = None,
        actual_instrument: Optional[str] = None,
    ) -> Tuple[icat_models.IcatDatasetParameters, dict]:
        """Assemble the pydantic model fields common to all data collection
        techniques (energy scans, XFE spectra, and finished data collections
        alike): sample name, collection start/end time, beam/detector/
        energy/transmission/machine/cryo readings.

        Returns a tuple ``(params, extra)``. ``params`` is a
        partially-filled ``icat_models.IcatDatasetParameters.blank()``
        instance. ``extra`` holds flat ICAT keys with no corresponding
        model field.
        """
        sample_id = datacollection_dict.get("blSampleId")
        logger.debug(f"SampleId is: {sample_id}")
        try:
            sample = HWR.beamline.lims.find_sample_by_sample_id(sample_id)
            sample_name = sample.get("sampleName")
        except (AttributeError, TypeError):
            sample_name = "unknown"
            logger.debug(f"Sample {sample_id} not found")

        start_time = datacollection_dict.get("collection_start_time", "")
        end_time = datetime.now(ZoneInfo("Europe/Paris")).isoformat()

        if start_time:
            try:
                dt_aware = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=ZoneInfo("Europe/Paris")
                )
                start_time = dt_aware.isoformat(timespec="microseconds")
            except (ValueError, TypeError):
                logger.exception("Cannot parse start time")
        else:
            start_time = datetime.now(ZoneInfo("Europe/Paris")).isoformat()

        bsx, bsy, shape, _ = HWR.beamline.beam.get_value()
        flux_end = datacollection_dict.get("flux_end") or HWR.beamline.flux.get_value()
        xbeam, ybeam = HWR.beamline.detector.get_beam_position(
            distance=HWR.beamline.detector.distance.get_value()
        )

        HWR.beamline.detector.distance.get_value()

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

        cryo_temperature = None
        if hasattr(HWR.beamline, "cryo"):
            try:
                cryo = HWR.beamline.cryo
                cryo_temperature = cryo.get_value()
                limits = cryo.get_limits()
                if None not in limits and cryo_temperature > max(limits):
                    cryo_temperature = "room temperature"
            except RuntimeError:
                cryo_temperature = None

        extra = {}
        if actual_instrument is not None:
            extra[ACTUAL_INSTRUMENT_KEY] = actual_instrument

        # IcatCryostat.value is a numeric quantity: the "room temperature"
        # sentinel string can't go through it, so it's sent as a plain key.
        if cryo_temperature == "room temperature":
            extra["InstrumentCryostat01_value"] = cryo_temperature

        params = icat_models.IcatDatasetParameters.blank()
        params.sample.name = sample_name
        params.start_time = start_time
        params.end_time = end_time
        params.investigationId = investigation_id
        params.proposal = investigation_name
        params.instrument.monochromator.wavelength = wavelength
        params.instrument.monochromator.energy = energy
        params.instrument.source.current = machine_info.get("current")
        params.instrument.source.mode = machine_info.get("fill_mode")
        if cryo_temperature is not None and cryo_temperature != "room temperature":
            params.instrument.cryostat01.value = cryo_temperature
        params.MX.beamShape = shape.value
        params.MX.beamSizeAtSampleX = bsx
        params.MX.beamSizeAtSampleY = bsy
        params.MX.xBeam = xbeam
        params.MX.yBeam = ybeam
        params.MX.flux = datacollection_dict.get("flux")
        params.MX.fluxEnd = flux_end
        params.MX.transmission = transmission

        return params, extra

    @staticmethod
    def _add_beamline_configuration_metadata(instrument, beamline_config):
        """Map fields from beamline_config onto their ICAT instrument model
        fields, for whichever fields are present."""
        if beamline_config is None:
            return

        key_mapping = {
            DETECTOR_PX_KEY: (instrument.detector01, "beam_center_x"),
            DETECTOR_PY_KEY: (instrument.detector01, "beam_center_y"),
            BEAM_DIVERGENCE_VERTICAL_KEY: (
                instrument.beam,
                "vertical_incident_beam_divergence",
            ),
            BEAM_DIVERGENCE_HORIZONTAL_KEY: (
                instrument.beam,
                "horizontal_incident_beam_divergence",
            ),
            POLARISATION_KEY: (instrument.beam, "final_polarization"),
            DETECTOR_MODEL_KEY: (instrument.detector01, "model"),
            DETECTOR_MANUFACTURER_KEY: (instrument.detector01, "manufacturer"),
            SYNCHROTRON_NAME_KEY: (instrument.source, "name"),
            MONOCHROMATOR_TYPE_KEY: (instrument.monochromator.crystal, "type"),
            DETECTOR_TYPE_KEY: (instrument.detector01, "type"),
        }

        # beam_center_x/y are plain str fields (not quantities): stringify
        # explicitly since the config value is typically numeric.
        str_only_attrs = {"beam_center_x", "beam_center_y"}
        for config_key, (target, attr_name) in key_mapping.items():
            if hasattr(beamline_config, config_key):
                value = getattr(beamline_config, config_key)
                if attr_name in str_only_attrs:
                    value = _optional_str(value)
                setattr(target, attr_name, value)

    @staticmethod
    def _get_oscillation_end(oscillation_sequence):
        return float(oscillation_sequence["start"]) + (
            float(oscillation_sequence["range"])
            - float(oscillation_sequence["offset"])
        ) * float(oscillation_sequence["number_of_images"])

    @staticmethod
    def _get_rotation_axis(oscillation_sequence):
        if "kappaStart" in oscillation_sequence:
            if (
                oscillation_sequence["kappaStart"] != 0
                and oscillation_sequence["kappaStart"] != -9999
            ):
                return "Omega"
        return "Phi"

    @staticmethod
    def _get_sample_position() -> tuple:
        """Return the position of the puck in the sample changer and the
        position of the sample within the puck."""
        position = None
        sample_position = None
        try:
            queue_entry = HWR.beamline.queue_manager.get_current_entry()
            sample_node = queue_entry.get_data_model().get_sample_node()
            location = sample_node.location  # Example: (8,2,5)

            if len(location) == 3:
                cell, puck, sample_position = location
            else:
                cell = 1
                puck, sample_position = location

            if None not in (cell, puck):
                position = int(cell * 3) + int(puck)
        except Exception:
            logger.exception("Cannot retrieve sample position")
        return position, sample_position


class ICATLIMS(AbstractLims):
    def __init__(self, name):
        super().__init__(name)
        HardwareObject.__init__(self, name)
        self.investigations = None
        self._icat_client_dict = {}
        self._active_user = None
        self._icat_session_dict = {}
        self._active_user_lock = RLock()
        self.lims_rest = None
        self.activemq_url = None

    def init(self):
        self.url = self.get_property("ws_root")
        self.activemq_url = self.get_property("queue_urls")
        self.authentication_icat_plugin = self.get_property(
            "authentication_icat_plugin", "esrf"
        )
        self.investigations = []
        self.samples = []
        self._downloads_cache = {}

    @property
    def _icat_client(self):
        with self._active_user_lock:
            active_user = self._active_user
        self.log.debug("Using ICAT client for user: %s", active_user)
        try:
            return self._icat_client_dict[active_user]
        except KeyError:
            msg = f"No active ICAT client for user {active_user!r}"
            raise RuntimeError(msg) from None

    @property
    def icat_session(self):
        with self._active_user_lock:
            active_user = self._active_user
        try:
            return self._icat_session_dict[active_user]
        except KeyError:
            msg = f"No active ICAT session for user {active_user!r}"
            raise RuntimeError(msg) from None

    def get_lims_name(self) -> List[Lims]:
        return [
            Lims(
                name="Data Portal",
                description="Data Repository for Advancing open sCience",
            ),
        ]

    def _create_icat_client(self):
        return IcatClient(
            icatplus_restricted_url=self.url,
            metadata_urls=[self.activemq_url],
            reschedule_investigation_urls=[self.activemq_url],
        )

    def _create_icat_session(
        self, user_name: str, password: str
    ) -> tuple[icat_models.AuthSession, IcatClient]:
        icat_client = self._create_icat_client()
        try:
            logger.debug(f"Authenticating {user_name}")
            icat_session = icat_client.do_log_in(
                password=password,
                plugin=self.authentication_icat_plugin,
            )
        except icat_errors.ForbiddenException as e:
            logger.error(f" Error occurred while authenticating. Access forbidden {e}")
            raise
        except icat_errors.ApiException as e:
            logger.error(f"Error occurred while authenticating {user_name}: {e}")
            raise
        return icat_session, icat_client

    def set_active_user(self, username: str):
        with self._active_user_lock:
            if username not in self._icat_client_dict:
                msg = f"User {username} has no active ICAT session"
                logger.error(msg)
                raise RuntimeError(msg)

            self._active_user = username
        self.log.info("Active ICAT user set to: %s", username)

    def login(
        self,
        username: str,
        password: str,
        session_manager: Optional[LimsSessionManager],
    ) -> LimsSessionManager:
        logger.debug(f"ICAT authenticate {username}")

        icat_session, icat_client = self._create_icat_session(username, password)
        with self._active_user_lock:
            self._icat_client_dict[username] = icat_client
            self._icat_session_dict[username] = icat_session

        # Connected to metadata icatClient
        msg = "Connected succesfully to ICAT: "
        msg += f"fullName={icat_session.full_name}, url={self.url}"
        logger.debug(msg)

        if not self._active_user:
            self.set_active_user(username)

        # Retrieving user's investigations
        sessions = self.to_sessions(self.__get_all_investigations())

        if len(sessions) == 0:
            msg = f"No sessions available for user {username}"
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
                msg += f"not avaialble for user {username}"
                raise RuntimeError(msg)

        return self.session_manager, icat_session, sessions

    def remove_user(self, user_name: str):
        """Drop a signed-out user's ICAT client/session along with the
        base-class session-manager bookkeeping. Never evicts the user
        currently active (matches AbstractLims.remove_user, which refuses
        to remove a user whose session is the active one)."""
        with self._active_user_lock:
            if user_name == self._active_user:
                self.log.debug(
                    "User %s was not removed because it is the active ICAT user",
                    user_name,
                )
                return
            self._icat_client_dict.pop(user_name, None)
            self._icat_session_dict.pop(user_name, None)

        super().remove_user(user_name)

    def is_user_login_type(self) -> bool:
        return True

    def get_proposals_by_user(self, user_name):
        msg = f"get_proposals_by_user {user_name}\n"
        msg += f"[ICATCLient] Read {len(self.lims_rest.investigations)} investigations"
        logger.debug(msg)

        return self.lims_rest.to_sessions(self.lims_rest.investigations)

    def _get_loaded_pucks(self, investigation_id: str) -> List[LoadedPuck]:
        """Return pucks with a defined sample changer location."""
        self.parcels = []
        try:
            self.parcels = self._icat_client.get_parcels_by(
                investigation_id=investigation_id
            )
            logger.debug(
                "Successfully retrieved %d parcels for investigation %s",
                len(self.parcels),
                investigation_id,
            )
        except Exception:
            logger.exception(
                "Failed to retrieve parcels for investigation %s", investigation_id
            )

        return [
            LoadedPuck(
                **puck.model_dump(),
                puck_name=puck.name,
                parcel_name=parcel.name,
                parcel_id=parcel.id,
            )
            for parcel in self.parcels
            for puck in parcel.content
            if puck.sample_changer_location is not None
        ]

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
            investigation_id = session.session_id

            logger.debug(
                "[ICATClient] get_samples: investigation_id=%s, proposal_name=%s",
                investigation_id,
                session.proposal_name,
            )

            self.sample_sheets = self.get_samples_by_investigation(
                investigation_id,
            )

            logger.debug(
                "[ICATClient] Retrieved %d sample sheets",
                len(self.sample_sheets),
            )

            # Filter for loaded pucks
            self.loaded_pucks = self._get_loaded_pucks(
                investigation_id,
            )
            logger.debug(
                "[ICATClient] Found %d loaded pucks",
                len(self.loaded_pucks),
            )

            sampleInformationList: List[icat_models.SampleInformation] = []
            # Download all sampleInformation for the investigation
            # This makes to perform a single call to the server instead of one per sample
            try:
                sampleInformationList = self._icat_client.get_sample_information_list_by(
                    investigation_id=str(investigation_id)
                )
            except Exception as e:
                logger.debug(
                    "No sample information found for investigation %s", e
                )

            # Extract and process samples from loaded pucks
            for puck in self.loaded_pucks:
                tracking_samples = puck.content
                msg = f"[ICATClient] Found puck {puck.name} at position "
                msg += f"{puck.sample_changer_location}, containing {len(puck.content)} samples"
                logger.debug(msg)
                for tracking_sample in tracking_samples:
                    sample = self.__to_sample(
                        tracking_sample, puck, sampleInformationList
                    )
                    self.samples.append(sample)

        except RuntimeError:
            logger.exception("[ICATClient] Error retrieving samples: %s")
        else:
            msg = f"[ICATClient] Total {len(self.samples)} samples read"
            logger.debug(msg)

            # MXCuBE Web expects containerSampleChangerLocation to be string
            for sample in self.samples:
                sample["containerSampleChangerLocation"] = str(
                    sample["containerSampleChangerLocation"]
                )        
        return self.samples
        

    def objectid_to_int(self, oid_str):
        return int(oid_str, 16)

    def int_to_objectid(self, i):
        return hex(i)[2:].zfill(24)

    def __add_download_path_to_processing_plan(
        self,
        processing_plan: List[icat_models.ExperimentPlanEntry],
        downloads: List[Download],
    ):
        file_path_lookup = {}
        group_paths = defaultdict(list)

        for download in downloads:
            file_path_lookup[download.filename] = download.path
            if download.groupName is not None:
                group_paths[download.groupName].append(download.path)

        # convert to json for legacy
        processing_plan_json = [item.to_dict() for item in processing_plan]

        # Enrich the processing_plan
        for item in processing_plan_json:
            key = item.get("key")
            value = item.get("value", {})
            if (
                key == "reference"
                and isinstance(value, str)
                and value in file_path_lookup
            ):
                item["value"] = {"filepath": file_path_lookup[value]}
            if key == "search_models":
                models = value
                if isinstance(models, str) and len(models) > 0:
                    try:
                        models = json.loads(models)
                    except json.JSONDecodeError:
                        logger.exception(
                            "[ICATClient] Error converting models to JSON. Input: %s",
                            models,
                        )
                        models = []
                for model in models:
                    group = model.get("pdb_group")
                    if group in group_paths:
                        model["file_paths"] = group_paths[group]
                item["value"] = models

        return processing_plan_json

    def _safe_json_loads(self, json_str):
        try:
            return json.loads(json_str)
        except Exception:
            return str(json_str)

    def __extract_sample_identifiers(
        self, tracking_sample: icat_models.Sample, puck: LoadedPuck
    ) -> dict:
        # Basic identifiers
        sample_name = tracking_sample.name

        # MXCuBE needs to be an integer while in DRAC is a ObjectId
        # Mongo @BES needs to be smaller then 8 bytes
        sample_id = int(str(self.objectid_to_int(tracking_sample.id))[-6:])
        # id to the sample sheet declared in the user portal
        sample_sheet_id = tracking_sample.sample_id
        msg = f"[ICATClient] Sample ids sample_id={sample_id} "
        msg += f"sample_sheet_id={sample_sheet_id} "
        msg += f"tracking_sample_id={tracking_sample.id}"
        logger.debug(msg)

        protein_acronym = self.__resolve_protein_acronym(sample_name, sample_sheet_id)

        return {
            "sampleName": sample_name,
            "sampleId": sample_id,
            "sample_sheet_id": sample_sheet_id,
            "trackingSampleId": tracking_sample.id,
            "proteinAcronym": protein_acronym,
            "sampleLocation": tracking_sample.sample_container_position,
            "containerCode": puck.name,
            "containerSampleChangerLocation": puck.sample_changer_location,
            "SampleTrackingParcel_name": puck.parcel_name,
            "SampleTrackingParcel_id": puck.parcel_id,
            "SampleTrackingContainer_id": puck.name,
            "SampleTrackingContainer_name": puck.id,
        }

    def __resolve_protein_acronym(self, sample_name: str, sample_sheet_id: str) -> str:
        """Return the sample sheet name when the ID matches; otherwise, use the sample name."""
        sample_sheet = next(
            (sample for sample in self.sample_sheets if sample.id == sample_sheet_id),
            None,
        )
        return sample_sheet.name if sample_sheet else sample_name

    def __experiment_plan_to_dict(
        self, experiment_plan: List[icat_models.ExperimentPlanEntry] | None
    ) -> dict[str, Any]:
        """Extract experiment plan values into a dictionary, using each item's key."""
        return {item.key: item.value.actual_instance for item in experiment_plan or []}

    def __prepare_processing_plan(
        self,
        tracking_sample: icat_models.ParcelItem,
        protein_acronym: str,
        sample_information: icat_models.SampleInformation | None,
    ) -> dict[str, Any]:
        if not tracking_sample.processing_plan or tracking_sample.processing_plan == []:
            return {}

        downloads: List[Download] = self.__download_resource(
            tracking_sample.sample_id, protein_acronym, sample_information
        )

        if downloads:
            try:
                return self.__add_download_path_to_processing_plan(
                    tracking_sample.processing_plan, downloads
                )
            except RuntimeError:
                logger.exception("Failed __add_download_path_to_processing_plan")
        return {
            item.key: (item.value.actual_instance if item.value is not None else None)
            for item in tracking_sample.processing_plan
        }

    def __download_resource(
        self,
        sample_sheet_id: str,
        protein_acronym: str,
        sample_information: icat_models.SampleInformation | None,
    ) -> List[Download]:
        cache_key = (sample_sheet_id, protein_acronym)
        logger.debug(f"Getting sample information for {protein_acronym}")
        if not sample_information:
            return []

        cached = self._downloads_cache.get(cache_key)

        # Validate cache by comparing resource count
        if cached and len(cached) == len(sample_information.resources):
            logger.debug(f"Reusing cached downloads for {cache_key}")
            return cached

        # Otherwise, re-download
        # create subfolder per protein acronym
        destination_folder = (
            Path(HWR.beamline.session.get_base_process_directory())
            / "processing_plan_resources"
            / protein_acronym
        )
        destination_folder.mkdir(parents=True, exist_ok=True)

        logger.debug(
            f"Download resource: sample_sheet_id={sample_sheet_id} "
            f"destination_folder={destination_folder}"
        )

        downloads = self._download_resources(
            sample_sheet_id,
            sample_information.resources,
            destination_folder,
            "",
        )

        logger.debug(f"Downloaded {len(downloads)} resources")
        self._downloads_cache[cache_key] = downloads
        return downloads

    def __to_sample(
        self,
        tracking_sample: icat_models.ParcelItem,
        puck: LoadedPuck,
        sample_information_list: List[icat_models.SampleInformation],
    ) -> dict[str, Any]:
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

        Returns:
            dict: A dictionary representing the standardized internal sample format.
        """
        sample_id_info = self.__extract_sample_identifiers(tracking_sample, puck)

        # converts experiment plan from list of icat_models.ExperimentPlanEntry to a dictionary
        experiment_plan = self.__experiment_plan_to_dict(
            tracking_sample.experiment_plan
        )

        sample_information = next(
            (
                sample
                for sample in sample_information_list
                if sample.sample_id == tracking_sample.sample_id
            ),
            None,
        )
        processing_plan = self.__prepare_processing_plan(
            tracking_sample,
            sample_id_info[PROTEIN_ACRONYM_KEY],
            sample_information,
        )
        # This still keeps compatible with ISPyB legacy code
        return {
            **sample_id_info,
            "experimentType": experiment_plan.get("workflowType"),
            "crystalSpaceGroup": experiment_plan.get("forceSpaceGroup"),
            "diffractionPlan": {},
            "experimentPlan": self.__experiment_plan_to_dict(
                tracking_sample.experiment_plan
            ),
            "processingPlan": processing_plan,
            "comments": tracking_sample.comments,
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

        self.use_set_endstation_name = self.get_property(
            "use_set_endstation_name",
            False,  # noqa: FBT003
        )

        if self.use_set_endstation_name:
            HWR.beamline.session.set_endstation_name(
                self.session_manager.active_session.beamline_name.lower()
            )

        return self.session_manager.active_session

    def allow_session(self, session: Session):
        self.active_session = session
        logger.debug("allow_session investigationId=%s", session.session_id)
        self._icat_client.reschedule_investigation(session.session_id)

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

    def __get_all_investigations(self) -> List[icat_models.InvestigationDetails]:
        """Returns all investigations by user. An investigation corresponds to
        one experimental session. It returns an empty array in case of error"""
        self.investigations = []
        
        try:
            msg = f"__get_all_investigations before={self.before_offset_days} "
            msg += f"after={self.after_offset_days} "
            msg += f"beamline={self.override_beamline_name} "
            msg += f"isInstrumentScientist={self.icat_session.is_instrument_scientist} "
            msg += f"isAdministrator={self.icat_session.is_administrator} "
            msg += f"compatible_beamlines={self.compatible_beamlines}"
            logger.debug(msg)

            if self.icat_session is not None and (
                self.icat_session.is_administrator
                or self.icat_session.is_instrument_scientist
            ):
                # Setting up of the session done by admin or staff
                self.investigations = self._icat_client.get_investigations_by(
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

                self.investigations = self._icat_client.get_investigations_by(
                    ids=[self.session_manager.active_session.session_id],
                )
            else:
                self.investigations = self._icat_client.get_investigations_by(
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

    def _get_data_portal_url(
        self, investigation: icat_models.InvestigationDetails
    ) -> str:
        try:
            return (
                self.data_portal_url.replace("{id}", str(investigation.id))
                if self.data_portal_url is not None
                else ""
            )
        except Exception:
            return ""

    def _get_logbook_url(self, investigation: icat_models.InvestigationDetails) -> str:
        try:
            return (
                self.logbook_url.replace("{id}", str(investigation.id))
                if self.logbook_url is not None
                else ""
            )
        except Exception:
            return ""

    def _get_user_portal_url(
        self, investigation: icat_models.InvestigationDetails
    ) -> str:
        try:
            return (
                self.user_portal_url.replace(
                    "{id}", str(investigation.parameters["Id"])
                )
                if self.user_portal_url is not None
                and investigation.parameters["Id"] is not None
                else ""
            )
        except Exception:
            return ""

    def __get_proposal_number_by_investigation(
        self, investigation: icat_models.InvestigationDetails
    ) -> str:
        """
        Given an investigation it returns the proposal number.
        Example: investigation["name"] = "MX-1234"
        returns: 1234

        TODO: this might not work for all type of proposals (example: TEST proposals)
        """
        return investigation.name.replace(investigation.type.name, "").replace("-", "")

    def __to_session(self, investigation: icat_models.InvestigationDetails) -> Session:
        """This methods converts a ICAT investigation into a session"""        
        actual_start_date = (
            investigation.parameters["actualStartDate"]
            if "actualStartDate" in investigation.parameters
            else investigation.start_date
        )
        actual_end_date = (
            investigation.parameters["actualEndDate"]
            if "actualEndDate" in investigation.parameters
            else investigation.end_date
        )

        instrument_name = investigation.instrument.name
        # If session has been rescheduled new date is overwritten
        return Session(
            code=investigation.type.name,
            number=self.__get_proposal_number_by_investigation(investigation),
            title=investigation.title,
            session_id=str(investigation.id),
            proposal_id=str(investigation.id),
            proposal_name=investigation.name,
            beamline_name=instrument_name,
            comments="",
            start_datetime=investigation.start_date,
            start_date=self._string_to_date(investigation.start_date),
            start_time=self._string_to_time(investigation.start_date),
            end_datetime=investigation.end_date,
            end_date=self._string_to_date(investigation.end_date),
            end_time=self._string_to_time(investigation.end_date),
            actual_start_date=self._string_to_date(actual_start_date),
            actual_start_time=self._string_to_time(actual_start_date),
            actual_end_date=self._string_to_date(actual_end_date),
            actual_end_time=self._string_to_time(actual_end_date),
            nb_shifts="3",
            scheduled=str(self.is_scheduled_on_host_beamline(instrument_name)),
            is_scheduled_time=self.is_scheduled_now(actual_start_date, actual_end_date),
            is_scheduled_beamline=self.is_scheduled_on_host_beamline(instrument_name),
            data_portal_URL=self._get_data_portal_url(investigation),
            user_portal_URL=self._get_user_portal_url(investigation),
            logbook_URL=self._get_logbook_url(investigation),
            is_rescheduled=bool("actualEndDate" in investigation.parameters),
            volume=investigation.parameters.get("__volume", "0"),
            sample_count=investigation.parameters.get("__sampleCount", "0"),
            dataset_count= investigation.parameters.get("__datasetCount", "0"),
        )

    def get_full_user_name(self):
        return self.icat_session.full_name

    def get_user_name(self):
        return self.icat_session.username

    def to_sessions(
        self, investigations: List[icat_models.InvestigationDetails]
    ) -> List[Session]:
        sessions =  [self.__to_session(investigation) for investigation in investigations]
        return sessions

    def get_samples_by_investigation(
        self, investigation_id: str
    ) -> List[icat_models.Sample]:
        """Return the sample records associated with an investigation."""
        samples_List = []
        try:
            samples_List: List[icat_models.Sample] = self._icat_client.get_samples_by(
                investigation_id=investigation_id
            )
            msg = f"Successfully retrieved {len(samples_List)} samples"
            logger.debug(msg)
        except Exception:
            logger.exception("Failed on get_samples_by_investigation")

        return samples_List

    def echo(self):
        """Mockup for the echo method."""
        return True

    def is_connected(self):
        return self.login_ok

    def find_sample_by_sample_id(self, sample_id):
        return next(
            (
                sample
                for sample in self.samples
                if str(sample["limsID"]) == str(sample_id)
            ),
            None,
        )

    def store_beamline_setup(self, session_id: str, bl_config_dict: dict):
        pass

    def store_image(self, image_dict: dict):
        pass

    def store_common_data(
        self, datacollection_dict: dict
    ) -> Tuple[icat_models.IcatDatasetParameters, dict]:
        """Fill in the pydantic model fields common to all the data
        collection techniques.
        Args:
            datacollection_dict(dict): dictionarry from the data collection.

        Returns:
            A tuple ``(params, extra)``.
            ``params`` is a partially-filled ``icat_models.IcatDatasetParameters.blank()`` instance.
            ``extra`` holds flat ICAT keys with no corresponding model field.
        """
        investigation_id, investigation_name = self._get_investigation_info()
        actual_instrument = self._get_actual_instrument()
        return DataCollectionMetadataGatherer.gather_common_metadata(
            datacollection_dict,
            investigation_id=investigation_id,
            investigation_name=investigation_name,
            actual_instrument=actual_instrument,
        )

    def _get_investigation_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Return the (id, proposal name) of the currently active ICAT
        investigation/session, or (None, None) if there is none."""
        investigation_id = None
        investigation_name = None
        if self.session_manager.active_session.session_id:
            investigation_id = self.session_manager.active_session.session_id
            session = self.get_session_by_id(investigation_id)
            if session is not None:
                investigation_name = session.proposal_name
        return investigation_id, investigation_name

    def _get_actual_instrument(self) -> Optional[str]:
        """Return the beamline name to report as "actualInstrument" when
        the active session has been rescheduled to a different beamline
        than the one it was originally allocated on, or None otherwise or
        on failure to determine it."""
        try:
            if (
                self.active_session is None
                or not self.active_session.is_scheduled_beamline
            ):
                return HWR.beamline.session.beamline_name
        except RuntimeError as e:
            logger.warning("Failed to set actualInstrument. %s", e)
        return None

    def __format_datetime(self, value: str) -> str:
        try:
            return (
                datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                .replace(tzinfo=ZoneInfo("Europe/Paris"))
                .isoformat(timespec="microseconds")
            )
        except (ValueError, TypeError):
            self.log.exception("Cannot parse datetime: %s", value)
            return value

    def store_energy_scan(self, energyscan_dict: dict):
        try:
            params, extra = self.store_common_data(energyscan_dict)
            try:
                beamline = self._get_scheduled_beamline()
                msg = f"Dataset Beamline={beamline} "
                msg += f"Current Beamline={HWR.beamline.session.beamline_name}"
                self.log.info(msg)
            except Exception:
                self.log.exception(
                    "Failed to get _get_scheduled_beamline",
                )
            _session = HWR.beamline.session
            proposal = f"{_session.proposal_code}{_session.proposal_number}"

            directory = Path(energyscan_dict["scanFileFullPath"]).parent.parent

            start_time = energyscan_dict.get("startTime", "")
            end_time = energyscan_dict.get("endTime", "")

            if start_time:
                params.start_time = self.__format_datetime(start_time)

            if end_time:
                params.end_time = self.__format_datetime(end_time)

            params.title = str(directory.name)
            params.folder_path = str(directory)

            mx = params.MX
            mx.directory = str(directory)
            mx.exposureTime = energyscan_dict.get("exposureTime")
            mx.scanType = "energy_scan"

            params.instrument.detector01.model = energyscan_dict.get(
                "fluorescenceDetector"
            )

            params = params.finalize()
            metadata = params.to_icat_dict()
            metadata.update(extra)
            # No icat_esrf_definitions model field exists yet for these
            # energy-scan-specific values, so they stay as plain flat keys.
            metadata.update(
                {
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

            # ontologies
            try:
                tech = technique.get_technique_metadata("MX", "MAD")
                metadata.update(tech.get_dataset_metadata())
            except (NameError, TypeError):
                self.log.warning("No technique added to the metadata")

            self._icat_client.store_dataset(
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
            params, extra = self.store_common_data(xfespectrum_dict)
            try:
                beamline = self._get_scheduled_beamline()
                msg = f"Dataset Beamline={beamline} "
                msg += f"Current Beamline={HWR.beamline.session.beamline_name}"
                self.log.info(msg)
            except Exception:
                self.log.exception(
                    "Failed to get _get_scheduled_beamline",
                )
            _session = HWR.beamline.session
            proposal = f"{_session.proposal_code}{_session.proposal_number}"

            directory = Path(xfespectrum_dict["filename"]).parent

            start_time = xfespectrum_dict.get("startTime", "")
            end_time = xfespectrum_dict.get("endTime", "")

            if start_time:
                params.start_time = start_time
            if end_time:
                params.end_time = end_time

            params.title = str(directory.name)
            params.folder_path = str(directory)

            mx = params.MX
            mx.directory = str(directory)
            mx.exposureTime = xfespectrum_dict.get("exposureTime")
            mx.scanType = "xrf"

            params = params.finalize()
            metadata = params.to_icat_dict()
            metadata.update(extra)

            # ontologies
            try:
                tech = technique.get_technique_metadata("MX", "XRF")
                metadata.update(tech.get_dataset_metadata())
            except (NameError, TypeError):
                self.log.warning("No technique added to the metadata")

            self._icat_client.store_dataset(
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

    def __get_sample_information_by(
        self, sample_id: str
    ) -> Optional[icat_models.SampleInformation]:
        """
        Fetches sample metadata and associated resources based on the sample ID.

        Parameters:
            sample_id (str): The unique identifier for the sample.

        Returns:
            Optional[SampleInformation]: Returns a SampleInformation object or None.
        """
        try:
            sampleInformationList: List[icat_models.SampleInformation] = (
                self._icat_client.get_sample_information_list_by(sample_id=str(sample_id))
            )
            if sampleInformationList is not None and len(sampleInformationList) > 0:
                return sampleInformationList[0]
            return None

        except icat_errors.ApiException as e:
            if e.status == 404:
                logger.info("Sample %s not found (404)", sample_id)
            else:
                logger.exception("HTTP error for sample %s", sample_id)
        except ValidationError:
            logger.exception("Invalid response format for sample %s", sample_id)
        return None

    def _download_resources(
        self,
        sample_id: str,
        resources: List[icat_models.FileResource] | None,
        output_folder: str,
        sample_name: str,
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
        # Snapshot once: self._icat_client resolves through the shared
        # "active user" and each download below yields to other greenlets,
        # so re-reading the property mid-loop could switch identity if
        # another user takes control while this loop is still running.
        icat_client = self._icat_client
        downloaded_files: List[Download] = []
        for resource in resources:
            resource_folder = Path(output_folder) / sample_name
            resource_folder = Path(resource_folder) / (resource.group_name or "")
            resource_folder.mkdir(
                parents=True,
                exist_ok=True,
            )  # Make sure the folder exists

            try:
                result = icat_client.download_file_by(str(sample_id), resource.id)
                output_path = Path(resource_folder / resource.filename)
                with output_path.open("wb") as f:
                    f.write(result)

                # Create a new Download instance with updated path
                downloaded = Download(
                    path=str(output_path),
                    filename=resource.filename,
                    groupName=resource.group_name,
                )
                downloaded_files.append(downloaded)
                logger.info("Downloaded %s to %s", resource.filename, downloaded.path)

            except icat_errors.ApiException:
                logger.exception("Failed to download %s", resource.filename)

        return downloaded_files

    def finalize_data_collection(self, datacollection_dict):
        logger.info("Storing datacollection in ICAT")

        try:
            gathered = self._gather_metadata(datacollection_dict)
        except LimsMetadataGatherError as e:
            logger.warning("Failed to gather metadata for ICAT. %s", e)
            return

        try:
            self._write_metadata(gathered)
        except LimsMetadataWriteError as e:
            logger.warning("Failed to write ICAT metadata to disk. %s", e)

        try:
            self._upload_metadata(gathered)
        except LimsMetadataUploadError as e:
            logger.warning("Failed uploading to ICAT. %s", e)
        else:
            logger.debug("Done uploading to ICAT")

    def _gather_metadata(self, datacollection_dict: dict) -> dict:
        """Assemble the ICAT metadata for a finished data collection.

        Delegates the actual assembly to DataCollectionMetadataGatherer,
        which has no knowledge of ICAT/ISPyB or of this class - here we only
        wire it up with the bits of state/behavior it needs from this LIMS
        object, and translate its failures into the typed exception this
        class's callers expect.

        Returns a dict with keys "metadata", "file_metadata", "directory",
        "dataset_name", "beamline", "proposal" and "snapshot_paths",
        consumed by _write_metadata and _upload_metadata.
        """
        try:
            params, extra = self.store_common_data(datacollection_dict)

            scheduled_beamline = None
            try:
                scheduled_beamline = self._get_scheduled_beamline()
            except RuntimeError as e:
                logger.warning("Failed to get scheduled beamline name. %s", e)

            return DataCollectionMetadataGatherer().gather(
                datacollection_dict,
                beamline_config=self.beamline_config,
                params=params,
                extra=extra,
                scheduled_beamline=scheduled_beamline,
            )
        except Exception as e:
            raise LimsMetadataGatherError(str(e)) from e

    def _write_metadata(self, gathered: dict) -> None:
        """Write metadata.json and copy the gathered snapshot files into the
        gallery directory for a finished data collection.

        Pure file-system I/O - all metadata assembly already happened in
        DataCollectionMetadataGatherer.
        """
        directory = gathered["directory"]
        try:
            icat_metadata_path = Path(directory) / "metadata.json"
            with Path(icat_metadata_path).open("w") as f:
                f.write(json.dumps(gathered["file_metadata"], indent=4))

            # Create ICAT gallery
            try:
                gallery_path = directory / "gallery"
                gallery_path.mkdir(mode=0o755, exist_ok=True)
                for snapshot_path in gathered["snapshot_paths"]:
                    logger.debug("Copying %s to gallery", snapshot_path)
                    shutil.copy(snapshot_path, gallery_path)
            except RuntimeError as e:
                logger.warning("Failed to create gallery. %s", e)
        except Exception as e:
            raise LimsMetadataWriteError(str(e)) from e

    def _upload_metadata(self, gathered: dict) -> None:
        """Upload the gathered ICAT metadata for a finished data collection."""
        try:
            self._icat_client.store_dataset(
                beamline=gathered["beamline"],
                proposal=gathered["proposal"],
                dataset=gathered["dataset_name"],
                path=str(gathered["directory"]),
                metadata=gathered["metadata"],
            )
        except Exception as e:
            raise LimsMetadataUploadError(str(e)) from e

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
        pass
