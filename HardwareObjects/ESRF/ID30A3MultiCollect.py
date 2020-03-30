import gevent
import socket
import logging
import pickle as pickle

from HardwareRepository.TaskUtils import task

from .ESRFMultiCollect import ESRFMultiCollect, FixedEnergy, PixelDetector
from HardwareRepository.HardwareObjects.LimaEigerDetector import Eiger
from PyTango.gevent import DeviceProxy


class ID30A3MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, FixedEnergy(0.9677, 12.812))

        self._notify_greenlet = None

    @task
    def data_collection_hook(self, data_collect_parameters):
        ESRFMultiCollect.data_collection_hook(self, data_collect_parameters)

        oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
        exp_time = oscillation_parameters["exposure_time"]
        if oscillation_parameters["range"] / exp_time > 90:
            raise RuntimeError(
                "Cannot move omega axis too fast (limit set to 90 degrees per second)."
            )

        self.first_image_timeout = 30 + exp_time * min(
            100, oscillation_parameters["number_of_images"]
        )

        data_collect_parameters["fileinfo"]

        self._detector.shutterless = data_collect_parameters["shutterless"]

    @task
    def get_beam_size(self):
        return self.bl_control.beam_info.get_beam_size()

    @task
    def get_slit_gaps(self):
        ctrl = self.getObjectByRole("controller")
        return (ctrl.s1h.position(), ctrl.s1v.position())

    @task
    def get_beam_shape(self):
        return self.bl_control.beam_info.get_beam_shape()

    def get_resolution_at_corner(self):
        return self.bl_control.resolution.get_value_at_corner()

    @task
    def move_motors(self, motors_to_move_dict):
        diffr = self.bl_control.diffractometer
        try:
            motors_to_move_dict.pop("kappa")
            motors_to_move_dict.pop("kappa_phi")
        except BaseException:
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

        # this has to be done before each chage of phase
        self.bl_control.diffractometer.get_command_object("save_centring_positions")()
        # not going to centring phase if in plate mode (too long)
        if not self.bl_control.diffractometer.in_plate_mode():
            self.bl_control.diffractometer.moveToPhase(
                "Centring", wait=True, timeout=200
            )
        self.bl_control.diffractometer.takeSnapshots(number_of_snapshots, wait=True)

    @task
    def do_prepare_oscillation(self, *args, **kwargs):
        # set the detector cover out
        self.getObjectByRole("controller").detcover.set_out()
        diffr = self.getObjectByRole("diffractometer")
        # send again the command as MD2 software only handles one
        # centered position!!
        # has to be where the motors are and before changing the phase
        diffr.get_command_object("save_centring_positions")()
        # move to DataCollection phase
        if diffr.getPhase() != "DataCollection":
            logging.getLogger("user_level_log").info("Moving MD2 to Data Collection")
        diffr.moveToPhase("DataCollection", wait=True, timeout=200)
        # switch on the front light
        diffr.getObjectByRole("FrontLight").set_value(0.8)
        # take the back light out
        diffr.getObjectByRole("BackLightSwitch").actuatorOut()

    @task
    def oscil(self, start, end, exptime, npass, wait=True):
        diffr = self.getObjectByRole("diffractometer")
        if self.helical:
            diffr.oscilScan4d(start, end, exptime, self.helical_pos, wait=True)
        elif self.mesh:
            diffr.oscilScanMesh(
                start,
                end,
                exptime,
                self._detector.get_deadtime(),
                self.mesh_num_lines,
                self.mesh_total_nb_frames,
                self.mesh_center,
                self.mesh_range,
                wait=True,
            )
        else:
            diffr.oscilScan(start, end, exptime, wait=True)

    def prepare_acquisition(
        self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""
    ):
        energy = self._tunable_bl.get_current_energy()
        return self._detector.prepare_acquisition(
            take_dark,
            start,
            osc_range,
            exptime,
            npass,
            number_of_images,
            comment,
            energy,
            self.mesh,
        )

    def open_fast_shutter(self):
        self.getObjectByRole("fastshut").actuatorIn()

    def close_fast_shutter(self):
        self.getObjectByRole("fastshut").actuatorOut()

    def stop_oscillation(self):
        pass

    @task
    def data_collection_cleanup(self):
        self.getObjectByRole("diffractometer")._wait_ready(10)
        state = self.getObjectByRole("fastshut").getActuatorState(read=True)
        if state != "out":
            self.close_fast_shutter()

    def set_helical(self, helical_on):
        self.helical = helical_on

    def set_helical_pos(self, helical_oscil_pos):
        self.helical_pos = helical_oscil_pos

    def get_cryo_temperature(self):
        return 0

    @task
    def set_detector_filenames(
        self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
    ):
        self.last_image_filename = filename
        return ESRFMultiCollect.set_detector_filenames(
            self,
            frame_number,
            start,
            filename,
            jpeg_full_path,
            jpeg_thumbnail_full_path,
        )

    def adxv_notify(self, image_filename):
        logging.info("adxv_notify %r", image_filename)
        try:
            adxv_notify_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            adxv_notify_socket.connect(("aelita.esrf.fr", 8100))
            adxv_notify_socket.sendall("load_image %s\n" % image_filename)
            adxv_notify_socket.close()
        except BaseException:
            pass
        else:
            gevent.sleep(3)

    def albula_notify(self, image_filename):
        try:
            albula_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            albula_socket.connect(("localhost", 31337))
        except BaseException:
            pass
        else:
            albula_socket.sendall(
                pickle.dumps({"type": "newimage", "path": image_filename})
            )

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
