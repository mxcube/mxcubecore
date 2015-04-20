from ESRFMultiCollect import *
from detectors.LimaPilatus import Pilatus
import gevent
import socket
import shutil
import logging
import os
import gevent
#import cPickle as pickle

class ID30BMultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, PixelDetector(Pilatus), TunableEnergy())

    @task
    def data_collection_hook(self, data_collect_parameters):
      self._detector.shutterless = data_collect_parameters["shutterless"]
      
    @task
    def get_beam_size(self):
        return self.bl_control.beam_info.get_beam_size()
 
    @task
    def get_slit_gaps(self):
        khoros = self.getObjectByRole("khoros")

        return (None,None)

    def get_measured_intensity(self):
        return 0

    @task
    def get_beam_shape(self):
        return self.bl_control.beam_info.get_beam_shape()

    @task
    def move_detector(self, detector_distance):
        det_distance = self.getObjectByRole("detector_distance")
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
        det_distance = self.getObjectByRole("detector_distance")
        return det_distance.getPosition()

    def ready(*motors):
        return not any([m.motorIsMoving() for m in motors])

    @task
    def move_motors(self, motors_to_move_dict):
        """
        def wait_ready(timeout=None):
            with gevent.Timeout(timeout):
                while not self.ready(*motors_to_move_dict.keys()):
                    time.sleep(0.1)

        wait_ready(timeout=30)

        if not ready(*motors_to_move_dict.keys()):
            raise RuntimeError("Motors not ready")

        for motor, position in motors_to_move_dict.iteritems():
            motor.move(position)
  
        wait_ready()
        """
  
        diffr = self.getObjectByRole("diffractometer")
        #cover_task = self.getObjectByRole("khoros").detcover.set_out(wait=False, timeout=15)
        diffr.moveToPhase("DataCollection", wait=True, timeout=20)
        diffr.moveSyncMotors(motors_to_move_dict, wait=True, timeout=20)
        #cover_task.get()

    @task
    def do_prepare_oscillation(self, *args, **kwargs):
        #switch on the front light
        self.getObjectByRole("diffractometer").getObjectByRole("flight").move(2)

    @task
    def oscil(self, start, end, exptime, npass):
        diffr = self.getObjectByRole("diffractometer")
        if self.helical:
            diffr.oscilScan4d(start, end, self.helical_pos, exptime, wait=True)
        else:
            diffr.oscilScan(start, end, exptime, wait=True)

    def open_fast_shutter(self):
        #self.getObjectByRole("diffractometer").controller.fshut.open()
        self.getObjectByRole("fastshut").actuatorIn()

    def close_fast_shutter(self):
        #self.getObjectByRole("diffractometer").controller.fshut.close()
        self.getObjectByRole("fastshut").actuatorOut()

    def set_helical(self, helical_on):
        self.helical = helical_on

    def set_helical_pos(self, helical_oscil_pos):
        #import pdb; pdb.set_trace()
        self.helical_pos = helical_oscil_pos

    def set_transmission(self, transmission):
    	self.getObjectByRole("transmission").set_value(transmission)

    def get_transmission(self):
        return self.getObjectByRole("transmission").get_value()

    def get_cryo_temperature(self):
        return 0

    @task
    def prepare_intensity_monitors(self):
        return

    def get_beam_centre(self):
        return self.bl_control.resolution.get_beam_centre()

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
                    shutil.copyfile(os.path.join("/data/pyarch/id30b", filename), dest)
        except:
            logging.exception("Exception happened while copying geo_corr files")

        return ESRFMultiCollect.write_input_files(self, datacollection_id)


