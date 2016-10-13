import gevent
import time
import subprocess
import os
import math
from HardwareRepository.TaskUtils import task, cleanup, error_cleanup
import logging
import PyTango

class Eiger:

    def init(self, config, collect_obj):
        self.config = config
        self.collect_obj = collect_obj
        self.header = dict()

      
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
        for param in header.items():
            if hasattr(self.dev, param[0])
                setattr(self.dev, param[0], param[1])

       
        # we have already the tango channel from the init, we could also do a setValue() in all of them
        self.config['OmegaStart'] = start
        self.config['OmegaIncrement'] = osc_range
        beam_x, beam_y = self.collect_obj.get_beam_centre() # returns length, not pixel
        self.config['BeamCenterX'] = beam_x
        self.config['BeamCenterY'] = beam_y
        self.config['Wavelength'] = self.collect_obj.get_wavelength()
        self.config['DetectorDistance'] = self.collect_obj.get_detector_distance()/1000.0

        self.config['FrameTime'] = exptime + self.get_deadtime()

        self.config['NbImages'] = number_of_images
        self.config['NbTriggers'] = ntrigger # to check for different tasks
        self.config['NbImagesPerFile'] = imagers_per_file
        self.config['RoiMode'] = roi
        self.config['PhotonEnergy'] = energy
        # This one??: self.getChannelObject("NbImagesPerFile").setValue(min(100,number_of_images))

        self.stop()
        self.wait_ready()
   

        if still:
            self.getChannelObject("TriggerMode").setValue("ints")
            # self.header['TriggerMode'] = "ints"
        else:
            self.getChannelObject("TriggerMode").setValue("exts")
            # self.header['TriggerMode'] = "exts"
        self.change_config(self.config)
        # check the bufferfree in DCU
        # compression

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
        return self.getCommandObject("Arm")()

    def stop(self):
        """To check the best stop sequence of commands"""
        try:
            self.getCommandObject("Cancel")()
        except:
            pass
        time.sleep(1)
        self.getCommandObject("Disarm")()

    def change_config(header):
        """This writes into the tango device"""
        for param in header.items():
            if hasattr(self.dev, param[0])
                setattr(self.dev, param[0], param[1])

