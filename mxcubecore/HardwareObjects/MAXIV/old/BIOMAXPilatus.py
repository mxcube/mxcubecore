from detectors.LimaPilatus import Pilatus
from HardwareRepository.TaskUtils import *
import subprocess
import os
import time

class BIOMAXPilatus(Pilatus):
  def init(self, config, collect_obj):
      Pilatus.init(self,config, collect_obj)

  @task
  def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
      prefix, suffix = os.path.splitext(os.path.basename(filename))
      prefix = "_".join(prefix.split("_")[:-1])+"_"
      dirname = os.path.dirname(filename)
      #if dirname.startswith(os.path.sep):
      #  dirname = dirname[len(os.path.sep):]
      dirname = dirname.replace("/data/","")
     
      saving_directory = os.path.join(self.config.getProperty("buffer"), dirname)

      subprocess.Popen("ssh %s@%s mkdir --parents %s" % (self.config.getProperty("control_user"), #"mxcube",
                                                         self.config.getProperty("control"),
                                                         saving_directory),
                                                         shell=True, stdin=None,
                                                         stdout=None, stderr=None,
                                                         close_fds=True).wait()

      self.wait_ready()

      os.system('ssh mxcube@b-biomax-pilatus-pc-01 "chmod -R 777 /ramdisk/visitor/"')
      #subprocess.Popen('ssh mxcube@b-biomax-pilatus-pc-01 "chmod -R 777 /ramdisk/visitor/"').wait()
      #self.wait_ready()  
      try:
          self.getChannelObject("saving_directory").setValue(saving_directory)
      except Exception as ex:
          print ex
      self.getChannelObject("saving_prefix").setValue(prefix)
      self.getChannelObject("saving_suffix").setValue(suffix)
      self.getChannelObject("saving_next_number").setValue(frame_number)
      self.getChannelObject("saving_index_format").setValue("%04d")
      self.getChannelObject("saving_format").setValue("CBF")
      self.getChannelObject("saving_header_delimiter").setValue(["|", ";", ":"])
      headers = list()
      for i, start_angle in enumerate(self.start_angles):
          header = "\n%s\n" % self.config.getProperty("serial")
          header += "# Detector: PILATUS3 2M, S/N 24-0126, MAXIV BIOMAX\n"
          header += "# %s\n" % time.strftime("%Y/%b/%d %T")
          header += "# Pixel_size 172e-6 m x 172e-6 m\n"
          header += "# Silicon sensor, thickness 0.000450 m\n"
          self.header["Start_angle"]=start_angle
          for key, value in self.header.iteritems():
              header += "# %s %s\n" % (key, value)
          headers.append("%d : array_data/header_contents|%s;" % (i, header))

      self.getCommandObject("set_image_header")(headers)



