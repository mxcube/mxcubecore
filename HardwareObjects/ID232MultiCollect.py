from ESRFMultiCollect import *

class ID232MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, PixelDetector(), FixedEnergy(0.8726, 14.2086))

    @task
    def data_collection_hook(self, data_collect_parameters):
      oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
      if data_collect_parameters.get("nb_sum_images"):
        if oscillation_parameters["number_of_images"] % data_collect_parameters.get("nb_sum_images", 1) != 0:
          raise RuntimeError, "invalid number of images to sum"

      data_collect_parameters["dark"] = 0
      # are we doing shutterless ?
      shutterless = data_collect_parameters.get("shutterless")
      if data_collect_parameters.get("experiment_type") == 'Helical':
          shutterless = False
      self._detector.shutterless = True if shutterless else False
      self.getChannelObject("shutterless").setValue(1 if shutterless else 0)

      self.getChannelObject("parameters").setValue(data_collect_parameters)
      self.execute_command("build_collect_seq")
      self.execute_command("local_set_experiment_type")
      self.execute_command("prepare_musst")
      self.execute_command("prepare_beamline")
      self.getCommandObject("prepare_beamline").executeCommand("musstPX_loadprog")

    @task
    def move_detector(self, detector_distance):
        self.bl_control.resolution.newDistance(detector_distance)

    @task
    def set_resolution(self, new_resolution):
        self.bl_control.resolution.move(new_resolution)


    def get_detector_distance(self):
        return self.bl_control.resolution.res2dist(self.bl_control.resolution.getPosition())


    def trigger_auto_processing(self, process_event, *args, **kwargs):
        if process_event in ('before', 'after'):
            return ESRFMultiCollect.trigger_auto_processing(self, process_event, *args, **kwargs)
 
  

