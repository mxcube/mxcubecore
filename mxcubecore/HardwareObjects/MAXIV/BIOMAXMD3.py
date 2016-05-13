"""
BIOMAXMinidiff (MD3)
"""
import os
import time
import logging
import gevent
import lucid2 as lucid
import numpy as np
from PIL import Image
#import lucid
import tempfile
import io

from GenericDiffractometer import GenericDiffractometer

class BIOMAXMD3(GenericDiffractometer):

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


        self.phi_motor_hwobj = self.getObjectByRole('phi')
        self.phiz_motor_hwobj = self.getObjectByRole('phiz')
        self.phiy_motor_hwobj = self.getObjectByRole('phiy')
        self.zoom_motor_hwobj = self.getObjectByRole('zoom')
        self.focus_motor_hwobj = self.getObjectByRole('focus')
        self.sample_x_motor_hwobj = self.getObjectByRole('sampx')
        self.sample_y_motor_hwobj = self.getObjectByRole('sampy')


    def start3ClickCentring(self):
        self.start_centring_method(self.CENTRING_METHOD_MANUAL)

    def startAutoCentring(self):
        self.start_centring_method(self.CENTRING_METHOD_AUTO)

    def get_pixels_per_mm(self):
        """
        Get the values from coaxCamScaleX and coaxCamScaleY channels diretly

        :returns: list with two floats
        """
        return (1/self.channel_dict["CoaxCamScaleX"].getValue(), 1/self.channel_dict["CoaxCamScaleY"].getValue())

    def manual_centring(self):
        """
        Descript. :
        """
        self.centring_hwobj.initCentringProcedure()
        for click in range(3):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
	    print "click ", x, y
            self.centring_hwobj.appendCentringDataPoint(
                 {"X": (x - self.beam_position[0])/ self.pixels_per_mm_x,
                  "Y": (y - self.beam_position[1])/ self.pixels_per_mm_y})
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

    def automatic_centring(self):
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
                    {"X": (x - self.beam_position[0])/ self.pixels_per_mm_x,
                     "Y": (y - self.beam_position[1])/ self.pixels_per_mm_y})
            surface_score_list.append(score)
            self.phi_motor_hwobj.moveRelative(\
                 360.0 / BIOMAXMD3.AUTOMATIC_CENTRING_IMAGES)
	    #gevent.sleep(2)
            self.wait_device_ready(5)
        self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)

    def find_loop(self):
        """
        Description:
        """
        imgStr=self.camera.get_snapshot_img_str()
        image = Image.open(io.BytesIO(imgStr)).rotate(90)
        try:
            img = np.array(image)
            info, y, x = lucid.find_loop(img,IterationClosing=6)
            x = self.camera.getWidth() - x
        except:
            return -2,-2, 0
        if info == "Coord":
            surface_score = 10
            print "x %s y %s and phi %s self.pixels_per_mm_x %s" % (x,y,self.phi_motor_hwobj.getPosition(),self.pixels_per_mm_x)
            return x, y, surface_score
        else:
            return  -2,-2, 0

    def omega_reference_add_constraint(self):
        """
        Descript. :
        """
        if self.omega_reference_par is None or self.beam_position is None: 
            return
        if self.omega_reference_par["camera_axis"].lower() == "x":
            on_beam = (self.beam_position[0] -  self.zoom_centre['x']) * \
                      self.omega_reference_par["direction"] / self.pixels_per_mm_x + \
                      self.omega_reference_par["position"]
        else:
            on_beam = (self.beam_position[1] -  self.zoom_centre['y']) * \
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
            kappa = self.current_motor_positions["kappa"] 
            phi = self.current_motor_positions["kappa_phi"] 

#        if (c['kappa'], c['kappa_phi']) != (kappa, phi) \
#         and self.minikappa_correction_hwobj is not None:
#            c['sampx'], c['sampy'], c['phiy'] = self.minikappa_correction_hwobj.shift(
#            c['kappa'], c['kappa_phi'], [c['sampx'], c['sampy'], c['phiy']], kappa, phi)
        xy = self.centring_hwobj.centringToScreen(c)
        x = (xy['X'] + c['beam_x']) * self.pixels_per_mm_x + \
              self.zoom_centre['x']
        y = (xy['Y'] + c['beam_y']) * self.pixels_per_mm_y + \
             self.zoom_centre['y']
        return x, y

