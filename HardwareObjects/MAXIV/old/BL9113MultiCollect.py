from MAXLABMultiCollect import *
import shutil
import logging


class BL9113MultiCollect(MAXLABMultiCollect):
    def __init__(self, name):
        MAXLABMultiCollect.__init__(self, name, CcdDetector(), TunableEnergy())

    @task
    def data_collection_hook(self, data_collect_parameters):
        oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
        if data_collect_parameters.get("nb_sum_images"):
            if (
                oscillation_parameters["number_of_images"]
                % data_collect_parameters.get("nb_sum_images", 1)
                != 0
            ):
                raise RuntimeError, "invalid number of images to sum"

        data_collect_parameters["dark"] = 0

        # are we doing shutterless ?
        # shutterless = data_collect_parameters.get("shutterless")
        # self._detector.shutterless = True if shutterless else False
        # self.getChannelObject("shutterless").setValue(1 if shutterless else 0)
        self.shutterless = 0

        self.getChannelObject("parameters").setValue(data_collect_parameters)
        self.execute_command("build_collect_seq")
        # self.execute_command("local_set_experiment_type")
        self.execute_command("prepare_beamline")
        MAXLABMultiCollect.data_collection_hook(self, data_collect_parameters)

    @task
    def move_detector(self, detector_distance):
        self.bl_control.detector_distance.move(detector_distance)
        while self.bl_control.detector_distance.motorIsMoving():
            time.sleep(0.5)

    def get_detector_distance(self):
        return self.bl_control.detector_distance.getPosition()

    @task
    def set_resolution(self, new_resolution):
        self.bl_control.resolution.move(new_resolution)
        while self.bl_control.resolution.motorIsMoving():
            time.sleep(0.5)

    def trigger_auto_processing(self, process_event, *args, **kwargs):
        if process_event in ("before", "after"):
            return MAXLABMultiCollect.trigger_auto_processing(
                self, process_event, *args, **kwargs
            )
