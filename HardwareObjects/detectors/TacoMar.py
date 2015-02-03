import TacoDevice
import time
import logging
import os
from HardwareRepository.TaskUtils import task, cleanup, error_cleanup
import gevent

MAR_READ,MAR_CORRECT,MAR_WRITE,MAR_DEZINGER = 1,2,3,4
MAR_IDLE, MAR_QUEUED, MAR_EXEC, MAR_ERROR, MAR_RESERVED = 0,1,2,4,8
MAR_ACQUIRE = 0

class Mar225:
    def init(self, config, collect_obj):
        self.config = config
        self.collect_obj = collect_obj
        self.header = dict()

        taco_device = config.getProperty("mar_device")

        for cmdname, taco_cmdname in (("detector_state", "DevState"),
                                      ("detector_substate", "DevSubState"),
                                      ("detector_status", "DevStatus"),
                                      ("detector_setthumbnail1", "DevCcdSetThumbnail1"),
                                      ("detector_setthumbnail2", "DevCcdSetThumbnail2"),
                                      ("detector_stop", "DevCcdStop"),
                                      ("detector_setheader", "DevCcdHeader"),
                                      ("detector_start_exposure", "DevCcdStart"),
                                      ("detector_setbin", "DevCcdSetBin"),
                                      ("detector_getbin", "DevCcdGetBin"),
                                      ("detector_xsize", "DevCcdXSize"),
                                      ("detector_dezinger", "DevCcdDezinger"),
                                      ("detector_write", "DevCcdWriteFile")):
            self.addCommand({"type":"taco", "name":cmdname, "taconame": taco_device}, taco_cmdname)
        
        # set Taco timeout to 15 seconds
        self.getCommandObject("detector_state").device.timeout(15)

    def execute_command(self, cmd_name, *args):
        return self.getCommandObject(cmd_name)(*args)

    def _wait(self, task, end_state=MAR_IDLE, timeout=5):
        with gevent.Timeout(timeout, RuntimeError("MAR detector: Timeout waiting for state")):
            while self._get_task_state(task, end_state):
                time.sleep(0.1)

    def _get_task_state(self, task, expected_state=MAR_IDLE):
        if self.execute_command("detector_substate", task) == expected_state:
            return 0
        else:
            return 1
        
    def wait(self):
        with gevent.Timeout(20, RuntimeError("Timeout waiting for detector")):
            logging.debug("CCD clearing...")
            if self._get_task_state(MAR_ACQUIRE):
                logging.debug("CCD integrating...")
            if self._get_task_state(MAR_READ):
                logging.debug("CCD reading out...")
                self._wait(MAR_READ)
                logging.debug("CCD reading done.")
            if self._get_task_state(MAR_CORRECT):
                logging.debug("CCD correcting...")
                self._wait(MAR_CORRECT)
                logging.debug("CCD correction done.")

    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment="", energy=None, still=False):
        self.header["start_phi"] = start
        self.header["rotation_range"] = osc_range
        self.header["exposure_time"] = exptime
        self.header["dataset_comments"] = comment
        self.header["file_comments"] = ""
        self.current_filename = ""
	self.current_thumbnail2 = ""
	self.current_thumbnail1 = ""

        self.stop()

        if take_dark:
            logging.info("CCD: taking a background")
            if self.execute_command("detector_state") == 2:
                logging.debug("CCD clearing before background image...")
                self.stop_acquisition()
            self.wait()
            self.execute_command("detector_stop", ["1","","",""])
            logging.debug("CCD readout...")
            self.wait()
        
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        self.header["xtal_to_detector"] = self.collect_obj.get_detector_distance()
        self.header["source_wavelength"] = self.collect_obj.get_wavelength()
        bx, by = self.collect_obj.get_beam_centre()
        self.header["beam_x"] = bx
        self.header["beam_y"] = by
        self.header["file_comment"] = filename
       
        if not os.path.isdir(os.path.dirname(jpeg_full_path)): 
            os.makedirs(os.path.dirname(jpeg_full_path))
        
        self.current_thumbnail1 =  jpeg_full_path
        self.current_thumbnail2 = jpeg_thumbnail_full_path
        self.current_filename = filename

    def _check_background(self):
        xsize    = self.execute_command("detector_xsize", 0)
        bkg_xsize= self.execute_command("detector_xsize", 1)
        # if binning has changed raw size if different than bkg size and at startup
        # time bkg size is 0.
        return bkg_xsize & xsize

    def take_background(self):
        if self.execute_command("detector_state") == 2:
            logging.debug("CCD: clearing before background image")
            self.stop_acquisition()

        self.wait()

        logging.debug("CCD: reading scratch image")
        self._wait(MAR_READ)
        self.execute_command("detector_stop", ["2","","",""])
        logging.debug("CCD: readout...")

        logging.debug("CCD: reading background image")
        self._wait(MAR_READ)
        self.execute_command("detector_stop", ["1","","",""])
        logging.debug("CCD: readout...")

        self.wait()

        logging.debug("CCD: Zinger correction")
        self.execute_command("detector_dezinger", 1)
        self.wait()

    def start_acquisition(self, exptime, npass, first_frame):
        with error_cleanup(self.stop):
            if self._check_background() == 0:
                self.take_background()
            
            self._wait(MAR_READ)

            self.execute_command("detector_start_exposure")

            self._wait(MAR_ACQUIRE, MAR_EXEC)
        
            logging.debug("CCD integrating...")

    def stop(self):
        self._wait(MAR_READ, MAR_IDLE)
        self.execute_command("detector_stop", ["0","","",""])

    def write_image(self, last_frame):
        pass

    def _send_header(self):
        header = []
        for header_info, value in self.header.iteritems():
            header.append("%s=%s" % (header_info, value))
        self.execute_command("detector_setheader", header)

    def stop_acquisition(self):
        #import pdb;pdb.set_trace()
        self.execute_command("detector_setthumbnail1", ["JPG", "1024", "1024"])
        self.execute_command("detector_setthumbnail2", ["JPG", "250", "250"])
        self._wait(MAR_READ)
        self._send_header()
        self.execute_command("detector_stop", ["0",self.current_filename,self.current_thumbnail1,self.current_thumbnail2])
        self._wait(MAR_READ, MAR_EXEC)
        
        logging.debug("CCD readout...")


