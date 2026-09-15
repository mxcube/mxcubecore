import json
import pathlib

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractLims import (
    LimsMetadataGatherError,
    LimsMetadataUploadError,
    LimsMetadataWriteError,
)
from mxcubecore.HardwareObjects.ICATLIMS import ICATLIMS


class SsxDataCollectionMetadataGatherer:
    """Assembles the metadata for a finished SSX data collection, in the
    format expected by ICAT (via pyicat-plus) and metadata.json.

    Independent of any LIMS hardware object instance or of how the
    resulting metadata is subsequently written to disk or uploaded - it
    only reads beamline state and the collection's own parameters.
    """

    def gather(self, parameters: dict) -> dict:
        """Assemble the metadata for a finished SSX data collection.

        Returns a dict with keys "data", "rounded_data", "data_path",
        "beamline", "proposal" and "dataset_name".
        """
        collection_parameters = parameters["collection_parameters"]
        beamline_parameters = parameters["beamline_parameters"]
        data_path = parameters["data_path"]
        extra_lims_values = parameters["extra_lims_values"]
        sample = parameters["sample"]

        path_parameters = collection_parameters.path_parameters
        horizontal_spacing = 0
        vertical_spacing = 0

        if hasattr(
            collection_parameters.user_collection_parameters, "horizontal_spacing"
        ):
            horizontal_spacing = (
                collection_parameters.user_collection_parameters.horizontal_spacing
            )

        if hasattr(
            collection_parameters.user_collection_parameters, "vertical_spacing"
        ):
            vertical_spacing = (
                collection_parameters.user_collection_parameters.vertical_spacing
            )

        data = {
            "SSXJet_speed": 0,
            "SSXJet_size": 0,
            "SSXChip_horizontal_spacing": horizontal_spacing,
            "SSXChip_vertical_spacing": vertical_spacing,
            "SSXChip_row_number": extra_lims_values.number_of_rows,
            "SSXChip_column_number": extra_lims_values.number_of_columns,
            "SSXChip_model": 0,
            "InstrumentLaser01_energy": 0,
            "InstrumentLaser01_wavelength": 0,
            "InstrumentLaser01_repetition_rate": 0,
            "InstrumentLaser01_delay": 0,
            "InstrumentLaser01_name": 0,
            "InstrumentLaser01_pulse_width": 0,
            "InstrumentDetector01_frame_time": 0,
            "Sample_support": 0,
            "SampleProtein_acronym": sample.protein_acronym,
            "MX_wavelength": beamline_parameters.wavelength,
            "MX_resolution_at_corner": 0,
            "MX_scanType": "datacollection",
            "MX_beamShape": beamline_parameters.beam_shape,
            "MX_beamSizeAtSampleX": beamline_parameters.beam_size_x,
            "MX_beamSizeAtSampleY": beamline_parameters.beam_size_y,
            "MX_detectorDistance": beamline_parameters.detector_distance,
            "MX_directory": data_path,
            "MX_exposureTime": (
                collection_parameters.user_collection_parameters.exp_time
            ),
            "MX_flux": extra_lims_values.flux_start,
            "MX_fluxEnd": extra_lims_values.flux_end,
            "MX_numberOfImages": (
                collection_parameters.collection_parameters.num_images
            ),
            "MX_resolution": beamline_parameters.resolution,
            "MX_transmission": beamline_parameters.transmission,
            "MX_xBeam": beamline_parameters.beam_x,
            "MX_yBeam": beamline_parameters.beam_y,
            "Project_name": path_parameters.prefix,
            "Sample_name": path_parameters.prefix,
            "scanNumber": 0,
            "InstrumentMonochromator_wavelength": beamline_parameters.wavelength,
            "chipModel": extra_lims_values.chip_model,
            "monoStripe": extra_lims_values.mono_stripe,
            "energyBandwidth": beamline_parameters.energy_bandwidth,
            "detector_id": HWR.beamline.detector.get_property("detector_id"),
            "experimentType": extra_lims_values.experiment_type,
            "scanType": extra_lims_values.experiment_type,
            "Experiment_name": path_parameters.experiment_name,
        }

        data.update(collection_parameters.user_collection_parameters.dict())
        data.update(collection_parameters.collection_parameters.dict())

        # Round float values to 3 decimal places
        rounded_data = {
            key: round(value, 3) if isinstance(value, float) else value
            for key, value in data.items()
        }

        return {
            "data": data,
            "rounded_data": rounded_data,
            "data_path": data_path,
            "beamline": HWR.beamline.session.beamline_name.lower(),
            "proposal": (
                f"{HWR.beamline.session.proposal_code}"
                f"{HWR.beamline.session.proposal_number}"
            ),
            "dataset_name": path_parameters.prefix,
        }


class SSXICATLIMS(ICATLIMS):
    """
    ICAT+ client for SSX.
    """

    def store_data_collection(self, parameters, bl_config=None):
        pass

    def update_data_collection(self, parameters):
        pass

    def finalize_data_collection(self, parameters):
        self.log.info("Storing data to ICAT")

        try:
            gathered = self._gather_ssx_metadata(parameters)
        except LimsMetadataGatherError as e:
            self.log.warning("Failed to gather metadata for ICAT. %s", e)
            return

        try:
            self._upload_ssx_metadata(gathered)
        except LimsMetadataUploadError as e:
            self.log.warning("Failed uploading to ICAT. %s", e)

        try:
            self._write_ssx_metadata(gathered)
        except LimsMetadataWriteError as e:
            self.log.warning("Failed to write ICAT metadata to disk. %s", e)

    def _gather_ssx_metadata(self, parameters: dict) -> dict:
        """Assemble the ICAT metadata for a finished SSX data collection.

        Delegates the actual assembly to SsxDataCollectionMetadataGatherer,
        which has no knowledge of ICAT/ISPyB or of this class, and
        translates its failures into the typed exception this class's
        callers expect.

        Returns a dict with keys "data", "rounded_data", "data_path",
        "beamline", "proposal" and "dataset_name", consumed by
        _upload_ssx_metadata and _write_ssx_metadata.
        """
        try:
            return SsxDataCollectionMetadataGatherer().gather(parameters)
        except Exception as e:
            raise LimsMetadataGatherError(str(e)) from e

    def _upload_ssx_metadata(self, gathered: dict) -> None:
        """Upload the gathered ICAT metadata for a finished SSX data
        collection."""
        try:
            self._icat_client.store_dataset(
                beamline=gathered["beamline"],
                proposal=gathered["proposal"],
                dataset=gathered["dataset_name"],
                path=gathered["data_path"],
                metadata=gathered["rounded_data"],
            )
        except Exception as e:
            raise LimsMetadataUploadError(str(e)) from e

    def _write_ssx_metadata(self, gathered: dict) -> None:
        """Write metadata.json to disk for a finished SSX data collection."""
        try:
            icat_metadata_path = pathlib.Path(gathered["data_path"]) / "metadata.json"
            with open(icat_metadata_path, "w") as f:
                f.write(json.dumps(gathered["data"], indent=4))
                self.log.info(f"Wrote {icat_metadata_path}")
        except Exception as e:
            raise LimsMetadataWriteError(str(e)) from e
