from .ESRFMultiCollect import ESRFMultiCollect, PixelDetector, TunableEnergy, task, time
from HardwareRepository.HardwareObjects.LimaPilatusDetector import LimaPilatusDetector
import shutil
import logging
import os


class ID231MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, TunableEnergy())

    @task
    def data_collection_hook(self, data_collect_parameters):
        ESRFMultiCollect.data_collection_hook(self, data_collect_parameters)

        oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
        if data_collect_parameters.get("nb_sum_images"):
            if (
                oscillation_parameters["number_of_images"]
                % data_collect_parameters.get("nb_sum_images", 1)
                != 0
            ):
                raise RuntimeError("invalid number of images to sum")

        data_collect_parameters["dark"] = 0
        # are we doing shutterless ?
        shutterless = data_collect_parameters.get("shutterless")
        self._detector.shutterless = True if shutterless else False

        self.get_channel_object("parameters").set_value(data_collect_parameters)
        self.execute_command("build_collect_seq")
        # self.execute_command("local_set_experiment_type")
        self.execute_command("prepare_beamline")
        self.execute_command("musstPX_loadprog")

    def get_beam_size(self):
        # should be moved to ESRFMultiCollect
        # (at the moment, ESRFMultiCollect is still using spec)
        return self.bl_control.beam_info.get_beam_size()

    def get_beam_shape(self):
        # should be moved to ESRFMultiCollect
        # (at the moment, ESRFMultiCollect is still using spec)
        return self.bl_control.beam_info.get_beam_shape()

    def get_resolution_at_corner(self):
        # should be moved to ESRFMultiCollect
        # (at the moment, ESRFMultiCollect is still using spec)
        return self.bl_control.resolution.get_value_at_corner()

    def get_beam_centre(self):
        # should be moved to ESRFMultiCollect
        # (at the moment, ESRFMultiCollect is still using spec)
        return self.bl_control.resolution.get_beam_centre()

    def trigger_auto_processing(self, process_event, *args, **kwargs):
        if process_event in ("before", "after"):
            return ESRFMultiCollect.trigger_auto_processing(
                self, process_event, *args, **kwargs
            )

    @task
    def write_input_files(self, datacollection_id):
        # copy *geo_corr.cbf* files to process directory
        try:
            process_dir = os.path.join(self.xds_directory, "..")
            raw_process_dir = os.path.join(self.raw_data_input_file_dir, "..")
            for dir in (process_dir, raw_process_dir):
                for filename in ("x_geo_corr.cbf.bz2", "y_geo_corr.cbf.bz2"):
                    dest = os.path.join(dir, filename)
                    if os.path.exists(dest):
                        continue
                    shutil.copyfile(
                        os.path.join("/data/id23eh1/inhouse/opid231", filename), dest
                    )
        except BaseException:
            logging.exception("Exception happened while copying geo_corr files")

        return ESRFMultiCollect.write_input_files(self, datacollection_id)
