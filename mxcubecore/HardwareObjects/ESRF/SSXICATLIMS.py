import json
import pathlib

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ICATLIMS import ICATLIMS


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
        collection_parameters = parameters["collection_parameters"]
        beamline_parameters = parameters["beamline_parameters"]
        data_path = parameters["data_path"]
        extra_lims_values = parameters["extra_lims_values"]
        sample = parameters["sample"]

        horizontal_spacing = 0
        vertical_spacing = 0

        if hasattr(collection_parameters.user_collection_parameters, "horizontal_spacing"):
            horizontal_spacing = collection_parameters.user_collection_parameters.horizontal_spacing

        if hasattr(collection_parameters.user_collection_parameters, "vertical_spacing"):
            vertical_spacing = collection_parameters.user_collection_parameters.vertical_spacing

        try:
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
                "Project_name": collection_parameters.path_parameters.prefix,
                "Sample_name": collection_parameters.path_parameters.prefix,
                "scanNumber": 0,
                "InstrumentMonochromator_wavelength": beamline_parameters.wavelength,
                "chipModel": extra_lims_values.chip_model,
                "monoStripe": extra_lims_values.mono_stripe,
                "energyBandwidth": beamline_parameters.energy_bandwidth,
                "detector_id": HWR.beamline.detector.get_property("detector_id"),
                "experimentType": collection_parameters.common_parameters.type,
                "Experiment_name": collection_parameters.path_parameters.experiment_name,
            }

            data.update(collection_parameters.user_collection_parameters.dict())
            data.update(collection_parameters.collection_parameters.dict())

            # Round float values to 3 decimal places
            rounded_data = {
                key: round(value, 3) if isinstance(value, float) else value
                for key, value in data.items()
            }

            self.icatClient.store_dataset(
                beamline=HWR.beamline.session.beamline_name.lower(),
                proposal=f"{HWR.beamline.session.proposal_code}{HWR.beamline.session.proposal_number}",
                dataset=collection_parameters.path_parameters.prefix,
                path=data_path,
                metadata=rounded_data,
            )

            rounded_data.pop("endDate")
            rounded_data.pop("startDate")

            icat_metadata_path = pathlib.Path(data_path) / "metadata.json"
            with open(icat_metadata_path, "w") as f:
                f.write(json.dumps(data, indent=4))
                self.log.info(f"Wrote {icat_metadata_path}")

        except Exception as e:
            self.log.exception("Failed uploading to ICAT (%s)", e)
