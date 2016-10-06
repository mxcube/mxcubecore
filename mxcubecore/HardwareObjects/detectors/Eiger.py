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

    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment, energy, still):
        diffractometer_positions = self.collect_obj.bl_control.diffractometer.getPositions()
        # we have already the tango channel from the init, we could also do a setValue() in all of them
        self.header['OmegaStart'] = start
        self.header['OmegaIncrement'] = osc_range
        beam_x, beam_y = self.collect_obj.get_beam_centre()
        self.header['BeamCenterX'] = beam_x/7.5000003562308848e-02
        self.header['BeamCenterY'] = beam_y/7.5000003562308848e-02
        self.header['Wavelength'] = self.collect_obj.get_wavelength()
        self.header['DetectorDistance'] = self.collect_obj.get_detector_distance()/1000.0

        self.header['FrameTime'] = exptime + self.get_deadtime()

        self.header['NbImages'] = number_of_images
        self.header['NbTriggers'] = 1 # to check for different tasks
        self.header['RoiMode'] = self.RoiMode.getValue() 
        # This one??: self.getChannelObject("NbImagesPerFile").setValue(min(100,number_of_images))

        self.stop()
        self.wait_ready()
   
        self.set_energy_threshold(energy)

        if still:
            self.getChannelObject("TriggerMode").setValue("ints")
            # self.header['TriggerMode'] = "ints"
        else:
            self.getChannelObject("TriggerMode").setValue("exts")
            # self.header['TriggerMode'] = "exts"

        self.set_header_data(self.header)

     def set_energy_threshold(self, energy):  
        minE = self.getChannelObject("PhotonEnergyMin").getValue()
        if energy < minE:
            energy = minE
     
        working_energy_chan = self.getChannelObject("PhotonEnergy")  # eV
        working_energy = working_energy_chan.getValue()/1000.0
        if math.fabs(working_energy - energy) > 0.1:
            egy = int(energy*1000.0)
            working_energy_chan.setValue(egy)
        
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

    def set_header_data(header):
        """This writes into the tango device"""
        for param in header.items():
            if hasattr(self.dev, param[0])
                setattr(self.dev, param[0], param[1])

    # def set_header_data_channel(header):
    #     """This writes into the tango channel"""
    #     for param in header.items():
    #         self.param[0].setValue(param[1])
