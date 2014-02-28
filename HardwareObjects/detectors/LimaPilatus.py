import gevent
import time
import subprocess
import os

class Pilatus:

  def init(self, config, collect_obj):
      self.config = config
      self.collect_obj = collect_obj
      self.header = dict()

      lima_device = config.getProperty("lima_device")
      pilatus_device = config.getProperty("pilatus_device")

      for channel_name in ("acq_trigger_mode", "saving_mode", "acq_nb_frames",
                           "acq_expo_time", "saving_directory", "saving_prefix",
                           "saving_suffix", "saving_next_number", "saving_index_format",
                           "saving_format", "saving_overwrite_policy", "threshold",
                           "saving_header_delimiter"):
        setattr(self, "__%s" % channel_name, self.addChannel({"type":"tango",
                                                              "name": channel_name,
                                                              "tangoname": lima_device },
                                                              channel_name))

      self.__prepare_acq = self.addCommand({ "type": "tango",
                                             "name": "prepare_acq",
                                             "tangoname": lima_device }, "prepare_acq")
      self.__working_energy = self.addChannel({ "type": "tango",
                                                "name": "working_energy",
                                                "tangoname": pilatus_device }, "working_energy")
      self.__fill_mode = self.addChannel({ "type": "tango",
                                           "name": "fill_mode",
                                           "tangoname": pilatus_device }, "fill_mode")
      self.__start_acq = self.addCommand({ "type": "tango",
                                           "name": "start_acq",
                                           "tangoname": lima_device }, "start_acq")
      self.__stop_acq = self.addCommand({ "type": "tango",
                                          "name": "stop_acq",
                                          "tangoname": lima_device }, "stop_acq")
      self.__reset = self.addCommand({ "type": "tango",
                                       "name": "reset",
                                       "tangoname": lima_device }, "reset")
      self.__set_image_header = self.addCommand({ "type": "tango",
                                                  "name": "SetImageHeader",
                                                  "tangoname": lima_device }, "SetImageHeader")

  def wait_ready(self):
      with gevent.Timeout(10, RuntimeError("Detector not ready")):
          while self.__acq_status != "Ready":
              time.sleep(1)

  def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment, energy, still):
      diffractometer_positions = self.collect.bl_control.diffractometer.getPositions()
      self.start_angles = list()
      for i in range(number_of_images):
        self.start_angles.append("%0.4f deg." % start+osc_range*i)
      self.header["file_comments"]=comment
      self.header["N_oscillations"]=number_of_images
      self.header["Oscillation_axis"]="omega"
      self.header["Chi"]="0.0000 deg."
      self.header["Phi"]="%0.4f deg." % diffractometer_positions.get("kappa_phi", -9999)
      self.header["Kappa"]="%0.4f deg." % diffractometer_positions.get("kappa", -9999)
      self.header["Alpha"]="0.0000 deg."
      self.header["Polarization"]=self.collect.bl_config.polarisation
      self.header["Detector_2theta"]="0.0000 deg."
      self.header["Angle_increment"]="%0.4f deg." % osc_range
      #self.header["Start_angle"]="%0.4f deg." % start
      self.header["Transmission"]=self.collect.get_transmission()
      self.header["Flux"]=self.collect.get_flux(),
      self.header["Beam_xy"]="(%.2f, %.2f) pixels" % self.collect.get_beam_centre()
      self.header["Detector_Voffset"]="0.0000 m"
      self.header["Energy_range"]="(0, 0) eV"
      self.header["Detector_distance"]="%f m" % self.collect.bl_control.get_detector_distance()/1000.0
      self.header["Wavelength"]="%f A" % self.collect.get_wavelength()
      self.header["Trim_directory:"]="(nil)"
      self.header["Flat_field:"]="(nil)"
      self.header["Excluded_pixels:"]=" badpix_mask.tif"
      self.header["N_excluded_pixels:"]="= 321"
      self.header["Threshold_setting"]="%d eV" % self.__threshold.getValue(),
      self.header["Count_cutoff"]="1048500",
      self.header["Tau"]="= 0 s",
      self.header["Exposure_period"]="%f s" % (exptime+float(self.config.getProperty("deadtime")))
      self.header["Exposure_time"]="%f s" % exptime

      self.wait_ready()

      self.set_energy_threshold(energy)

      if still:
          self.__acq_trigger_mode.setValue("INTERNAL_TRIGGER")
      else:
          self.__acq_trigger_mode.setValue("EXTERNAL_TRIGGER")

      self.__saving_mode.setValue("AUTO_FRAME")
      self.__acq_nb_frames.setValue(number_of_images)
      self.__acq_expo_time.setValue(exptime)
      self.__saving_overwrite_policy.setValue("OVERWRITE")
      self.__prepare_acq()

  def set_energy_threshold(self, energy):  
      minE = self.config.getProperty("minE")
      if energy < minE:
        energy = minE
      
      working_energy = self.__working_energy.getValue()
      if math.fabs(working_energy - energy) > 0.1:
        self.__working_energy.setValue(energy)
        
        while math.fabs(working_energy - energy) > 0.1:
          working_energy = self.__working_energy.getValue()
          time.sleep(1)    
      
      self.__fill_mode.setValue("ON")
      
  def set_detector_filename(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
      prefix, suffix = os.path.splitext(os.path.basename(filename))
      prefix = "_".join(prefix.split("_")[:-1])+"_"
      dirname = os.path.dirname(filename)
      
      saving_directory = os.path.join(self.config.getProperty("buffer"), dirname)
      subprocess.Popen("ssh %s@%s mkdir --parents %s" % (os.environ["USER"],
                                                         self.config.getProperty("control"),
                                                         saving_directory),
                                                         shell=True, stdin=None, 
                                                         stdout=None, stderr=None, 
                                                         close_fds=True)
      
      self.wait_ready()  

      self.__saving_directory.setValue(saving_directory) 
      self.__saving_prefix.setValue(prefix)
      self.__saving_suffix.setValue(suffix)
      self.__saving_next_number.setValue(frame_number)
      self.__saving_index_format.setValue("%04d")
      self.__saving_format.setValue("CBF")
      self.__saving_header_delimiter.setValue(["|", ";", ":"])

      headers = list()
      for i, start_angle in enumerate(self.start_angles):
          header = "\n%s\n" % self.config.getProperty("serial")
          header += "# %s\n" % time.strftime("%Y/%b/%d %T")
          header += "# Pixel size 172e-6 m x 172e-6 m\n"
          header += "# Silicon sensor, thickness 0.000320 m\n"  
          self.header["Start_angle"]=start_angle
          for key, value in self.header.iteritems():
              header += "# %s %s\n" % (key, value)
          headers.append("%d : array_data/header_contents|%s;" % (i, header))    
      
      self.__set_image_header(headers)
        
  def start_acquisition(self):
      return self.__start_acq()

  def stop(self):
      try:
          self.__stop_acq()
      except:
          pass
      self.__reset()



