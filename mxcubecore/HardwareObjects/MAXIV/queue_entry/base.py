import logging
from pathlib import Path
from mxcubecore.utils.units import mm_to_meter
from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry
from mxcubecore import HardwareRepository as HWR


log = logging.getLogger("queue_exec")


def restore_beamline():
    collect = HWR.beamline.collect

    #
    # close fast shutter
    #
    try:
        collect.close_fast_shutter()
    except Exception:
        log.exception("Error while closing fast shutter.")

    #
    # close detector cover
    #
    try:
        collect.close_detector_cover()
    except Exception:
        log.exception("Error while closing detector cover.")


class AbstractSsxQueueEntry(BaseQueueEntry):
    """
    Contains common code utilized by 'SSX Injector' and 'SSX Time Resolved Injector' queue
    entries.
    """

    def pre_execute(self):
        super().pre_execute()

        #
        # this is probably wrong approach, but let's use it for now
        #
        # make sure the 'run number' of the task is increased each time
        # we launch a new data collection run
        #
        path_template = self._data_model.acquisitions[0].path_template
        queue_model = HWR.beamline.queue_model
        path_template.run_number = queue_model.get_next_run_number(path_template)

    def prepare_data_collection(self, num_triggers=1):
        """
        Prepare beamline for a SSX data collection, i.e.:

        - move detector
        - configure detector
        - set MD3 into correct phase/mode
        - open detector cover
        - open fast shutter
        """

        def get_params():
            td = self._data_model._task_data
            dc_dict = self._data_model.as_dict()
            uc_params = td.user_collection_parameters
            col_params = td.collection_parameters

            return (
                uc_params.exp_time,
                uc_params.num_images,
                uc_params.cellA,
                uc_params.cellB,
                uc_params.cellC,
                uc_params.cellAlpha,
                uc_params.cellBeta,
                uc_params.cellGamma,
                col_params.energy,
                col_params.resolution,
                dc_dict["path"],
                td.path_parameters.prefix,
                dc_dict["run_number"],
            )

        def get_hwobjs():
            beamline = HWR.beamline
            return beamline.detector, beamline.collect, beamline.diffractometer

        #
        # fetch task parameters from model object
        #
        (
            exp_time,
            num_images,
            cell_a,
            cell_b,
            cell_c,
            cell_alpha,
            cell_beta,
            cell_gamma,
            energy,
            resolution,
            root_dir,
            path_prefix,
            run_number,
        ) = get_params()

        detector, collect, diffractometer = get_hwobjs()

        #
        # open safety shutter
        #
        collect.open_safety_shutter()

        #
        # move detector for selected resolution
        #
        collect.set_resolution(resolution)

        #
        # configure and arm detector
        #
        beam_center_x, beam_center_y = collect.get_beam_centre()
        det_cfg = detector.col_config
        det_cfg["NbImages"] = num_images
        det_cfg["OmegaStart"] = 0.0
        det_cfg["OmegaIncrement"] = 0.0
        det_cfg["BeamCenterX"] = beam_center_x
        det_cfg["BeamCenterY"] = beam_center_y
        det_cfg["DetectorDistance"] = mm_to_meter(collect.get_detector_distance())
        det_cfg["NbTriggers"] = num_triggers
        det_cfg["CountTime"] = exp_time
        det_cfg["FilenamePattern"] = str(Path(root_dir, f"{path_prefix}_{run_number}"))
        det_cfg["UnitCellA"] = cell_a
        det_cfg["UnitCellB"] = cell_b
        det_cfg["UnitCellC"] = cell_c
        det_cfg["UnitCellAlpha"] = cell_alpha
        det_cfg["UnitCellBeta"] = cell_beta
        det_cfg["UnitCellGamma"] = cell_gamma
        detector.prepare_acquisition(det_cfg)

        #
        # change MD3 phase to data collection mode,
        # this moves in beam stop
        #
        diffractometer.set_phase("DataCollection")

        #
        # open detector cover and fast shutter
        #
        collect.open_detector_cover()
        collect.open_fast_shutter()

    def stop(self):
        super().stop()
        log.info("Aborting acquisition.")
        HWR.beamline.detector.stop_acquisition()
