# -*- coding: utf-8 -*-
"""
[Name] DetectorBeamCenter

[Description]
Calculates the beam center at the detector position

Needs signals from following channels

   Detector distance
   Wavelength
   BeamCenter X (at the OAV)
   BeamCenter Y (at the OAV)

        self.distance_motor = PyTango.DeviceProxy('i11-ma-cx1/dt/dtc_ccd.1-mt_ts')
        self.wavelength_motor = PyTango.DeviceProxy('i11-ma-c03/op/mono1')
        self.det_mt_tx = PyTango.DeviceProxy('i11-ma-cx1/dt/dtc_ccd.1-mt_tx') #.read_attribute('position').value - 30.0
        self.det_mt_tz = PyTango.DeviceProxy('i11-ma-cx1/dt/dtc_ccd.1-mt_tz') #.read_attribute('position').value + 14.3
 

[Emited signals]

detectorBeamCenterChanged

[Included Hardware Objects]

[Example XML file]

<device class = "DetectorBeamCenter">
  <username>DetecterBeamCenter</username>

  <object role="detector" href="eiger" />

  <channel name="detector_distance" type="tango" tangoname="i11-ma-cx1/dt/dtc_ccd.1-mt_ts" polling="1000">position</channel>
  <channel name="wavelength" type="tango" tangoname="i11-ma-c03/op/mono1" polling="1000">lambda</channel>
  <channel name="table_x" type="tango" tangoname="i11-ma-cx1/dt/dtc_ccd.1-mt_tx" polling="1000">position</channel>
  <channel name="table_z" type="tango" tangoname="i11-ma-cx1/dt/dtc_ccd.1-mt_tz" polling="1000">position</channel>

  <theta_x>1.65113065e+03, 5.63662370e+00,  3.49706731e-03, 9.77188997e+00</theta_x>
  <theta_y>1.54776707e+03, 3.65108709e-01, -1.12769165e-01, 9.74625808e+00</theta_y>

</device>


"""

import logging
import numpy as np

from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Equipment

class PX2DetectorBeamCenter(Equipment):

    def __init__(self, *args):

        self.current_detdist = None
        self.current_wavelength = None
        self.current_table_x = None
        self.current_table_z = None

        Equipment.__init__(self, *args)

        # Channels
        self.detdist_chan = None
        self.wavelength_chan = None
        self.table_x_chan  = None
        self.table_z_chan  = None

    def init(self):

        self.det_hwobj = self.getObjectByRole('detector')
        if self.det_hwobj is None:
             self.pixel_size_x, self.pixel_size_y = (75e-6, 75e-6)
        else:
             self.pixel_size_x, self.pixel_size_y = self.det_hwobj.get_pixel_size()

        self.detdist_chan = self.getChannelObject('detector_distance')
        self.wavelength_chan = self.getChannelObject('wavelength')
        self.table_x_chan = self.getChannelObject('table_x')
        self.table_z_chan = self.getChannelObject('table_z')

        # values and offsets for calculation
        self._theta_x_vals = self.getProperty("theta_x")
        self._theta_y_vals = self.getProperty("theta_y")

        _x_offset = self.getProperty("x_offset")
        if _x_offset is not None:  
              self._x_offset = float(_x_offset)
        else:
              self._x_offset = 0

        _y_offset = self.getProperty("y_offset")
        if _y_offset is not None:  
              self._y_offset = float(_y_offset)
        else:
              self._y_offset = 0

        _table_x_offset = self.getProperty("table_x_offset")
        if _table_x_offset is not None:  
              self._table_x_offset = float(_table_x_offset)
        else:
              self._table_x_offset = 0

        _table_z_offset = self.getProperty("table_z_offset")
        if _table_z_offset is not None:  
              self._table_z_offset = float(_table_z_offset)
        else:
              self._table_z_offset = 0

        if None not in [ self.detdist_chan, self.wavelength_chan, \
                         self.table_x_chan, self.table_z_chan, \
                         self._theta_x_vals, self._theta_y_vals ]:

            self.detdist_chan.connectSignal('update', self.detdist_changed)
            self.wavelength_chan.connectSignal('update', self.wavelength_changed)
            self.table_x_chan.connectSignal('update', self.table_x_changed)
            self.table_z_chan.connectSignal('update', self.table_z_changed)
    

            self.theta_x_matrix = np.matrix(eval(self._theta_x_vals))
            self.theta_y_matrix = np.matrix(eval(self._theta_y_vals))
        else:
            logging.getLogger("HWR").error("Incomplete configuration for DetectorBeamDistance. \
                        Invalid data may be included with your data. Please check your configuration")

    def detdist_changed(self, value):
        self.current_detdist = value
        self.info_updated() 

    def wavelength_changed(self, value):
        self.current_wavelength = value
        self.info_updated() 

    def table_x_changed(self, value):
        self.current_table_x = value
        self.info_updated() 

    def table_z_changed(self, value):
        self.current_table_z = value
        self.info_updated() 

    def info_updated(self):
        if None not in [self.current_detdist, self.current_wavelength, \
                        self.current_table_x, self.current_table_z, \
                        self._theta_x_vals, self._theta_y_vals ]:
             self.center_x, self.center_y = self.calculate_center() 
             self.emit("detectorBeamCentreChanged", [self.center_x, self.center_y])
                
    def _update(self):
        self.current_detdist = self.detdist_chan.getValue()
        self.current_wavelength = self.wavelength_chan.getValue()
        self.current_table_x = self.table_x_chan.getValue()
        self.current_table_z = self.table_z_chan.getValue()

        self.info_updated()

    def get_beam_center(self):
        self._update()
        return self.center_x, self.center_y

    def calculate_center(self):
        px_x = self.pixel_size_x * 1000
        px_y = self.pixel_size_y * 1000
   
        table_x_offset = self._table_x_offset
        table_z_offset = self._table_z_offset

        x_offset = self._x_offset
        y_offset = self._y_offset

        # roi_mode = self.det_hwobj.get_roi_mode()
        roi_mode = "4M"
        roi_mode = ""

        wavelength = self.current_wavelength
        distance   = self.current_detdist
        table_x = self.current_table_x
        table_z = self.current_table_z

        tx         = table_x + table_x_offset
        tz         = table_z + table_z_offset

        theta_x = self.theta_x_matrix
        theta_y = self.theta_y_matrix

        X = np.matrix([1., wavelength, distance, 0, 0 ]) 

        X_x = X[:,[0,1,2,3]]
        X_y = X[:,[0,1,2,4]]

        cent_x = float( X_x * theta_x.T )
        cent_y = float( X_y * theta_y.T )


        if roi_mode == '4M':
            cent_y -= 550

        cent_x += tx / px_x + x_offset
        cent_y += tz / px_y + y_offset

        return cent_x, cent_y

def print_me(det):
    det._update()

    print "\nOffsets:"

    print "         X:  ", det._x_offset
    print "         Y:  ", det._y_offset
    print "  Table  X:  ", det._table_x_offset
    print "  Table  Z:  ", det._table_z_offset

    print "\nCurrent values: "
    print "    Detector Distance: ", det.current_detdist
    print "           Wavelength: ", det.current_wavelength
    print "              Table X: ", det.current_table_x
    print "              Table Z: ", det.current_table_z
    print "           Pixel size: ", det.pixel_size_x, det.pixel_size_y

    print "\nCenter:"
    print "         X:  ", det.center_x
    print "         y:  ", det.center_y


def test():
    import os
    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    detcen = hwr.getHardwareObject("/detector_beamcenter")
    print_me(detcen)
    

if __name__ == '__main__':
   test()

