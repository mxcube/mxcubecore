import gevent
import time
import subprocess
import os
import math
from HardwareRepository.TaskUtils import task, cleanup, error_cleanup
import logging
import PyTango


class PixelDetector:
    def __init__(self, detector_class=None):
        self._detector = detector_class() if detector_class else None
        self.shutterless = True
        self.new_acquisition = True
        self.oscillation_task = None
        self.shutterless_exptime = None
        self.shutterless_range = None

    def init(self, config, collect_obj):
        self.collect_obj = collect_obj
        if self._detector:
          self._detector.addChannel = self.addChannel
          self._detector.addCommand = self.addCommand
          self._detector.getChannelObject = self.getChannelObject
          self._detector.getCommandObject = self.getCommandObject
          self._detector.init(config, collect_obj)

    def last_image_saved(self):
        return self._detector.last_image_saved()

    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment="", energy=None):
        self.new_acquisition = True
        if osc_range < 1E-4:
            still = True
        else:
            still = False
        take_dark = 0
        if self.shutterless:
            self.shutterless_range = osc_range*number_of_images
            self.shutterless_exptime = (exptime + self._detector.get_deadtime())*number_of_images
        if self._detector:
            self._detector.prepare_acquisition(take_dark, start, osc_range, exptime, npass, number_of_images, comment, energy, still)

    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
      if self.shutterless and not self.new_acquisition:
          return

      if self._detector:
          self._detector.set_detector_filenames(frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path)

    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        if self.shutterless:
            end = start+self.shutterless_range
            if self.new_acquisition:
                self.collect_obj.do_prepare_oscillation(start, end, self.shutterless_exptime, npass)
            return (start, end)
        else:
            if osc_range < 1E-4:
                # still image
                pass
            else:
                self.collect_obj.do_prepare_oscillation(start, start+osc_range, exptime, npass)
            return (start, start+osc_range)

    @task
    def start_acquisition(self, exptime, npass, first_frame):
        try:
            self.collect_obj.getObjectByRole("detector_cover").set_out()
        except:
            pass

        if not first_frame and self.shutterless:
            pass
        else:
            if self._detector:
                self._detector.start_acquisition()

    @task
    def no_oscillation(self, exptime):
        self.collect_obj.open_fast_shutter()
        time.sleep(exptime)
        self.collect_obj.close_fast_shutter()


    @task
    def do_oscillation(self, start, end, exptime, npass):
      still = math.fabs(end-start) < 1E-4
      if self.shutterless:
          if self.new_acquisition:
              # only do this once per collect
              # make oscillation an asynchronous task => do not wait here
              if still:
                  self.oscillation_task = self.no_oscillation(self.shutterless_exptime, wait=False)
              else:
                  self.oscillation_task = self.collect_obj.oscil(start, end, self.shutterless_exptime, 1, wait=False)
          if self.oscillation_task.ready():
              self.oscillation_task.get()
      else:
          if still:
              self.no_oscillation(exptime)
          else:
              self.collect_obj.oscil(start, end, exptime, npass)

    @task
    def write_image(self, last_frame):
      if last_frame:
        if self.shutterless:
            self.oscillation_task.get()


    def stop_acquisition(self):
        self.new_acquisition = False

    @task
    def reset_detector(self):
      if self.shutterless:
          self.oscillation_task.kill()
      if self._detector:
          self._detector.stop()

class BIOMAXEiger:

    def init(self, config, collect_obj):
        self.config = config
        self.collect_obj = collect_obj

      
        eiger_device = config.getProperty("eiger_device")

        self.dev = PyTango.DeviceProxy(eiger_device)
        # not all of the following attr are needed, for now all of them here for convenience
        attr_list=('NbImages','Temperature','Humidity','CountTime','FrameTime','PhotonEnergy',
                    'Wavelength','EnergyThreshold','FlatfieldEnabled','AutoSummationEnabled',
                    'TriggerMode','RateCorrectionEnabled','BitDepth','ReadoutTime','Description',
                    'NbImagesMax','NbImagesMin','CountTimeMax','CountTimeMin','FrameTimeMax',
                    'FrameTimeMin','PhotonEnergyMax','PhotonEnergyMin','EnergyThresholdMax',
                    'EnergyThresholdMin','Time','MustArmFlag','NbTriggers','NbTriggersMax',
                    'NbTriggersMin','CountTimeInte','DownloadDirectory','FilesInBuffer','Error',
                    'BeamCenterX','BeamCenterY','DetectorDistance','OmegaIncrement','OmegaStart',
                    'PixelMask','PixelMaskApplied','Compression','RoiMode','FileWriterMode',
                    'NbImagesPerFile','ImagesNbStart','NamePattern','CompressionEnabled',
                    'FileWriterState','BufferFree', 'State')

        # config needed to be set up for data collection
        # if values are None, use the one from the system
        col_config = { 'OmegaStart': 0,
                       'OmegaIncrement': 0.1,
                       'BeamCenterX': None, # length not pixel
                       'BeamCenterY': None,
                       'Wavelength': None,
                       'DetectorDistance': None,
                       'FrameTime': None,
                       'NbImages': None,
                       'NbTriggers': None,
                       'NbImagesPerFile': None,
                       'RoiMode': None,
                       'PhotonEnergy': None
                     }

        buffer_free_chan = self.getChannelObject("BufferFree") 

        # not all of the following commands are needed, for now all of them here for convenience
        cmd_list = ('Arm','Trigger','Abort','Cancel','ClearBuffer','DeleteFileFromBuffer',
                'Disarm','DownloadFilesFromBuffer')


        for channel_name in attr_list:
            self.addChannel({"type":"tango", 
                             "name": channel_name,
                             "tangoname": eiger_device },
                             channel_name)

        for cmd_name in cmd_list:
            self.addCommand({"type":"tango",
                             "name": channel_name, 
                             "tangoname": eiger_device },
                             channel_name)

        # init the detector settings in case of detector restart
        # use bslz4 for compression ()        
        self.getChannelObject("Compression").setValue("bslz4")
        #self.getChannelObject("CompressionEnabled").setValue(True)
        
    def wait_ready(self):
        acq_status_chan = self.getChannelObject("State")
        with gevent.Timeout(30, RuntimeError("Detector not ready")):
            while acq_status_chan.getValue() != "On":
                time.sleep(1)

    # def last_image_saved(self):
    #     #return 0
    #     return self.getChannelObject("last_image_saved").getValue() + 1

    def get_deadtime(self):
        return float(self.config.getProperty("deadtime"))
  
    def get_buffer_free(self):
        return self.buffer_free_chan.getValue()

    @task
    def prepare_acquisition(self, config):
        """
        config is a dictionary
        OmegaStart,OmegaIncrement,
        BeamCenterX
        BeamCenterY
        OmegaStart
        OmegaIncrement
         
        start, osc_range, exptime, ntrigger, number_of_images, images_per_file, energy, compression,ROI,wavelength):
        """
        diffractometer_positions = self.collect_obj.bl_control.diffractometer.getPositions()
       
        
        """This writes into the tango device"""
        for param in self.config.items():
            if hasattr(self.dev, param[0]) and param[1] is not None:
                setattr(self.dev, param[0], param[1])

        self.stop()
        self.wait_ready()
   
        # check the bufferfree in DCU
        # compression
        # 

    def has_shutterless(self):
        return True
        
    @task 
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        prefix, suffix = os.path.splitext(os.path.basename(filename))
        prefix = "_".join(prefix.split("_")[:-1])+"_"
        dirname = os.path.dirname(filename)
        if dirname.startswith(os.path.sep):
          dirname = dirname[len(os.path.sep):]
        # this would be 'DownloadDirectory' attribute
        saving_directory = os.path.join(self.config.getProperty("buffer"), dirname)

        self.wait_ready()  
     
        self.getChannelObject("NamePattern").setValue(saving_directory) # only this?


    @task 
    def start_acquisition(self):
        logging.getLogger("user_level_log").info("Preparing acquisition")
        logging.getLogger("user_level_log").info("Detector ready, continuing")

        try:
            self.collect_obj.getObjectByRole("detector_cover").set_out()
            logging.getLogger("user_level_log").info("Open the detector cover")
        except:
            pass

        return self.getCommandObject("Arm")()

    def stop_acquisition(self):
        """To check the best stop sequence of commands"""
        try:
            self.getCommandObject("Cancel")()
        except:
            pass
        time.sleep(1)
        self.getCommandObject("Disarm")()

    def abort(self):
        try:
            self.getCommandObject("Abort")()
        except:
            pass

