from ESRFMultiCollect import *
import shutil
import logging
import time

class ID29MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, PixelDetector(), TunableEnergy())

    @task
    def data_collection_hook(self, data_collect_parameters):
      oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
      if data_collect_parameters.get("nb_sum_images"):
        if oscillation_parameters["number_of_images"] % data_collect_parameters.get("nb_sum_images", 1) != 0:
          raise RuntimeError, "invalid number of images to sum"

      data_collect_parameters["dark"] = 0
      # are we doing shutterless ?
      #if oscillation_parameters["overlap"] != 0:
      #  shutterless = False
      #else:
      
      shutterless = data_collect_parameters.get("shutterless")
      self._detector.shutterless = True if shutterless else False
      self.getChannelObject("shutterless").setValue(1 if shutterless else 0)

      self.getChannelObject("parameters").setValue(data_collect_parameters)
      self.execute_command("build_collect_seq")
      self.execute_command("local_set_experiment_type")
      self.execute_command("prepare_beamline")

    @task
    def move_detector(self, detector_distance):
        self.bl_control.detector_distance.move(detector_distance)
        time.sleep(1)
        self.bl_control.detector_distance.waitMove()

    def get_detector_distance(self):
        return self.bl_control.detector_distance.getPosition()

    @task
    def set_resolution(self, new_resolution):
        self.bl_control.resolution.move(new_resolution)
        time.sleep(1)
        self.bl_control.resolution.waitMove()

    def trigger_auto_processing(self, process_event, *args, **kwargs):       
        if process_event in ('before', 'after'):
            return ESRFMultiCollect.trigger_auto_processing(self, process_event, *args, **kwargs)

    @task
    def write_input_files(self, datacollection_id):
        # copy *geo_corr.cbf* files to process directory
        try:
            process_dir = os.path.join(self.xds_directory, "..")
            raw_process_dir = os.path.join(self.raw_data_input_file_dir, "..") 
            for dir in (process_dir, raw_process_dir):
                for filename in ("x_geo_corr.cbf.bz2", "y_geo_corr.cbf.bz2"):
                    dest = os.path.join(dir,filename)
                    if os.path.exists(dest):
                        continue
                    shutil.copyfile(os.path.join("/data/id29/inhouse/opid291", filename), dest)
        except:
            logging.exception("Exception happened while copying geo_corr files")
       
        return ESRFMultiCollect.write_input_files(self, datacollection_id)
        
