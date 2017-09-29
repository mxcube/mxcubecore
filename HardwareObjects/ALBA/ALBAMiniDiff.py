#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name]
ALBAMiniDiff

[Description]
Specific HwObj for M2D2 diffractometer @ ALBA

[Channels]
- N/A

[Commands]
- N/A

[Emited signals]
- pixelsPerMmChanged
- phiMotorMoved
- stateChanged
- zoomMotorPredefinedPositionChanged
 

[Functions]
- None

[Included Hardware Objects]
- None
"""

import logging, time, math, numpy
from GenericDiffractometer import GenericDiffractometer
from gevent.event import AsyncResult
import gevent
import PyTango


__author__ = "Jordi Andreu"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Jordi Andreu"
__email__ = "jandreu[at]cells.es"
__status__ = "Draft"


class ALBAMiniDiff(GenericDiffractometer):

    def __init__(self, *args):
        GenericDiffractometer.__init__(self, *args)
        self.centring_hwobj = None
        
    def init(self):
        self.calibration = self.getObjectByRole("calibration")
        self.centring_hwobj = self.getObjectByRole('centring')
        if self.centring_hwobj is None:
            logging.getLogger("HWR").debug('ALBAMinidiff: Centring math is not defined')

        self.cmd_start_auto_focus = self.getCommandObject('startAutoFocus')

        self.phi_motor_hwobj = self.getObjectByRole('phi')
        self.phiz_motor_hwobj = self.getObjectByRole('phiz')
        self.phiy_motor_hwobj = self.getObjectByRole('phiy')
        self.zoom_motor_hwobj = self.getObjectByRole('zoom')
        self.focus_motor_hwobj = self.getObjectByRole('focus')
        self.sample_x_motor_hwobj = self.getObjectByRole('sampx')
        self.sample_y_motor_hwobj = self.getObjectByRole('sampy')

        if self.phi_motor_hwobj is not None:
            self.connect(self.phi_motor_hwobj, 'stateChanged', self.phi_motor_state_changed)
            self.connect(self.phi_motor_hwobj, "positionChanged", self.phi_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Phi motor is not defined')

        if self.phiz_motor_hwobj is not None:
            self.connect(self.phiz_motor_hwobj, 'stateChanged', self.phiz_motor_state_changed)
            self.connect(self.phiz_motor_hwobj, 'positionChanged', self.phiz_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Phiz motor is not defined')

        if self.phiy_motor_hwobj is not None:
            self.connect(self.phiy_motor_hwobj, 'stateChanged', self.phiy_motor_state_changed)
            self.connect(self.phiy_motor_hwobj, 'positionChanged', self.phiy_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Phiy motor is not defined')

        if self.zoom_motor_hwobj is not None:
            self.connect(self.zoom_motor_hwobj, 'positionChanged', self.zoom_position_changed)
            self.connect(self.zoom_motor_hwobj, 'predefinedPositionChanged', self.zoom_motor_predefined_position_changed)
            self.connect(self.zoom_motor_hwobj, 'stateChanged', self.zoom_motor_state_changed)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Zoom motor is not defined')

        if self.sample_x_motor_hwobj is not None:
            self.connect(self.sample_x_motor_hwobj, 'stateChanged', self.sampleX_motor_state_changed)
            self.connect(self.sample_x_motor_hwobj, 'positionChanged', self.sampleX_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Sampx motor is not defined')

        if self.sample_y_motor_hwobj is not None:
            self.connect(self.sample_y_motor_hwobj, 'stateChanged', self.sampleY_motor_state_changed)
            self.connect(self.sample_y_motor_hwobj, 'positionChanged', self.sampleY_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Sampx motor is not defined')

        if self.focus_motor_hwobj is not None:
            self.connect(self.focus_motor_hwobj, 'positionChanged', self.focus_motor_moved)

        GenericDiffractometer.init(self)

    def getCalibrationData(self, offset=None):
        calibx, caliby = self.calibration.getCalibration()
        return 1000.0/caliby, 1000.0/caliby 
        # return 1000./self.md2.CoaxCamScaleX, 1000./self.md2.CoaxCamScaleY

    def get_pixels_per_mm(self):
        px_x, px_y = self.getCalibrationData()
        return (px_x,px_y)
            

    def update_pixels_per_mm(self, *args):
        """
        Descript. :
        """
        self.pixels_per_mm_x,  self.pixels_per_mm_y = self.getCalibrationData()
        self.emit('pixelsPerMmChanged', ((self.pixels_per_mm_x, self.pixels_per_mm_y), ))

    def get_centred_point_from_coord(self, x,y, return_by_names=None):
        """
        """
        return {'omega': [200,200]}
        #raise NotImplementedError

    def getBeamInfo(self, update_beam_callback):
        calibx, caliby = self.calibration.getCalibration()

        size_x = self.getChannelObject("beamInfoX").getValue() / 1000.0
        size_y = self.getChannelObject("beamInfoY").getValue() / 1000.0

        data = {
           "size_x":  size_x,
           "size_y":  size_y,
           "shape":   "ellipse",
        }

        update_beam_callback(data)

    def use_sample_changer(self):
        return True

    def in_plate_mode(self):
        return False

    def manual_centring(self):
        """
        Descript. :
        """
        self.centring_hwobj.initCentringProcedure()

        # self.head_type = self.chan_head_type.getValue()

        for click in range(3):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
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
                    self.phi_motor_hwobj.moveRelative(-90)
        #self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)


    def phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["phi"] = pos
        self.emit_diffractometer_moved() 
        self.emit("phiMotorMoved", pos)
        #self.emit('stateChanged', (self.current_motor_states["phi"], ))

    def phi_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_motor_states["phi"] = state
        self.emit('stateChanged', (state, ))

    def phiz_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["phiz"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def phiz_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit('stateChanged', (state, ))

    def phiy_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit('stateChanged', (state, ))

    def phiy_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["phiy"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def zoom_position_changed(self, value):
        self.update_pixels_per_mm()
        self.current_motor_positions["zoom"] = value
        self.refresh_omega_reference_position()

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        """
        Descript. :
        """
        self.update_pixels_per_mm()
        self.emit('zoomMotorPredefinedPositionChanged',
               (position_name, offset, ))

    def zoom_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit('stateChanged', (state, ))

    def sampleX_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["sampx"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def sampleX_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_motor_states["sampx"] = state
        self.emit('stateChanged', (state, ))

    def sampleY_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["sampy"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def sampleY_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_motor_states["sampy"] = state
        self.emit('stateChanged', (state, ))

    def focus_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["focus"] = pos

    def start_auto_focus(self):
        self.cmd_start_auto_focus()

