from ESRFMultiCollect import *
#from detectors.TacoMar import Mar225
from detectors.LimaEiger import Eiger
#from detectors.LimaPilatus import Pilatus
import gevent
import socket
import shutil
import logging
import os
import math
import gevent
#import cPickle as pickle
from PyTango.gevent import DeviceProxy

class ID30A3MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, PixelDetector(Eiger), FixedEnergy(0.9677, 12.812))

        self._notify_greenlet = None

    def upload_images_to_icat(self, template, prefix, run_number, directory, 
                              number_of_images, start_image_number, overlap):
        logging.getLogger("user_level_log").info("Uploading to images to ICAT")
        if math.fabs(overlap) > 1:
            for image_number in range(1, number_of_images + 1):
                h5_master_file_name = "{prefix}_{run_number}_{image_number}_master.h5".format(
                    prefix=prefix, run_number=run_number, image_number=image_number)
                h5_master_file_path = os.path.join(directory, h5_master_file_name)
                self._metadataManagerClient.appendFile(h5_master_file_path)
                h5_data_file_name = "{prefix}_{run_number}_{image_number}_data_000001.h5".format(
                    prefix=prefix, run_number=run_number, image_number=image_number)
                h5_data_file_path = os.path.join(directory, h5_data_file_name)
                self._metadataManagerClient.appendFile(h5_data_file_path)
        else:
            h5_master_file_name = "{prefix}_{run_number}_{start_image_number}_master.h5".format(
                prefix=prefix, run_number=run_number, start_image_number=start_image_number)
            h5_master_file_path = os.path.join(directory, h5_master_file_name)
            self._metadataManagerClient.appendFile(h5_master_file_path)
            for index in range(int((number_of_images-1)/100)+1):
                h5_data_file_name = "{prefix}_{run_number}_{start_image_number}_data_{data_index:06d}.h5".format(
                    prefix=prefix, run_number=run_number, start_image_number=start_image_number, data_index=(index+1))
                h5_data_file_path = os.path.join(directory, h5_data_file_name)
                self._metadataManagerClient.appendFile(h5_data_file_name)

    @task
    def data_collection_hook(self, data_collect_parameters):
      ESRFMultiCollect.data_collection_hook(self, data_collect_parameters)
      self._reset_detector_task = None

      oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
      exp_time = oscillation_parameters['exposure_time']
      if oscillation_parameters['range']/exp_time > 90:
          raise RuntimeError("Cannot move omega axis too fast (limit set to 90 degrees per second).")

      self.first_image_timeout = 30+exp_time*min(100, oscillation_parameters["number_of_images"])
 
      file_info = data_collect_parameters["fileinfo"]
      diagfile = os.path.join(file_info["directory"], file_info["prefix"])+"_%d_diag.dat" % file_info["run_number"]
      self.getObjectByRole("diffractometer").controller.set_diagfile(diagfile)

      self._detector.shutterless = data_collect_parameters["shutterless"]

      """      
      try:
          albula_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
          albula_socket.connect(('localhost', 31337))
      except:
          pass
      else:
          albula_socket.sendall(pickle.dumps({"type":"newcollection"}))
      """
       


    @task
    def get_beam_size(self):
        return self.bl_control.beam_info.get_beam_size()
 
    @task
    def get_slit_gaps(self):
        return (self.bl_control.diffractometer.controller.hgap.position(), self.bl_control.diffractometer.controller.vgap.position())

    def get_measured_intensity(self):
        return 0

    @task
    def get_beam_shape(self):
        return self.bl_control.beam_info.get_beam_shape()

    @task
    def move_detector(self, detector_distance):
        det_distance = self.getObjectByRole("distance")
        det_distance.move(detector_distance)
        while det_distance.motorIsMoving():
          gevent.sleep(0.1)

    @task
    def set_resolution(self, new_resolution):
        self.bl_control.resolution.move(new_resolution)
        while self.bl_control.resolution.motorIsMoving():
          gevent.sleep(0.1)

    def get_resolution_at_corner(self):
        return self.bl_control.resolution.get_value_at_corner()

    def get_detector_distance(self):
        det_distance = self.getObjectByRole("distance")
        return det_distance.getPosition()

    @task
    def move_motors(self, motors_to_move_dict):
        motion = ESRFMultiCollect.move_motors(self,motors_to_move_dict,wait=False)

        # DvS:
        cover_task = gevent.spawn(self.getObjectByRole("eh_controller").detcover.set_out, timeout=15)
        self.getObjectByRole("beamstop").moveToPosition("in", wait=True)
        self.getObjectByRole("light").wagoOut()
        motion.get()
        # DvS:
        cover_task.get()

    @task
    def do_prepare_oscillation(self, *args, **kwargs):
        return

    @task
    def oscil(self, start, end, exptime, npass):
        save_diagnostic = True
        operate_shutter = True
        if self.helical: 
              self.getObjectByRole("diffractometer").helical_oscil(start, end, self.helical_pos, exptime, save_diagnostic)
        else:
              self.getObjectByRole("diffractometer").oscil(start, end, exptime, save_diagnostic, operate_shutter)

    def open_fast_shutter(self):
        self.getObjectByRole("diffractometer").controller.fshut.open()

    def close_fast_shutter(self):
        self.getObjectByRole("diffractometer").controller.fshut.close()

    def stop_oscillation(self):
        self.getObjectByRole("diffractometer").controller.omega.stop()
        self.getObjectByRole("diffractometer").controller.musst.putget("#ABORT")

    def reset_detector(self):
        self.stop_oscillation()
        self._reset_detector_task = ESRFMultiCollect.reset_detector(self, wait=False)

    @task
    def data_collection_cleanup(self):
        self.stop_oscillation()
        self.close_fast_shutter()
        if self._reset_detector_task is not None:
            self._reset_detector_task.get()
 
    def set_helical(self, helical_on):
        self.helical = helical_on

    def set_helical_pos(self, helical_oscil_pos):
        self.helical_pos = helical_oscil_pos

    def set_transmission(self, transmission):
    	self.getObjectByRole("transmission").set_value(transmission)

    def get_transmission(self):
        return self.getObjectByRole("transmission").get_value()

    def get_cryo_temperature(self):
        return 0

    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        self.last_image_filename = filename
        return ESRFMultiCollect.set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path)
       
 
    def adxv_notify(self, image_filename):
        logging.info("adxv_notify %r", image_filename)
        try:
            adxv_notify_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            adxv_notify_socket.connect(("aelita.esrf.fr", 8100))
            adxv_notify_socket.sendall("load_image %s\n" % image_filename)
            adxv_notify_socket.close()
        except:
            pass
        else:
            gevent.sleep(3)
        
    def albula_notify(self, image_filename):
       try:
          albula_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
          albula_socket.connect(('localhost', 31337))
       except:
          pass
       else:
          albula_socket.sendall(pickle.dumps({ "type":"newimage", "path": image_filename }))

    @task
    def write_image(self, last_frame):
        ESRFMultiCollect.write_image(self, last_frame)
        if last_frame:
            gevent.spawn_later(1, self.adxv_notify, self.last_image_filename)
        else:
            if self._notify_greenlet is None or self._notify_greenlet.ready():
                self._notify_greenlet = gevent.spawn_later(1, self.adxv_notify, self.last_image_filename)

#    def trigger_auto_processing(self, *args, **kw):
#        return

    @task
    def prepare_intensity_monitors(self):
        i1 = DeviceProxy("id30/keithley_massif3/i1")
        i0 = DeviceProxy("id30/keithley_massif3/i0")
        i1.autorange = False
        i1.range = i0.range

    def get_beam_centre(self):
        return self.bl_control.resolution.get_beam_centre()

    @task
    def write_input_files(self, datacollection_id):
        # copy *geo_corr.cbf* files to process directory
	
	# DvS 23rd Feb. 2016: For the moment, we don't have these correction files for the Eiger,
	# thus skipping the copying for now:
	# 	
        # try:
        #     process_dir = os.path.join(self.xds_directory, "..")
        #     raw_process_dir = os.path.join(self.raw_data_input_file_dir, "..")
        #     for dir in (process_dir, raw_process_dir):
        #         for filename in ("x_geo_corr.cbf.bz2", "y_geo_corr.cbf.bz2"):
        #             dest = os.path.join(dir,filename)
        #             if os.path.exists(dest):
        #                 continue
        #             shutil.copyfile(os.path.join("/data/pyarch/id30a3", filename), dest)
        # except:
        #     logging.exception("Exception happened while copying geo_corr files")

        return ESRFMultiCollect.write_input_files(self, datacollection_id)


