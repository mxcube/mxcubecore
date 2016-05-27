from detectors.LimaPilatus import Pilatus
from ESRFMultiCollect import *
import shutil
import logging
import os

class Pilatus3_2M(PixelDetector):
    def __init__(self,*args,**kwargs):
      PixelDetector.__init__(self,*args,**kwargs)

    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        self.new_acquisition = True
        if  osc_range < 0.0001:
            self.shutterless = False
        take_dark = 0
        if self.shutterless:
            self.shutterless_range = osc_range*number_of_images
            self.shutterless_exptime = (exptime + 0.00095)*number_of_images
        self.execute_command("prepare_acquisition", take_dark, start, osc_range, exptime, npass, comment)


class ID232MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, PixelDetector(Pilatus), TunableEnergy())
       
    @task
    def data_collection_hook(self, data_collect_parameters):
      oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
      if data_collect_parameters.get("nb_sum_images"):
        if oscillation_parameters["number_of_images"] % data_collect_parameters.get("nb_sum_images", 1) != 0:
          raise RuntimeError, "invalid number of images to sum"

      data_collect_parameters["dark"] = 0
      # are we doing shutterless ?
      shutterless = data_collect_parameters.get("shutterless")
      self._detector.shutterless = True if shutterless else False

      self.getChannelObject("parameters").setValue(data_collect_parameters)
      self.execute_command("build_collect_seq")
      #self.execute_command("local_set_experiment_type")
      self.execute_command("prepare_beamline")
      self.getCommandObject("prepare_beamline").executeCommand("musstPX_loadprog")
      self.executeCommand("detcoverout")

    @task
    def move_detector(self, detector_distance):
        self.bl_control.resolution.dtox.move(detector_distance)
        while self.bl_control.detector_distance.motorIsMoving():
            time.sleep(0.5)

    def get_detector_distance(self):
        return self.bl_control.resolution.dtox.getPosition()

    @task
    def set_resolution(self, new_resolution):
        self.bl_control.resolution.move(new_resolution, wait=False)
        while self.bl_control.resolution.motorIsMoving():
            time.sleep(0.5)

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
                    shutil.copyfile(os.path.join("/data/id23eh1/inhouse/opid231", filename), dest)
        except:
            logging.exception("Exception happened while copying geo_corr files")

        return ESRFMultiCollect.write_input_files(self, datacollection_id)


class _ID232MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, PixelDetector(Pilatus), FixedEnergy(0.966, 12.8353))
        #ESRFMultiCollect.__init__(self, name, Pilatus3_2M(), FixedEnergy(0.8726, 14.2086))

    @task
    def data_collection_hook(self, data_collect_parameters):
      oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
      if data_collect_parameters.get("nb_sum_images"):
        if oscillation_parameters["number_of_images"] % data_collect_parameters.get("nb_sum_images", 1) != 0:
          raise RuntimeError, "invalid number of images to sum"

      data_collect_parameters["dark"] = 0
      # are we doing shutterless ?
      shutterless = data_collect_parameters.get("shutterless")
      self._detector.shutterless = True if shutterless else False
      #self.getChannelObject("shutterless").setValue(1 if shutterless else 0)

      self.getChannelObject("parameters").setValue(data_collect_parameters)
      self.execute_command("build_collect_seq")
    #  self.execute_command("local_set_experiment_type")
      self.execute_command("prepare_musst")
      self.execute_command("prepare_beamline")
      self.getCommandObject("prepare_beamline").executeCommand("musstPX_loadprog")

    @task
    def move_detector(self, detector_distance):
        self.bl_control.resolution.newDistance(detector_distance)

    @task
    def set_resolution(self, new_resolution):
        self.bl_control.resolution.move(new_resolution)

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

    def get_detector_distance(self):
        return self.bl_control.resolution.dtox.getPosition()

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
                    shutil.copyfile(os.path.join("/data/id23eh2/inhouse/opid232", filename), dest)
        except:
            logging.exception("Exception happened while copying geo_corr files")

        return ESRFMultiCollect.write_input_files(self, datacollection_id)

