import json
import logging
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
        logging.getLogger("HWR").info("Storing data to ICAT")
        collection_parameters = parameters["collection_parameters"]
        beamline_parameters = parameters["beamline_parameters"]
        data_path = parameters["data_path"]
        extra_lims_values = parameters["extra_lims_values"]

        try:
            data = {
                "MX_scanType": "SSX-Jet",
                "MX_beamShape": beamline_parameters.beam_shape,
                "MX_beamSizeAtSampleX": beamline_parameters.beam_size_x,
                "MX_beamSizeAtSampleY": beamline_parameters.beam_size_y,
                "MX_detectorDistance": beamline_parameters.detector_distance,
                "MX_directory": data_path,
                "MX_exposureTime": collection_parameters.user_collection_parameters.exp_time,
                "MX_flux": extra_lims_values.flux_start,
                "MX_fluxEnd": extra_lims_values.flux_end,
                "MX_numberOfImages": collection_parameters.collection_parameters.num_images,
                "MX_resolution": beamline_parameters.resolution,
                "MX_transmission": beamline_parameters.transmission,
                "MX_xBeam": beamline_parameters.beam_x,
                "MX_yBeam": beamline_parameters.beam_y,
                "Sample_name": collection_parameters.path_parameters.prefix,
                "InstrumentMonochromator_wavelength": beamline_parameters.wavelength,
                "chipModel": extra_lims_values.chip_model,
                "monoStripe": extra_lims_values.mono_stripe,
                "energyBandwidth": beamline_parameters.energy_bandwidth,
                "detector_id": HWR.beamline.detector.get_property("detector_id"),
                "experimentType": collection_parameters.common_parameters.type,
            }

            data.update(collection_parameters.user_collection_parameters.dict())
            data.update(collection_parameters.collection_parameters.dict())

            self.icatClient.store_dataset(
                beamline="ID29",
                proposal=f"{HWR.beamline.session.proposal_code}{HWR.beamline.session.proposal_number}",
                dataset=collection_parameters.path_parameters.prefix,
                path=data_path,
                metadata=data,
            )

            icat_metadata_path = pathlib.Path(data_path) / "metadata.json"
            with open(icat_metadata_path, "w") as f:
                f.write(json.dumps(data, indent=4))
                logging.getLogger("HWR").info(f"Wrote {icat_metadata_path}")

        except Exception as e:
            logging.getLogger("HWR").exception("Failed uploading to ICAT (%s)", e)
