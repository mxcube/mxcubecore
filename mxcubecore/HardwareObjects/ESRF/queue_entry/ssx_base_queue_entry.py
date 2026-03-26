import contextlib
import datetime
import json
import logging
import os
import subprocess
import xmlrpc.client

import gevent
from devtools import debug
from ewoksjob.client import submit
from pydantic import (
    BaseModel,
    Field,
)
from typing_extensions import (
    Literal,
    Union,
)

from mxcubecore import HardwareRepository as HWR
from mxcubecore.model.common import (
    BeamlineParameters,
    CommonCollectionParamters,
    ISPYBCollectionParameters,
    LegacyParameters,
    PathParameters,
    StandardCollectionParameters,
)
from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry

DEFAULT_MAX_FREQ = 925


class SSXPathParameters(PathParameters):
    use_experiment_name: bool = Field(
        True, description="Whether to use the experiment name in the data path"
    )


class BaseUserCollectionParameters(BaseModel):
    exp_time: float = Field(75e-6, gt=0, lt=1, unit="s")
    sub_sampling: Literal[1, 2, 4, 6, 8] = Field(1)
    take_pedestal: bool = Field(True)
    reject_empty_frames: bool = Field(True)

    frequency: float = Field(
        float(HWR.beamline.diffractometer.get_property("max_freq", DEFAULT_MAX_FREQ)),
        unit="Hz",
    )


class SsxBaseQueueTaskParameters(BaseModel):
    path_parameters: SSXPathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    legacy_parameters: LegacyParameters
    lims_parameters: Union[ISPYBCollectionParameters, None]

    def update_dependent_fields(field_data):
        return {}

    @staticmethod
    def ui_schema():
        return json.dumps(
            {
                "ui:order": [
                    "num_images",
                    "exp_time",
                    "osc_range",
                    "osc_start",
                    "resolution",
                    "transmission",
                    "energy",
                    "vertical_spacing",
                    "horizontal_spacing",
                    "nb_lines",
                    "nb_samples_per_line",
                    "motor_top_left_x",
                    "motor_top_left_y",
                    "motor_top_left_z",
                    "motor_top_right_x",
                    "motor_top_right_y",
                    "motor_top_right_z",
                    "motor_bottom_left_x",
                    "motor_bottom_left_y",
                    "motor_bottom_left_z",
                    "chip_type",
                    "take_pedestal",
                    "sub_sampling",
                    "*",
                ],
                "ui:submitButtonOptions": {
                    "norender": "true",
                },
                "sub_sampling": {"ui:readonly": "true"},
                "frequency": {"ui:readonly": "true"},
            }
        )


class SsxBaseQueueEntry(BaseQueueEntry):
    """
    Defines common SSX collection methods.
    """

    def __init__(self, view, data_model):
        super().__init__(view=view, data_model=data_model)
        self._beamline_values = None
        self._use_nicoproc = False
        self._use_besproc = False
        self._processing_host = "http://lid29control-2:9998"
        self._current_data_path = None
        self._current_process_path = None

        self.__pedestal_task = None
        self.__stop_req = False

    def get_data_path(self):
        return self._current_data_path

    def get_process_path(self):
        return self._current_process_path

    def take_pedestal(self):
        params = self._data_model._task_data.user_collection_parameters
        if params.take_pedestal:
            try:
                self._take_pedestal_func()
            except Exception as e:
                logging.getLogger("user_level_log").exception(
                    f"Error taking pedestal: {e}"
                )
                raise

        try:
            HWR.beamline.control.LDetX.wait_move()
        except Exception:
            if HWR.beamline.control.LDetX.position > 0:
                HWR.beamline.control.LDetX.move(0)

    def _take_pedestal_func(self):
        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        freq = self._data_model._task_data.user_collection_parameters.frequency
        sub_sampling = (
            self._data_model._task_data.user_collection_parameters.sub_sampling
        )

        effect_freq = freq / sub_sampling
        logging.getLogger("user_level_log").info(
            f"Frequency for pedestal: {freq} / {sub_sampling} = {effect_freq}"
        )

        data_root_path = self.get_data_path()

        packet_fifo_depth = 20000

        save_raw = False

        HWR.beamline.control.safshut_oh2.close()
        if not hasattr(HWR.beamline.control, "lima2_jungfrau_pedestal_scans"):
            HWR.beamline.control.load_script("id29_lima2.py")

        pedestal_dir = HWR.beamline.detector.find_next_pedestal_dir(
            data_root_path, "pedestal"
        )
        sls_detectors = "/users/blissadm/local/sls_detectors"
        lima2_path = f"{sls_detectors}/lima2"
        cl_source_path = f"{lima2_path}/processings/common/fai/kernels"

        disable_saving_list = []
        if not save_raw:
            disable_saving_list.append("raw")
        disable_saving = ",".join(disable_saving_list)

        saving_compression = {
            "raw": "zip",
            "average": "zip",
        }

        logging.getLogger("user_level_log").info(f"Storing pedestal in {pedestal_dir}")
        nb_retries = 2
        for _r in range(nb_retries):
            try:
                cmd = "mkdir --parents %s && chmod -R 755 %s" % (
                    pedestal_dir,
                    pedestal_dir,
                )
                subprocess.run(cmd, shell=True, check=True, close_fds=True)
            except Exception as e:
                logging.getLogger("user_level_log").warning(
                    "Error creating pedestal directory %s: %s", pedestal_dir, e
                )
            else:
                logging.getLogger("user_level_log").info(
                    "Created pedestal directory %s", pedestal_dir
                )
                break
        else:
            msg = "Failing creating pedestal directory %s after %s retries" % (
                pedestal_dir,
                nb_retries,
            )
            logging.getLogger("user_level_log").error(msg)
            raise RuntimeError(msg)

        if len(HWR.beamline.detector.lima2_device.recvs) == 4:
            rr = "rr4"
        else:
            rr = "rr"
        det_name = f"lima2_jungfrau4m_{rr}_smx"
        detector = getattr(HWR.beamline.control, det_name)

        def pedestal_func():
            HWR.beamline.control.lima2_jungfrau_pedestal_scans(
                detector,
                exp_time,
                effect_freq,
                1000,
                pedestal_dir,
                "pedestal.h5",
                disable_saving=disable_saving,
                print_params=True,
                det_params={"packet_fifo_depth": packet_fifo_depth},
                cl_source_path=cl_source_path,
                saving_compression=saving_compression,
            )

        self.__stop_req = False

        self.__pedestal_task = gevent.spawn(pedestal_func)
        try:
            while not self.__pedestal_task.ready():
                if self.__stop_req:
                    logging.getLogger("user_level_log").info(
                        f"Stop requested. Killing pedestal task"
                    )
                    self.__pedestal_task.kill()
                    return
                gevent.sleep(0.1)
            self.__pedestal_task.get()
        except Exception as e:
            logging.getLogger("user_level_log").exception(f"Error taking pedestal: {e}")
        finally:
            self.__pedestal_task = None

        cmd = "cd %s && rm -f pedestal.h5 && ln -s %s/pedestal.h5" % (
            data_root_path,
            pedestal_dir,
        )
        subprocess.run(cmd, shell=True, check=True, close_fds=True)

    def start_processing(self, exp_type):
        data_root_path = self.get_data_path()

        if self._use_nicoproc:
            logging.getLogger("user_level_log").info(f"Starting NICOPROC")
            self._start_nico_processing(
                self._beamline_values,
                self._data_model._task_data,
                data_root_path,
                experiment_type=exp_type,
            )
        else:
            logging.getLogger("user_level_log").info(f"Not using NICOPROC")

        if self._use_besproc:
            logging.getLogger("user_level_log").info(f"Using BES PROC")
            HWR.beamline.workflow.start(
                ["modelpath", "SSX", "data_path", data_root_path]
            )
        else:
            logging.getLogger("user_level_log").info(f"BES PROC False")

    def prepare_acquisition(self):
        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        num_images = self._data_model._task_data.user_collection_parameters.num_images

        data_root_path = self.get_data_path()
        reject_empty_frames = (
            self._data_model._task_data.user_collection_parameters.reject_empty_frames
        )

        logging.getLogger("user_level_log").info(f"Preparing detector")
        HWR.beamline.detector.wait_ready()
        HWR.beamline.detector.stop_acquisition()
        HWR.beamline.detector.prepare_acquisition(
            num_images,
            exp_time,
            data_root_path,
            fname_prefix,
            dense_skip_nohits=reject_empty_frames,
        )
        HWR.beamline.detector.wait_ready()
        logging.getLogger("user_level_log").info(f"Detector prepared, continuing !")

    def _monitor_collect(self):
        for i in range(1, 99):
            self.emit_progress(i / 100.0)
            gevent.sleep(0.1)

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)

        self._monitor_task = gevent.spawn(self._monitor_collect)

    def pre_execute(self):
        super().pre_execute()
        self._current_data_path = self.get_data_model().get_path_template().directory
        self._current_process_path = (
            self.get_data_model().get_path_template().process_directory
        )

        with contextlib.suppress(AttributeError):
            HWR.beamline.beam.wait_for_beam()

        logging.getLogger("user_level_log").info(f"Moving detector table")
        HWR.beamline.control.LDetX.wait_move()
        HWR.beamline.control.LDetX.move(0, wait=False)
        self._beamline_values = self.get_current_beamline_values()
        self._data_model._task_data.lims_parameters = self.get_additional_lims_values()
        self.emit_progress(0)

    def post_execute(self):
        super().post_execute()
        data_root_path = self.get_data_path()
        data_process_path = self.get_process_path()
        self._data_model._task_data.lims_parameters.end_time = datetime.datetime.now()

        parameters = {}
        parameters["collection_parameters"] = self._data_model._task_data
        parameters["data_path"] = data_root_path
        parameters["data_process_path"] = data_process_path
        parameters["beamline_parameters"] = self._beamline_values
        parameters["extra_lims_values"] = self._data_model._task_data.lims_parameters
        parameters["sample"] = self._data_model.get_parent().get_parent().crystals[0]

        HWR.beamline.lims.finalize_data_collection(parameters)

        self.start_ewoks(parameters)

        try:
            move_back = HWR.beamline.detector.move_detector.get_value().value
        except ValueError:
            move_back = True

        if move_back:
            logging.getLogger("user_level_log").info(f"Moving detector back")
            HWR.beamline.control.LDetX.move(1000, wait=False)

        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            logging.getLogger("user_level_log").info(f"Closing OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.close()

    def start_ewoks(self, parameters):
        raw_path = os.path.normpath(parameters["data_path"])

        inputs_acc = [{"name": "path_scan", "value": raw_path}]
        upload_parameters_acc = {
            "beamline": HWR.beamline.session.beamline_name.lower(),
            "proposal": (
                f"{HWR.beamline.session.proposal_code}{HWR.beamline.session.proposal_number}"
            ),
            "dataset": "accumulation",
            "path": os.path.join(parameters["data_process_path"], "accumulation"),
            "raw": [raw_path],
            "metadata": {
                "Sample_name": (
                    parameters["collection_parameters"].path_parameters.prefix
                )
            },
        }

        self._start_ewoks_workflow(
            workflow="max_sum_projection_workflow",
            queue="slurm",
            inputs=inputs_acc,
            flag_icat=True,
            upload_parameters=upload_parameters_acc,
        )

        config_ssx = HWR.get_hardware_repository().find_in_repository(
            "ssx_mxcube_config.json"
        )

        logging.getLogger("user_level_log").info("Config Json Ewoks:")
        logging.getLogger("user_level_log").info(config_ssx)
        logging.getLogger("user_level_log").info("$#$#$#$#$#$#$#$#$#$#$#$#$#$#$#$#")

        with open(config_ssx, "r") as f:
            dict_ssx = json.load(f)
            inputs_ssx = dict_ssx["default_inputs"]

        inputs_ssx.append({"name": "image_directory", "value": raw_path})
        metadata_path = os.path.join(raw_path, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path) as f:
                meta = json.loads(f.read())
        protein_name = meta["SampleProtein_acronym"]
        cell_file = protein_name + ".cell"
        session = HWR.beamline.session.get_base_image_directory().strip("RAW_DATA")
        logging.getLogger("user_level_log").info(session)
        scripts_folder = os.path.join(session, "SCRIPTS")
        cell_file = os.path.join(scripts_folder, cell_file)
        try:
            inputs_ssx.append({"name": "unit_cell_file", "value": cell_file})
        except Exception:
            logging.getLogger("user_level_log").exception(
                "unit_cell_file: %s" % cell_file
            )

        self._start_ewoks_workflow(
            workflow="ssx_workflow", queue="ssx", inputs=inputs_ssx, flag_icat=False
        )

    def _start_ewoks_workflow(
        self, workflow, queue, inputs, flag_icat, upload_parameters=None
    ):
        kwargs = {
            "load_options": {"root_module": "ewoksid29.workflows"},
            "inputs": inputs,
        }

        if flag_icat:
            kwargs["upload_parameters"] = upload_parameters

        logging.getLogger("user_level_log").info("Calling ewoks with:")
        logging.getLogger("user_level_log").info(f"kwargs f{kwargs}")

        submit(args=(workflow,), kwargs=kwargs, queue=queue)

    def emit_progress(self, progress):
        HWR.beamline.collect.emit_progress(progress)

    def stop(self):
        logging.getLogger("user_level_log").info(f"Stop requested")
        self.__stop_req = True

        super().stop()

        if self.__pedestal_task is not None:
            return

        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            HWR.beamline.control.safshut_oh2.close()
            logging.getLogger("user_level_log").info("shutter closed")

        HWR.beamline.detector.stop_acquisition()
        self.post_execute()  # launch processing and cleanup even if the scan is aborted

    def _start_processing(self, dc_parameters, file_paramters):
        param = {
            "exposure": dc_parameters["oscillation_sequence"][0]["exposure_time"],
            "detector_distance": dc_parameters["detectorDistance"],
            "wavelength": dc_parameters["wavelength"],
            "orgx": dc_parameters["xBeam"],
            "orgy": dc_parameters["yBeam"],
            "oscillation_range": dc_parameters["oscillation_sequence"][0]["range"],
            "start_angle": dc_parameters["oscillation_sequence"][0]["start"],
            "number_images": dc_parameters["oscillation_sequence"][0][
                "number_of_images"
            ],
            "image_first": dc_parameters["oscillation_sequence"][0][
                "start_image_number"
            ],
            "fileinfo": file_paramters,
        }

        logging.getLogger("HWR").info("NICOPROC START")

        with xmlrpc.client.ServerProxy(self._processing_host) as p:
            p.start(param)

    def _start_nico_processing(self, beamline_values, params, path, experiment_type=""):
        param = {
            "exposure": params.user_collection_parameters.exp_time,
            "detector_distance": beamline_values.detector_distance,
            "wavelength": beamline_values.wavelength,
            "orgx": beamline_values.beam_x,
            "orgy": beamline_values.beam_y,
            "oscillation_range": params.collection_parameters.osc_range,
            "start_angle": params.collection_parameters.osc_start,
            "number_images": params.user_collection_parameters.num_images,
            "image_first": params.collection_parameters.first_image,
            "fileinfo": params.path_parameters.dict(),
            "root_path": path,
            "experiment_type": experiment_type,
        }

        logging.getLogger("HWR").info("NICOPROC START")

        try:
            with xmlrpc.client.ServerProxy(self._processing_host) as p:
                p.start(param)
        except Exception:
            logging.getLogger("HWR").exception("")

    def _stop_processing(self):
        logging.getLogger("HWR").info("NICOPROC STOP")

        with xmlrpc.client.ServerProxy(self._processing_host) as p:
            p.stop()

    def get_current_beamline_values(self):
        return BeamlineParameters(
            **{
                "energy": HWR.beamline.energy.get_value(),
                "wavelength": HWR.beamline.energy.get_wavelength(),
                "resolution": HWR.beamline.resolution.get_value(),
                "transmission": HWR.beamline.transmission.get_value(),
                "detector_distance": 103.0,
                "beam_x": HWR.beamline.detector.get_beam_position()[0],
                "beam_y": HWR.beamline.detector.get_beam_position()[1],
                "beam_size_x": 4,
                "beam_size_y": 2,
                "beam_shape": "gaussian",
                "energy_bandwidth": 1,
            }
        )

    def get_additional_lims_values(self):
        return ISPYBCollectionParameters(
            **{
                "flux_start": (
                    3e15
                    * HWR.beamline.transmission.get_value()
                    / 100
                    * HWR.beamline.machine_info.get_current()
                    / 200
                ),
                "flux_end": (
                    3e15
                    * HWR.beamline.transmission.get_value()
                    / 100
                    * HWR.beamline.machine_info.get_current()
                    / 200
                ),
                "start_time": datetime.datetime.now(),
                "end_time": datetime.datetime.now(),
                "chip_model": "",
                "polarisation": 0.99,
                "mono_stripe": "PdB4C",
                "number_of_rows": 20,
                "number_of_columns": 20,
            }
        )
