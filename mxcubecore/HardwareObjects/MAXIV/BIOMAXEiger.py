import gevent
import time
from HardwareRepository.TaskUtils import task, cleanup, error_cleanup

import logging
import PyTango
from HardwareRepository.BaseHardwareObjects import Equipment

class BIOMAXEiger(Equipment):
    """
    Description: Eiger hwobj based on tango
    """

    def __init__(self, *args):
        """
        Descrip. :
        """
        Equipment.__init__(self, *args)

        self.device = None
        self.file_suffix = None
        self.default_exposure_time = None
        self.default_compression = None
        self.buffer_limit = None
        self.dcu = None


    def init(self):
        
        tango_device = self.getProperty("detector_device")
        filewriter_device = self.getProperty("filewriter_device")

        self.device = PyTango.DeviceProxy(tango_device)
	self.device.set_timeout_millis(6000)

        self.fw_device = PyTango.DeviceProxy(filewriter_device)
	self.fw_device.set_timeout_millis(6000)

        self.file_suffix =  self.getProperty("file_suffix") 
        self.default_exposure_time = self.getProperty("default_exposure_time")
        self.default_compression = self.getProperty("default_compression")
        self.buffer_limit = self.getProperty("buffer_limit")
        self.dcu = self.getProperty("dcu")

        # not all of the following attr are needed, for now all of them here for convenience
        attr_list=('NbImages','Temperature','Humidity','CountTime','FrameTime','PhotonEnergy',
                    'Wavelength','EnergyThreshold','FlatfieldEnabled','AutoSummationEnabled',
                    'TriggerMode','RateCorrectionEnabled','BitDepth','ReadoutTime','Description',
                    'NbImagesMax','NbImagesMin','CountTimeMax','CountTimeMin','FrameTimeMax',
                    'FrameTimeMin','PhotonEnergyMax','PhotonEnergyMin','EnergyThresholdMax',
                    'EnergyThresholdMin','Time','NbTriggers','NbTriggersMax','XPixelSize','YPixelSize',
                    'NbTriggersMin','CountTimeInte','DownloadDirectory','FilesInBuffer','Error',
                    'BeamCenterX','BeamCenterY','DetectorDistance','OmegaIncrement','OmegaStart',
                    'Compression','RoiMode', 'State','XPixelsDetector','YPixelsDetector')
	fw_list = ('FilenamePattern','ImagesPerFile','BufferFree',# 'CompressionEnabled'
		  'FileWriterState', 'ImageNbStart', 'Mode')
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
                       'ImagesPerFile': None,
                       'RoiMode': None,#,
                       'FilenamePattern':None
                       #'PhotonEnergy': None
                     }

        # not all of the following commands are needed, for now all of them here for convenience
        cmd_list = ('Arm','Trigger','Abort','Cancel','ClearBuffer','DeleteFileFromBuffer',
                'Disarm','DownloadFilesFromBuffer')


        for channel_name in attr_list:
            self.addChannel({"type":"tango", 
                             "name": channel_name,
                             "tangoname": tango_device },
                             channel_name)

        for channel_name in fw_list:
            self.addChannel({"type":"tango", 
                             "name": channel_name,
                             "tangoname": filewriter_device },
                             channel_name)
        for cmd_name in cmd_list:
            self.addCommand({"type":"tango",
                             "name": cmd_name, 
                             "tangoname": tango_device },
                             cmd_name)
	print self.getChannelNamesList()
	print self.getCommandNamesList()
        # init the detector settings in case of detector restart
        # use bslz4 for compression ()        
	import time
	time.sleep(1) #this is for avoiding timeout in the next line
        self.getChannelObject('Compression').setValue("bslz4")
        #self.getChannelObject("CompressionEnabled").setValue(True)
        
    def wait_ready(self):
        ## add external trigger, use wait command instead
        acq_status_chan = self.getChannelObject("State")
        with gevent.Timeout(30, RuntimeError("Detector not ready")):
            while acq_status_chan.getValue() != "On":
                time.sleep(1)
 
    def wait_buffer_ready(self):
        with gevent.Timeout(30, RuntimeError("Detector free buffer size is lower than limit")):
            while self.get_buffer_free() < self.buffer_limit:
                time.sleep(1)


    def get_readout_time(self):
        return self.getChannelObject("ReadoutTime").getValue()
  
    def get_buffer_free(self):
        return self.getChannelObject("BufferFree").getValue()

    def get_roi_mode(self):
        return self.getChannelObject("RoiMode").getValue()
 
    def get_pixel_size_x(self):
        """ 
        return sizes of a single pixel along x-axis respectively
        unit, mm
        """
        #x_pixel_size = self.getChannelObject("XPixelSize")  # unit, m 
        x_pixel_size = 0.000075
        return x_pixel_size * 1000

    def get_pixel_size_y(self):
        """
        return sizes of a single pixel along y-axis respectively
        unit, mm
        """
        #y_pixel_size = self.getChannelObject("YPixelSize")  # unit, m
        y_pixel_size = 0.000075
        return y_pixel_size * 1000

    def get_x_pixels_in_detector(self):
        """
        number of pixels along x-axis
        numbers vary depending on the RoiMode
        """
        return self.getChannelObject("XPixelsDetector").getValue()

    def get_y_pixels_in_detector(self):
        """
        number of pixels along y-axis,
        numbers vary depending on the RoiMode
        """
        return self.getChannelObject("YPixelsDetector").getValue()

    
    def get_minimum_exposure_time(self):
        return self.getChannelObject("FrameTimeMin").getValue() - self.get_readout_time()
  
    def get_sensor_thickness(self):
        return # not available, self.getChannelObject("").getValue()

    def set_photon_energy(self,energy):
        """
        set photon_energy
        Note, the readout_time will be changed
        engery, in eV
        """
        self.getChannelObject("PhotonEnergy").setValue(energy)

    def set_energy_threshold(self, erngy):
        """
        set energy_threshold
        Note, the readout_time will be changed
        By deafult, the value is 50% of the photon_energy and will be 
        updated upon setting PhotonEnergy. If other values are needed,
        this should be set after changing PhotonEnergy.
        Eengery, in eV
        """
        self.getChannelObject("EnergyThreshold").setValue(energy)

    @task
    def prepare_acquisition(self, config):
        """
        config is a dictionary
        OmegaStart,OmegaIncrement,
        BeamCenterX
        BeamCenterY
        OmegaStart
        OmegaIncrement
        start, osc_range, exptime, ntrigger, number_of_images, images_per_file, compression,ROI,wavelength):
        """
        
        """This writes into the tango device"""
        self.wait_ready()
        for param in self.config.items():
            if hasattr(self.device, param[0]) and param[1] is not None:
                setattr(self.device, param[0], param[1])
        # check the bufferfree in DCU
        # compression
        #
    
    def has_shutterless(self):
        return True
        
    @task 
    def start_acquisition(self):
        logging.getLogger("user_level_log").info("Preparing acquisition")
        logging.getLogger("user_level_log").info("Detector ready, continuing")

        self.wait_buffer_ready()
        return self.getCommandObject("Arm")()
    
    def stop_acquisition(self):
        """
        when use external trigger, Disarm is required, otherwise the last h5 will 
        not be released and not available in WebDAV.
        """
      
        self.wait_ready()  
  
        try:
            self.getCommandObject("Disarm")()
        except:
            pass
        time.sleep(1)


    def cancel_acquisition(self):
        """Cancel acquisition"""
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

