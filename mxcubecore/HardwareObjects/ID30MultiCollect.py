from ESRFMultiCollect import *
from detectors.LimaPilatus import Pilatus
import gevent

class ID30MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, PixelDetector(Pilatus), FixedEnergy(0.965, 12.8))

    ### TEMPORARY DEACTIVATE XTAL SNAPSHOTS
    @task
    def take_crystal_snapshots(self):
        return
    ###
  
    @task
    def move_detector(self, detector_distance):
        pass #self.bl_control.resolution.newDistance(detector_distance)

    @task
    def set_resolution(self, new_resolution):
        pass #self.bl_control.resolution.move(new_resolution)

    def get_detector_distance(self):
        return 260 #self.bl_control.resolution.res2dist(self.bl_control.resolution.getPosition())

    @task
    def do_prepare_oscillation(self, *args, **kwargs):
        return

    @task
    def oscil(self, start, end, exptime, npass):
        save_diagnostic = False
        operate_shutter = True
        self.getObjectByRole("diffractometer").oscil(start, end, exptime, npass, save_diagnostic, operate_shutter)

    def open_fast_shutter(self):
        self.getObjectByRole("diffractometer").controller.fshut.open()

    def close_fast_shutter(self):
        self.getObjectByRole("diffractometer").controller.fshut.close()

    def set_helical(self, helical_on):
        return

    def set_helical_pos(self, helical_oscil_pos):
        return

    def get_flux(self):
        return -1

    def set_transmission(self, transmission_percent):
    	pass

    def get_transmission(self):
        return 100

    def get_cryo_temperature(self):
        return 0

    @task
    def prepare_intensity_monitors(self):
        return

    def get_beam_centre(self):
        return (159.063, 163.695)


