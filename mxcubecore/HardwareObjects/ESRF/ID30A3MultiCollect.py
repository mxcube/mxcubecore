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

        self._detector.shutterless = data_collect_parameters["shutterless"]

    @task
    def get_beam_size(self):
        return self.bl_control.beam_info.get_beam_size()
 
    @task
    def get_slit_gaps(self):
        ctrl = self.getObjectByRole("controller")
        return (ctrl.s1h.position(), ctrl.s1v.position())

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
        diffr = self.bl_control.diffractometer
        try:
            motors_to_move_dict.pop('kappa')
            motors_to_move_dict.pop('kappa_phi')
        except:
            pass
        diffr.moveSyncMotors(motors_to_move_dict, wait=True, timeout=200)

        """
        motion = ESRFMultiCollect.move_motors(self,motors_to_move_dict,wait=False)

        # DvS:
        cover_task = gevent.spawn(self.getObjectByRole("eh_controller").detcover.set_out, timeout=15)
        self.getObjectByRole("beamstop").moveToPosition("in", wait=True)
        self.getObjectByRole("light").wagoOut()
        motion.get()
        # DvS:
        cover_task.get()
        """

    @task
    def take_crystal_snapshots(self, number_of_snapshots):
       if self.bl_control.diffractometer.in_plate_mode():
            if number_of_snapshots > 0:
                number_of_snapshots = 1

       #this has to be done before each chage of phase
       self.bl_control.diffractometer.getCommandObject("save_centring_positions")()
       # not going to centring phase if in plate mode (too long)
       if not self.bl_control.diffractometer.in_plate_mode():        
           self.bl_control.diffractometer.moveToPhase("Centring", wait=True, timeout=200)
       self.bl_control.diffractometer.takeSnapshots(number_of_snapshots, wait=True)




    @task
    def do_prepare_oscillation(self, *args, **kwargs):
        #set the detector cover out
        self.getObjectByRole("controller").detcover.set_out()
        diffr = self.getObjectByRole("diffractometer")
        #send again the command as MD2 software only handles one
        #centered position!!
        #has to be where the motors are and before changing the phase
        diffr.getCommandObject("save_centring_positions")()
        #move to DataCollection phase
        if diffr.getPhase() != "DataCollection":
            logging.getLogger("user_level_log").info("Moving MD2 to Data Collection")
        diffr.moveToPhase("DataCollection", wait=True, timeout=200)
        #switch on the front light
        diffr.getObjectByRole("flight").move(0.8)
        #take the back light out
        diffr.getObjectByRole("lightInOut").actuatorOut()

    @task
    def oscil(self, start, end, exptime, npass, wait=True):
        diffr = self.getObjectByRole("diffractometer")
        if self.helical:
            diffr.oscilScan4d(start, end, exptime, self.helical_pos, wait=True)
        elif self.mesh:
            diffr.oscilScanMesh(start, end, exptime, self._detector.get_deadtime(), self.mesh_num_lines, self.mesh_total_nb_frames, self.mesh_center, self.mesh_range , wait=True) 
        else:
            diffr.oscilScan(start, end, exptime, wait=True)
            
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        energy = self._tunable_bl.getCurrentEnergy()
        return self._detector.prepare_acquisition(take_dark, start, osc_range, exptime, npass, number_of_images, comment, energy, self.mesh)


    def open_fast_shutter(self):
        self.getObjectByRole("fastshut").actuatorIn()

    def close_fast_shutter(self):
        self.getObjectByRole("fastshut").actuatorOut()

    def stop_oscillation(self):
        #self.getObjectByRole("diffractometer").controller.omega.stop()
        #self.getObjectByRole("diffractometer").controller.musst.putget("#ABORT")
        pass

    def reset_detector(self):
        self.stop_oscillation()
        self._reset_detector_task = ESRFMultiCollect.reset_detector(self, wait=False)

    @task
    def data_collection_cleanup(self):
        #self.stop_oscillation()
        self.getObjectByRole("diffractometer")._wait_ready(10)
        state = self.getObjectByRole("fastshut").getActuatorState(read=True)
        if state != "out":
            self.close_fast_shutter()

        if self._reset_detector_task is not None:
            self._reset_detector_task.get()
 
    def set_helical(self, helical_on):
        self.helical = helical_on

    def set_helical_pos(self, helical_oscil_pos):
        self.helical_pos = helical_oscil_pos
        
    # specifies the next scan will be a mesh scan
    def set_mesh(self, mesh_on):
        self.mesh = mesh_on

    def set_mesh_scan_parameters(self, num_lines, total_nb_frames, mesh_center_param, mesh_range_param):
        """
        sets the mesh scan parameters :
         - vertcal range
         - horizontal range
         - nb lines
         - nb frames per line
         - invert direction (boolean)  # NOT YET DONE
         """
        self.mesh_num_lines = num_lines
        self.mesh_total_nb_frames = total_nb_frames
        self.mesh_range = mesh_range_param
        self.mesh_center = mesh_center_param

        
        
        

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
        """
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
        """
        return ESRFMultiCollect.write_input_files(self, datacollection_id)


