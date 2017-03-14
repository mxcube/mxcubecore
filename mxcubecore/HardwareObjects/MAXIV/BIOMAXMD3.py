"""

BIOMAXMinidiff (MD3)

"""

import time
import logging
import gevent
import lucid2 as lucid
import numpy as np
from PIL import Image
# import lucid
import io
import math

from GenericDiffractometer import *


class BIOMAXMD3(GenericDiffractometer):

    MOTOR_TO_EXPORTER_NAME = {"focus": "AlignmentX",
                              "kappa": "Kappa",
                              "kappa_phi": "Phi",
                              "phi": "Omega",
                              "phiy": "AlignmentY",
                              "phiz": "AlignmentZ",
                              "sampx": "CentringX",
                              "sampy": "CentringY",
                              "zoom": "Zoom"
                              }

    AUTOMATIC_CENTRING_IMAGES = 6

    def __init__(self, *args):
        """
        Description:
        """
        GenericDiffractometer.__init__(self, *args)

    def init(self):

        GenericDiffractometer.init(self)

        self.front_light = self.getObjectByRole('frontlight')
        self.back_light = self.getObjectByRole('backlight')
        self.back_light_switch = self.getObjectByRole('backlightswitch')
        self.front_light_switch = self.getObjectByRole('frontlightswitch')

        self.centring_hwobj = self.getObjectByRole('centring')
        if self.centring_hwobj is None:
            logging.getLogger("HWR").debug('EMBLMinidiff: Centring math is not defined')

        # to make it comaptible
        self.camera = self.camera_hwobj
        self.acceptCentring = self.accept_centring

        self.phi_motor_hwobj = self.motor_hwobj_dict['phi']
        self.phiz_motor_hwobj = self.motor_hwobj_dict['phiz']
        self.phiy_motor_hwobj = self.motor_hwobj_dict['phiy']
        self.zoom_motor_hwobj = self.motor_hwobj_dict['zoom']
        self.focus_motor_hwobj = self.motor_hwobj_dict['focus']
        self.sample_x_motor_hwobj = self.motor_hwobj_dict['sampx']
        self.sample_y_motor_hwobj = self.motor_hwobj_dict['sampy']

        self.cent_vertical_pseudo_motor = None
        try:
            self.cent_vertical_pseudo_motor = self.addChannel({"type": "exporter",
                                                               "name": "CentringTableVerticalPositionPosition"
                                                               },
                                                              "CentringTableVerticalPosition"
                                                              )
            if self.cent_vertical_pseudo_motor is not None:
                self.connect(self.cent_vertcial_pseudo_motor, "update",
                             self.centring_motor_moved)
        except:
            logging.getLogger("HWR").warning('Cannot initialize CentringTableVerticalPosition')

        try:
            use_sc = self.getProperty("use_sc")
            self.set_use_sc(use_sc)
        except:
                logging.getLogger("HWR").debug('Cannot set sc mode, use_sc: ', str(use_sc))

        try:
            self.zoom_centre = eval(self.getProperty("zoom_centre"))
            if self.camera.zoom is not None:
                self.zoom_centre['x'] = self.zoom_centre['x'] * self.camera.zoom
                self.zoom_centre['y'] = self.zoom_centre['y'] * self.camera.zoom
            self.beam_position = [self.zoom_centre['x'], self.zoom_centre['y']]
        except:
            if self.image_width is not None and self.image_height is not None:
                self.zoom_centre = {'x': self.image_width / 2, 'y': self.image_height / 2}
                self.beam_position = [self.image_width / 2, self.image_height / 2]
                logging.getLogger("HWR").warning("Diffractometer: Zoom center is ' +\
                       'not defined. Continuing with the middle: %s" % self.zoom_centre)
            else:
                logging.getLogger("HWR").warning("Diffractometer: Neither zoom centre nor camera size are defined")

    def start3ClickCentring(self):
        self.start_centring_method(self.CENTRING_METHOD_MANUAL)

    def startAutoCentring(self):
        self.start_centring_method(self.CENTRING_METHOD_AUTO)

    def get_pixels_per_mm(self):
        """
        Get the values from coaxCamScaleX and coaxCamScaleY channels diretly

        :returns: list with two floats
        """
        return (0.5/self.channel_dict["CoaxCamScaleX"].getValue(), 0.5/self.channel_dict["CoaxCamScaleY"].getValue())
        return (1/self.channel_dict["CoaxCamScaleX"].getValue(), 1/self.channel_dict["CoaxCamScaleY"].getValue())

    def update_zoom_calibration(self):
        """
        """
        self.pixels_per_mm_x = 0.5/self.channel_dict["CoaxCamScaleX"].getValue()
        self.pixels_per_mm_y = 0.5/self.channel_dict["CoaxCamScaleY"].getValue()

    def manual_centring(self):
        """
        Descript. :
        """
        self.centring_hwobj.initCentringProcedure()
        for click in range(3):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            self.centring_hwobj.appendCentringDataPoint(
                 {"X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                  "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y})
            if self.in_plate_mode():
                dynamic_limits = self.phi_motor_hwobj.getDynamicLimits()
                if click == 0:
                    self.phi_motor_hwobj.move(dynamic_limits[0])
                elif click == 1:
                    self.phi_motor_hwobj.move(dynamic_limits[1])
            else:
                if click < 2:
                    self.phi_motor_hwobj.moveRelative(90)
        self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)

    def automatic_centring_old(self):
        """Automatic centring procedure. Rotates n times and executes
           centring algorithm. Optimal scan position is detected.
        """

        surface_score_list = []
        self.zoom_motor_hwobj.moveToPosition("Zoom 1")
        self.wait_device_ready(3)
        self.centring_hwobj.initCentringProcedure()
        for image in range(BIOMAXMD3.AUTOMATIC_CENTRING_IMAGES):
            x, y, score = self.find_loop()
            if x > -1 and y > -1:
                self.centring_hwobj.appendCentringDataPoint(
                    {"X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                     "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y})
            surface_score_list.append(score)
            self.phi_motor_hwobj.moveRelative(360.0 / BIOMAXMD3.AUTOMATIC_CENTRING_IMAGES)
            self.wait_device_ready(5)
        self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)

    def automatic_centring(self):
        """Automatic centring procedure. Rotates n times and executes
           centring algorithm. Optimal scan position is detected.
        """

        # check if loop is there at the beginning
        i = 0
        while -1 in self.find_loop():
            self.phi_motor_hwobj.moveRelative(90)
            self.wait_device_ready(5)
            i += 1
            if i > 4:
                self.emit_progress_message("No loop detected, aborting")
                return

        for k in range(3):
            self.emit_progress_message("Doing automatic centring")
            surface_score_list = []
            self.centring_hwobj.initCentringProcedure()
            for a in range(3):
                x, y, score = self.find_loop()
                logging.info("in autocentre, x=%f, y=%f", x, y)
                if x < 0 or y < 0:
                    for i in range(1, 9):
                        # logging.info("loop not found - moving back %d" % i)
                        self.phi_motor_hwobj.moveRelative(10)
                        self.wait_device_ready(5)
                        x, y, score = self.find_loop()
                        surface_score_list.append(score)
                        if -1 in (x, y):
                            continue
                        if y >= 0:
                            if x < self.camera.getWidth()/2:
                                x = 0
                                self.centring_hwobj.appendCentringDataPoint(
                                    {"X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                                     "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y})
                                break
                            else:
                                x = self.camera.getWidth()
                                self.centring_hwobj.appendCentringDataPoint(
                                    {"X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                                     "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y})
                                break
                    if -1 in (x, y):
                        raise RuntimeError("Could not centre sample automatically.")
                    self.phi_motor_hwobj.moveRelative(-i*10)
                    self.wait_device_ready(5)
                else:
                    self.centring_hwobj.appendCentringDataPoint(
                        {"X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                         "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y})
                self.phi_motor_hwobj.moveRelative(90)
                self.wait_device_ready(5)

            self.omega_reference_add_constraint()
            centred_pos = self.centring_hwobj.centeredPosition(return_by_name=False)
            if k < 2:
                self.move_to_centred_position(centred_pos)
                self.wait_device_ready(5)
        return centred_pos

    def find_loop(self):
        """
        Description:
        """
        imgStr = self.camera.get_snapshot_img_str()
        image = Image.open(io.BytesIO(imgStr))
        try:
            img = np.array(image)
            img_rot = np.rot90(img, 1)
            info, y, x = lucid.find_loop(np.array(img_rot, order='C'), IterationClosing=6)
            x = self.camera.getWidth() - x
        except:
            return -1, -1, 0
        if info == "Coord":
            surface_score = 10
            return x, y, surface_score
        else:
            return -1, -1, 0

    def omega_reference_add_constraint(self):
        """
        Descript. :
        """
        if self.omega_reference_par is None or self.beam_position is None:
            return
        if self.omega_reference_par["camera_axis"].lower() == "x":
            on_beam = (self.beam_position[0] - self.zoom_centre['x']) * \
                      self.omega_reference_par["direction"] / self.pixels_per_mm_x + \
                      self.omega_reference_par["position"]
        else:
            on_beam = (self.beam_position[1] - self.zoom_centre['y']) * \
                      self.omega_reference_par["direction"] / self.pixels_per_mm_y + \
                      self.omega_reference_par["position"]
        self.centring_hwobj.appendMotorConstraint(self.omega_reference_motor, on_beam)

    def omega_reference_motor_moved(self, pos):
        """
        Descript. :
        """
        if self.omega_reference_par["camera_axis"].lower() == "x":
            pos = self.omega_reference_par["direction"] * \
                  (pos - self.omega_reference_par["position"]) * \
                  self.pixels_per_mm_x + self.zoom_centre['x']
            self.reference_pos = (pos, -10)
        else:
            pos = self.omega_reference_par["direction"] * \
                  (pos - self.omega_reference_par["position"]) * \
                  self.pixels_per_mm_y + self.zoom_centre['y']
            self.reference_pos = (-10, pos)
        self.emit('omegaReferenceChanged', (self.reference_pos,))

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        c = centred_positions_dict

        if self.head_type == GenericDiffractometer.HEAD_TYPE_MINIKAPPA:
            kappa = self.motor_hwobj_dict["kappa"]
            phi = self.motor_hwobj_dict["kappa_phi"]

#        if (c['kappa'], c['kappa_phi']) != (kappa, phi) \
#         and self.minikappa_correction_hwobj is not None:
#            c['sampx'], c['sampy'], c['phiy'] = self.minikappa_correction_hwobj.shift(
#            c['kappa'], c['kappa_phi'], [c['sampx'], c['sampy'], c['phiy']], kappa, phi)
        xy = self.centring_hwobj.centringToScreen(c)
        # x = (xy['X'] + c['beam_x']) * self.pixels_per_mm_x + \
        x = xy['X'] * self.pixels_per_mm_x + \
            self.zoom_centre['x']
        # y = (xy['Y'] + c['beam_y']) * self.pixels_per_mm_y + \
        y = xy['Y'] * self.pixels_per_mm_y + \
            self.zoom_centre['y']
        return x, y

    def osc_scan(self, start, end, exptime, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end-start) / exptime
            # todo, JN, get scan_speed limit
            """
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)
            """
        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1" % (start, (end-start), exptime)
        scan = self.command_dict["startScanEx"]
        logging.getLogger("HWR").info("[BIOMAXMND3] MD3 oscillation requested, waiting device ready..., params "+str(scan_params))
        self.wait_device_ready(200)
        logging.getLogger("HWR").info("[BIOMAXMND3] MD3 oscillation requested, device ready.")
        scan(scan_params)
        logging.getLogger("HWR").info("[BIOMAXMND3] MD3 oscillation launched, waiting for device ready.")
        #if wait:
        time.sleep(0.1)	
        self.wait_device_ready(exptime+30)  # timeout of 5 min
        logging.getLogger("HWR").info("[BIOMAXMND3] MD3 oscillation, device ready.")

    def osc_scan_4d(self, start, end, exptime, helical_pos, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end-start) / exptime
            # todo, JN, get scan_speed limit
            """
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)
            """
        scan_params = "%0.3f\t%0.3f\t%0.4f\t" % (start, (end-start), exptime)
        scan_params += "%0.3f\t" % helical_pos['1']['phiy']
        scan_params += "%0.3f\t" % helical_pos['1']['phiz']
        scan_params += "%0.3f\t" % helical_pos['1']['sampx']
        scan_params += "%0.3f\t" % helical_pos['1']['sampy']
        scan_params += "%0.3f\t" % helical_pos['2']['phiy']
        scan_params += "%0.3f\t" % helical_pos['2']['phiz']
        scan_params += "%0.3f\t" % helical_pos['2']['sampx']
        scan_params += "%0.3f\t" % helical_pos['2']['sampy']

        logging.getLogger("HWR").info("[BIOMAXMND3] MD3 helical oscillation requested, waiting device ready..., params "+str(scan_params))
        scan = self.command_dict["startScan4DEx"]
        time.sleep(0.1)	
        self.wait_device_ready(200)
        logging.getLogger("HWR").info("[BIOMAXMND3] MD3 helical oscillation requested, device ready.")
        scan(scan_params)
        if wait:
            self.wait_device_ready(900)  # timeout of 5 min

    def set_phase(self, phase, wait=False, timeout=None):
        if self.is_ready():
            print "current state is", self.current_state
            self.command_dict["startSetPhase"](phase)
            if wait:
                if not timeout:
                    timeout = 40
                self.wait_device_ready(timeout)
        else:
            print "moveToPhase - Ready is: ", self.is_ready()

    # def move_sync_motors(self, motors_dict, wait=False, timeout=None):
    def move_sync_motors(self, motors_dict, wait=True, timeout=30):
        argin = ""
        logging.getLogger("HWR").debug("BIOMAXMD3: in move_sync_motors, wait: %s, motors: %s, tims: %s " %(wait, motors_dict, time.time()))
        for motor in motors_dict.keys():
            position = motors_dict[motor]
            if position is None:
                continue
            name = self.MOTOR_TO_EXPORTER_NAME[motor]
            argin += "%s=%0.3f;" % (name, position)
        if not argin:
            return
        self.wait_device_ready(2000)
        self.command_dict["startSimultaneousMoveMotors"](argin)
    # task_info = self.command_dict["getTaskInfo"](task_id)
        if wait:
            self.wait_device_ready(timeout)

    def moveToBeam(self, x, y):
        try:
            self.emit_progress_message("Move to beam...")
            self.centring_time = time.time()
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centring_status = {"valid": True,
                                    "startTime": curr_time,
                                    "endTime": curr_time}

            self.beam_position = self.beam_info_hwobj.get_beam_position()
            beam_xc = self.beam_position[0]
            beam_yc = self.beam_position[1]
            cent_vertical_to_move = self.cent_vertical_pseudo_motor.getValue()-(x-beam_xc)/float(self.pixelsPerMmY)
            self.emit_progress_message("")

            motors = {}
            motors["sampx"] = self.sample_x_motor_hwobj.getPosition()
            motors["sampy"] = self.sample_y_motor_hwobj.getPosition()
            motors["phiy"] = self.phiy_motor_hwobj.getPosition()
            motors["phiz"] = self.phiz_motor_hwobj.getPosition()
            print "positions before ", motors

            self.phiy_motor_hwobj.moveRelative(-1*(y-beam_yc)/float(self.pixelsPerMmZ))
            self.cent_vertical_pseudo_motor.setValue(cent_vertical_to_move)
            self.wait_device_ready(5)

            # motors = {}
            motors["sampx"] = self.sample_x_motor_hwobj.getPosition()
            motors["sampy"] = self.sample_y_motor_hwobj.getPosition()
            motors["phiy"] = self.phiy_motor_hwobj.getPosition()
            motors["phiz"] = self.phiz_motor_hwobj.getPosition()
            print "positions after ", motors

            self.centring_status["motors"] = motors
            self.centring_status["valid"] = True
            self.centring_status["angleLimit"] = True
            self.centring_status["accepted"] = True

            self.emit('centringAccepted', (True, self.get_centring_status()))
            self.emit('centringSuccessful', (self.CENTRING_METHOD_MOVE_TO_BEAM, self.get_centring_status()))
            self.emit_progress_message("")
            self.ready_event.set()
            self.current_centring_method = None
            self.current_centring_procedure = None
        except:
            logging.getLogger("HWR").exception("MiniDiff: could not center to beam, aborting")

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """
        self.centring_hwobj.initCentringProcedure()
        self.centring_hwobj.appendCentringDataPoint({
                   "X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                   "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y})
        self.omega_reference_add_constraint()
        pos = self.centring_hwobj.centeredPosition()
        if return_by_names:
            pos = self.convert_from_obj_to_name(pos)
        return pos

    def abort(self):
        """
        Stops all the pending tasks, stops all the motors and closes all theirs control loop.
        """
        logging.getLogger("HWR").exception("MiniDiff: going to abort")
        self.command_dict["abort"]()
        logging.getLogger("HWR").exception("MiniDiff: all movements aborted")

