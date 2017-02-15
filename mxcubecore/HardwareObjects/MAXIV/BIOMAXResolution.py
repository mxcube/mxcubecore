import logging
from HardwareRepository import HardwareRepository
import Resolution
#import gevent
#import time
#import copy
class BIOMAXResolution(Resolution.Resolution):
    def __init__(self, *args, **kwargs):
        Resolution.Resolution.__init__(self, *args, **kwargs)

    def init(self): 
        #Resolution.Resolution.init(self)
        self.currentResolution = None
        self.energy = None

        self.dtox = self.getObjectByRole("dtox")
        self.energy = self.getObjectByRole("energy")
        self.detector = self.getObjectByRole("detector")
        
        if self.detector:
            self.det_width = self.detector.get_x_pixels_in_detector()
            self.det_height = self.detector.get_y_pixels_in_detector()
        else:
            self.valid = False
            logging.getLogger().exception('Cannot get detector size')
            raise AttributeError("Cannot get detector ")

        #self.connect(self.detector, "roiChanged", self.det_roi_changed)
        self.connect(self.dtox, "stateChanged", self.dtoxStateChanged)
        self.connect(self.dtox, "positionChanged", self.dtoxPositionChanged)
        self.connect(self.energy, "valueChanged", self.energyChanged)
        self.connect(self.detector, "roiChanged", self.det_roi_changed)
        

    def det_roi_changed(self):
        self.det_width = self.detector.get_x_pixels_in_detector()
        self.det_height = self.detector.get_y_pixels_in_detector()
        print 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxrecalculate resolution'
        self.recalculateResolution()

    def update_beam_centre(self, dtox):
        beam_x, beam_y = self.get_beam_centre(dtox)
        self.det_radius =  min(self.det_width - beam_x, self.det_height - beam_y, beam_x, beam_y)*0.075

