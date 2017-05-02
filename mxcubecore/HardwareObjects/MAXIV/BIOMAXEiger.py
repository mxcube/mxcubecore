"""

  File:  BIOMAXEiger.py

  Description:  This module implements the hardware object for the Eiger detector
     based on a Tango device server


Detector Status:
-----------------

hardware status:
   ready:   ready for trigger (this is the state after an "Arm" command)
   idle:    ready for config (this should be the state after a "Disarm" command)

hardware object status:

   configuring:  a configuration task is ongoing


"""

import gevent
import time
import copy
import logging

from HardwareRepository import HardwareRepository
from HardwareRepository.TaskUtils import task
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
        self.config_state = None
        self.initialized = False
        self.status_chan = None

        # defaults
        self.energy_change_threshold_default = 20

    def init(self):
        tango_device = self.getProperty("detector_device")
        filewriter_device = self.getProperty("filewriter_device")

        self.file_suffix = self.getProperty("file_suffix")
        self.default_exposure_time = self.getProperty("default_exposure_time")
        self.default_compression = self.getProperty("default_compression")
        self.buffer_limit = self.getProperty("buffer_limit")
        self.dcu = self.getProperty("dcu")

        # not all of the following attr are needed, for now all of them here for convenience
        attr_list = ('NbImages', 'Temperature', 'Humidity', 'CountTime', 'FrameTime', 'PhotonEnergy',
                     'Wavelength', 'EnergyThreshold', 'FlatfieldEnabled', 'AutoSummationEnabled',
                     'TriggerMode', 'RateCorrectionEnabled', 'BitDepth', 'ReadoutTime', 'Description',
                     'NbImagesMax', 'NbImagesMin', 'CountTimeMax', 'CountTimeMin', 'FrameTimeMax',
                     'FrameTimeMin', 'PhotonEnergyMax', 'PhotonEnergyMin', 'EnergyThresholdMax',
                     'EnergyThresholdMin', 'Time', 'NbTriggers', 'NbTriggersMax', 'XPixelSize',
                     'YPixelSize', 'NbTriggersMin', 'CountTimeInte', 'DownloadDirectory',
                     'FilesInBuffer', 'Error', 'BeamCenterX', 'BeamCenterY', 'DetectorDistance',
                     'OmegaIncrement', 'OmegaStart', 'Compression', 'RoiMode', 'State', "Status",
                     'XPixelsDetector', 'YPixelsDetector'
                     )

        fw_list = ('FilenamePattern', 'ImagesPerFile', 'BufferFree', 'FileWriterState', 'ImageNbStart', 'Mode')

        # config needed to be set up for data collection
        # if values are None, use the one from the system
        self.col_config = {'OmegaStart': 0,
                           'OmegaIncrement': 0.1,
                           'BeamCenterX': None,  # length not pixel
                           'BeamCenterY': None,
                           'DetectorDistance': None,
                           'CountTime': None,
                           'NbImages': None,
                           'NbTriggers': None,
                           'ImagesPerFile': None,
                           'RoiMode': None,
                           'FilenamePattern': None,
                           'PhotonEnergy': None,
                           'TriggerMode': "exts",
                           }

        # not all of the following commands are needed, for now all of them here for convenience
        cmd_list = ('Arm', 'Trigger', 'Abort', 'Cancel', 'ClearBuffer', 'DeleteFileFromBuffer',
                    'Disarm', 'DownloadFilesFromBuffer'
                    )

        for channel_name in attr_list:
            self.addChannel({"type": "tango",
                             "name": channel_name,
                             "tangoname": tango_device,
                             "timeout": 10000,
                             },
                            channel_name
                            )

        # we need to program timeout once in the device
        # get any of the channels for that.

        for channel_name in fw_list:
            self.addChannel({"type": "tango",
                             "name": channel_name,
                             "tangoname": filewriter_device
                             },
                            channel_name
                            )

        for cmd_name in cmd_list:
            self.addCommand({"type": "tango",
                             "name": cmd_name,
                             "timeout": 8000,
                             "tangoname": tango_device
                             },
                            cmd_name
                            )
        # init the detector settings in case of detector restart
        # use bslz4 for compression ()

        # we need to call the init device before accessing the channels here
        #   otherwise the initialization is triggered by the HardwareRepository Poller
        #   that is delayed after the application starts

        try:
            self.energy_change_threshold = float(self.getProperty("min_trigger_energy_change"))
        except:
            self.energy_change_threshold = self.energy_change_threshold_default

        self.getChannelObject('Compression').init_device()
        self.getChannelObject('Compression').setValue("bslz4")

        # self.getChannelObject('TriggerMode').init_device()
        # self.getChannelObject('TriggerMode').setValue("exts")

    #  STATUS , status can be "idle", "ready", "UNKNOWN"
    def get_status(self):
        if self.status_chan is None:
            self.status_chan = self.getChannelObject("Status")

            if self.status_chan is not None:
                self.initialized = True
            else:
                return "not_init"

        return self.status_chan.getValue().split('\n')[0]

    def is_idle(self):
        return self.get_status() == "idle"

    def is_ready(self):
        return self.get_status() == "ready"

    def is_acquire(self):
        return self.get_status() == "acquire"

    def is_preparing(self):
        return self.config_state == "config"

    def prepare_error(self):
        if self.config_state == "error":
            return True
        else:
            return False

    def wait_ready(self):
        with gevent.Timeout(20, RuntimeError("Detector not ready")):
            while not self.is_ready():
                gevent.sleep(0.1)

    def wait_ready_or_idle(self):
        with gevent.Timeout(20, RuntimeError("Detector neither ready or idle")):
            while not (self.is_ready() or self.is_idle()):
                logging.getLogger("HWR").debug("Waiting for the detector to be ready, current state: " + self.get_status())
                gevent.sleep(0.1)

    def wait_idle(self):
        with gevent.Timeout(20, RuntimeError("Detector not ready")):
            while not self.is_idle():
                gevent.sleep(0.1)

    def wait_acquire(self):
        with gevent.Timeout(20, RuntimeError("Detector not ready")):
            while not self.is_acquire():
                gevent.sleep(0.1)

    def wait_buffer_ready(self):
        with gevent.Timeout(20, RuntimeError("Detector free buffer size is lower than limit")):
            while self.get_buffer_free() < self.buffer_limit:
                gevent.sleep(0.1)

    def wait_config_done(self):
        logging.getLogger("HWR").info("Waiting to configure the detector.")
	print self.config_state 
        with gevent.Timeout(30, RuntimeError("Detector configuration error")):
            while self.is_preparing():
		print self.config_state 
                gevent.sleep(0.1)
        logging.getLogger("HWR").info("Detector configuration finished.")
    
    #  STATUS END

    #  GET INFORMATION
    def get_value(self, name):
        return self.getChannelObject(name).getValue()

    def set_value(self, name, value):
	try:
            self.getChannelObject(name).setValue(value)
	    logging.getLogger("HWR").debug("[DETECTOR] Setting value: %s for attribute %s"  %(value, name))
	except Exception as ex:
	    print ex
	    logging.getLogger("HWR").info("Cannot set value: %s for attribute %s"  %(value, name))

    def get_readout_time(self):
        return self.get_value("ReadoutTime")

    def get_acquisition_time(self):
        frame_time = self.get_value("FrameTime")
        readout_time = self.get_value("ReadoutTime")
        nb_images = self.get_value("NbImages")
        time =  nb_images * frame_time - readout_time
	_count_time = self._config_vals.get('CountTime') 
	_nb_images = self._config_vals.get('NbImages')  
	logging.getLogger("HWR").debug("[DETECTOR] Configuration params: CounTime: %s, NbImages: %s" %(_count_time, _nb_images))
	logging.getLogger("HWR").debug("[DETECTOR] Params applied IN the detector: FrameTime: %s, NbImages: %s" %(frame_time, nb_images))
	if time != _nb_images * _count_time - readout_time:
	    logging.getLogger("HWR").error("[DETECTOR] Acquisition time configuration wrong.")    
	logging.getLogger("HWR").info("Detector acquisition time: "+str(time))
        return time

    def get_buffer_free(self):
        return self.get_value("BufferFree")

    def get_roi_mode(self):
        return self.get_value("RoiMode")

    def get_pixel_size_x(self):
        """
        return sizes of a single pixel along x-axis respectively
        unit, mm
        """
        # x_pixel_size = self.getChannelObject("XPixelSize")  # unit, m
        x_pixel_size = 0.000075
        return x_pixel_size * 1000

    def get_pixel_size_y(self):
        """
        return sizes of a single pixel along y-axis respectively
        unit, mm
        """
        # y_pixel_size = self.getChannelObject("YPixelSize")  # unit, m
        y_pixel_size = 0.000075
        return y_pixel_size * 1000

    def get_x_pixels_in_detector(self):
        """
        number of pixels along x-axis
        numbers vary depending on the RoiMode
        """
        return self.get_value("XPixelsDetector")

    def get_y_pixels_in_detector(self):
        """
        number of pixels along y-axis,
        numbers vary depending on the RoiMode
        """
        return self.get_value("YPixelsDetector")

    def get_minimum_exposure_time(self):
        return self.get_value("FrameTimeMin") - self.get_readout_time()

    def get_sensor_thickness(self):
        return  # not available, self.getChannelObject("").getValue()

    def has_shutterless(self):
        return True

    #  GET INFORMATION END

    #  SET VALUES
    def set_photon_energy(self, energy):
        """
        set photon_energy
        Note, the readout_time will be changed
        engery, in eV
        """
        valid = self._validate_energy_value(energy)

        if valid == -1:
            return False
        elif valid == 0:
            return True  # is valid, but no need to change energy. continue
        else:
            self.set_value("PhotonEnergy", energy)
            return True

    def _validate_energy_value(self, energy):
        try:
            target_energy = float(energy)
        except:
            # not a valid value
            logging.getLogger("user_level_log").info("Wrong Energy value: %s" % energy)
            return -1

        max_energy = self.get_value("PhotonEnergyMax")
        min_energy = self.get_value("PhotonEnergyMin")
        current_energy = self.get_value("PhotonEnergy")

        print("   - currently configured energy is: %s" % current_energy)
        print("   -    min val: %s / max val: %s " % (min_energy, max_energy))

        if target_energy < min_energy or target_energy > max_energy:
            print("Energy value out of limits: %s" % energy)
            logging.getLogger("user_level_log").info("Energy value out of limits: %s" % energy)
            return -1

        if abs(energy-current_energy) > self.energy_change_threshold:
            print("Energy difference over threshold. program energy necessary")
            return 1
        else:
            print("Energy difference below threshold. Do not need to program")
            return 0

    def set_energy_threshold(self, threshold):
        """
        set energy_threshold
        Note, the readout_time will be changed
        By deafult, the value is 50% of the photon_energy and will be
        updated upon setting PhotonEnergy. If other values are needed,
        this should be set after changing PhotonEnergy.
        Eengery, in eV
        """
        self.set_value("EnergyThreshold", threshold)

    #  SET VALUES END

    def prepare_acquisition(self, config):
        """
        config is a dictionary
        OmegaStart,OmegaIncrement,
        BeamCenterX
        BeamCenterY
        OmegaStart
        OmegaIncrement
        start, osc_range, exptime, ntrigger, number_of_images, images_per_file,
        compression,ROI,wavelength):
        """

        logging.getLogger("user_level_log").info("Preparing acquisition")

        self.config_state = "config"

        self._config_vals = copy.copy(config)
       # self._config_task = gevent.spawn(self._prepare_acquisition_sequence)
       # self._config_task.link(self._configuration_done)
       # self._config_task.link_exception(self._configuration_failed)
	try:
	    self._prepare_acquisition_sequence()
	except Exception as ex:
	    print ex
	    self._configuration_failed()
	else:
     	    self._configuration_done()

    def _configuration_done(self): # (self, gl)
	logging.getLogger("HWR").info("Detector configuration done")
        self.config_state = None

    def _configuration_failed(self): # (self, gl)
        self.config_state = "error"
	logging.getLogger("HWR").error("Could not configure detector")
        RuntimeError("Could not configure detector")

    def _prepare_acquisition_sequence(self):

        if not self.is_idle():
            self.stop_acquisition()

        self.wait_idle()
	
	logging.getLogger("HWR").info("Ok. detector is idle. Continuing with configuration")
        print("Ok. detector is idle. Continuing with configuration")
        logging.getLogger("HWR").info(self._config_vals)	
        if "PhotonEnergy" in self._config_vals.keys():
            new_egy = self._config_vals["PhotonEnergy"]
            if new_egy is not None:
                if self.set_photon_energy(new_egy) is False:
                    raise Exception("Could not program energy in detector")
        if "CountTime" in self._config_vals.keys():
            self.set_value("CountTime",  self._config_vals["CountTime"])
            print "readout time and count time is ", self.get_readout_time(), self.get_value("CountTime")
            self.set_value("FrameTime",  self._config_vals["CountTime"]+self.get_readout_time())
            print "new frame time is ", self.get_value("FrameTime")
            for cfg_name, cfg_value in self._config_vals.items():
                t0 = time.time()
                if cfg_name == "PhotonEnergy" or cfg_name == "CountTime":
                    continue  # already handled above

                logging.getLogger("HWR").info("Detector: configuring %s: %s" % (cfg_name, cfg_value))
                if cfg_value is None or cfg_value == "":
                    continue

                if cfg_value is not None:
                    if self.get_value(cfg_name) != cfg_value:
                        self.set_value(cfg_name, cfg_value)
                        if cfg_name == "RoiMode":
                            self.emit("roiChanged")
                    else:
                        print("      - value does need to change")
                else:
                    logging.getLogger("HWR").error("Could not config value %s for detector. Not such channel" % cfg_name)
		logging.getLogger("HWR").info("Detector parameter configuration took %s seconds" % (time.time() - t0))
                print(" took %s seconds" % (time.time() - t0))

    @task
    def start_acquisition(self):
        """
        Before starting the acquisition a prepare_acquisition should be issued
        After prepare_acquisition the detector should be in "idle" state

        Otherwise you will have to send a "disarm" command by hand to be able to
        start an acquisition
        """

        self.wait_buffer_ready()

        if not self.is_idle():
            RuntimeError("Detector should be idle before starting a new acquisition")

        self.config_state = None

        logging.getLogger("user_level_log").info("Detector going to arm")

        return self.arm()

    def stop_acquisition(self):
        """
        when use external trigger, Disarm is required, otherwise the last h5 will
        not be released and not available in WebDAV.
        """

        print("Stop acquisition. waiting")
        logging.getLogger("HWR").info("[DETECTOR] Stop acquisition, waiting...")
        self.wait_ready_or_idle()

        try:
            self.cancel()
            # this is needed as disarm in tango device server does not seem to work
            # as expected. the disarm command in the simpleinterface is always working
            # when called from Tango it does not. Once bug is solved in tango server, the
            # call to "cancel()" is not necessary here
            self.disarm()
            logging.getLogger("HWR").info("[DETECTOR] Stop acquisition, detector canceled and disarmed.")
        except:
            pass

    def cancel_acquisition(self):
        """Cancel acquisition"""
        logging.getLogger("HWR").info("[DETECTOR] Cancelling acquisition")
        try:
            self.cancel()
        except:
            pass

        time.sleep(1)
        self.disarm()

    def arm(self):
        logging.getLogger("HWR").info("[DETECTOR] Arm command requested")
        cmd = self.getCommandObject("Arm")
        cmd.setTimeout(10000)
        cmd()
	self.wait_ready()
        logging.getLogger("HWR").info("[DETECTOR] Arm command executed, new state of the dectector: " + self.get_status())
        logging.getLogger("user_level_log").info("Detector armed")

    def trigger(self):
        self.getCommandObject("Trigger")()

    def disarm(self):
        self.getCommandObject("Disarm")()

    def cancel(self):
        self.getCommandObject("Cancel")()

    def abort(self):
        try:
            self.getCommandObject("Abort")()
        except:
            pass


def test():
    import sys
    import os

    if len(sys.argv) != 5:
        print("Usage: %s triggermode (exts/ints) nb_images exp_time energy" % sys.argv[0])
        sys.exit(0)
    else:
        try:
            trigmode = sys.argv[1]
            nimages = float(sys.argv[2])
            exptime = float(sys.argv[3])
            egy = float(sys.argv[4])
        except ValueError:
            print "Cannot decode parameters. Aborting"
            sys.exit(0)

    if trigmode not in ["exts", "ints"]:
        print('Bad trigger mode. It should be "exts" or "ints"')
        sys.exit(0)

    hwr = HardwareRepository.HardwareRepository(os.environ.get("XML_FILES_PATH"))
    hwr.connect()
    obj = hwr.getHardwareObject("/detector")

    config = {
         'OmegaStart': 0,
         'OmegaIncrement': 0.1,
         'BeamCenterX': None,  # length not pixel
         'BeamCenterY': None,
         'DetectorDistance': None,
         'FrameTime': exptime,
         'NbImages': nimages,
         'NbTriggers': None,
         'ImagesPerFile': None,
         'RoiMode': "4M",
         'FilenamePattern': None,
         'PhotonEnergy': egy,
         'TriggerMode': trigmode,
        }

    if obj.get_status() == "not_init":
        print("Cannot initialize hardware object")
        sys.exit(0)

    if not obj.is_idle():
        obj.stop_acquisition()
        obj.wait_idle()

    obj.prepare_acquisition(config)

    print("Waiting for configuration finished")

    while obj.is_preparing():
        gevent.wait(timeout=0.1)
        gevent.sleep(0.1)
        print "."

    if obj.prepare_error():
        print "Prepare went wrong. Aborting"
        sys.exit(0)

    readout_time = obj.get_readout_time()
    print("EIGER configuration done")

    print("Starting acquisition (trigmode = %s)" % trigmode)
    if trigmode == "exts":
        total_time = nimages * (exptime + readout_time)
        print("Total exposure time (estimated) will be: %s", total_time)

    try:
        obj.start_acquisition()

        if trigmode == "exts":
            print("  - waiting for trigger.")
            sys.stdout.flush()
            obj.wait_acquire()
            print("  - trigger received. Acquiring")
            obj.wait_ready_or_idle()
        else:
            obj.trigger()
            obj.wait_ready_or_idle()

        obj.stop_acquisition()
        print("Acquisition done")
    except KeyboardInterrupt:
        obj.abort()
        obj.wait_idle()


if __name__ == "__main__":
    test()
