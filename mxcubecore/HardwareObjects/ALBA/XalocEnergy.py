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
[Name] XalocEnergy

[Description]
HwObj used to configure the beamline energy.

[Signals]
- energyChanged
"""

#from __future__ import print_function

import logging

from mxcubecore.HardwareObjects.Energy import Energy

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"


class XalocEnergy(Energy):

    def __init__(self, name):
        Energy.__init__(self, name)
        self.logger = logging.getLogger("HWR.XalocEnergy")
        #self.energy_motor = None
        self.wavelength_motor = None
        self.is_tunable = None

        self.energy_position = None
        self.wavelength_position = None
        
    def init(self):
        #Energy.init(self)
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        #self.energy_motor = self.get_object_by_role("energy")
        self.wavelength_motor = self.get_object_by_role("wavelength")

        try:
            self.energy_motor = self.get_object_by_role("energy")
        except KeyError:
            logging.getLogger("HWR").warning("Energy: error initializing energy motor")

        try:
            self.is_tunable = self.get_property("tunable_energy")
        except KeyError:
            self.is_tunable = False
            logging.getLogger("HWR").warning("Energy: will be set to fixed energy")

        if self.energy_motor is not None:
            #self.connect(self.wavelength_motor, "valueChanged",
                        #self.energy_position_changed)
            self.connect(self.energy_motor, "valueChanged",
                        self.energy_position_changed)
            self.energy_motor.connect("stateChanged", self.energyStateChanged)
        

    def is_ready(self):
        try: 
            if self.energy_motor is not None: 
                return self.energy_motor.is_ready()
            else: return True
        except Exception as e:
            logging.getLogger("HWR").warning("Energy error %s" % str(e) )
            return True

    def can_move_energy(self):
        #if self.energy_motor is not none: 
            #return not self.energy_motor.is_moving()
        #else: return True
        return True

    def get_value(self):
        if self.energy_motor is not None:
            try:
                return self.energy_motor.get_value()
            except Exception:
                logging.getLogger("HWR").exception(
                    "EnergyHO: could not read current energy"
                )
                return None
        return self.default_en

    def get_wavelength(self):
        if self.wavelength_motor != None:
            self.wavelength_position = self.wavelength_motor.get_value()
        return self.wavelength_position

    def update_values(self):
        self.energy_position_changed()

    #TODO update resolution. Resolution has a method called energyChanged, which takes a egy but doenst use it
    #  this calls updateResolution, which also calls update_beam_center, but probably this doesnt affect Xaloc
    #  as the beam center is taken from Variables just before a collect. Check though...
    def energy_position_changed(self, value):
        self.energy_position = self.energy_motor.get_value()
        self.wavelength_position = self.wavelength_motor.get_value()
        if None not in [self.energy_position, self.wavelength_position]:
            self.emit('energyChanged', self.energy_position, self.wavelength_position)
            self.emit("valueChanged", (self.energy_position,))

    #def wavelength_position_changed(self, value):
        #wavelength_position = value
        #energy_position = energy_motor.get_value() 
        #if None not in [energy_position, wavelength_position]:
            #self.emit('energyChanged', energy_position, wavelength_position)

    def move_energy(self, value, timeout=0):
        current_egy = self.get_value()

        self.logger.debug("Moving energy to %s. now is %s" % (value, current_egy))

        if abs(value-current_egy) > self.energy_motor.move_threshold:
            self.energy_motor.set_value(value, timeout)
        else:     
            self.logger.debug("Change below threshold. not moved")

    set_value = move_energy
    #_set_value = move_energy

    def wait_move_energy_done(self):
        self.logger.debug("wait_move_energy_done energ_motor state is %s" % (self.energy_motor.get_state() ) )
        self.energy_motor.wait_ready(timeout = 30)

    def move_wavelength(self, value):
        # convert wavelength to energy and move energy
 
        current_lambda = self.get_wavelength()
        kV_from_lambda = 12.398419303652055 / value
        self.logger.debug("Requested wavelength change, moving wavelength to %s (E %s). now is %s" % 
                            (value, kV_from_lambda, current_lambda)
                         )

        self.move_energy( kV_from_lambda ) 
        #self.wavelength_motor.set_value(value)

    def wait_move_wavelength_done(self):
        self.wavelength_motor.wait_ready()
    
    def get_energy_limits(self):
        return self.energy_motor.get_limits()

    get_limits=get_energy_limits

    def get_wavelength_limits(self):
        return self.wavelength_motor.get_limits()

    set_wavelength = move_wavelength
    
    def stop(self):
        self.energy_motor.stop()
        self.energy_motor.update_values()

    def energyStateChanged(self, state):
        """
          state is a MotorState
          state.value[0] retrieves HardwareObjectState from MotorState
        """
        self.emit("stateChanged", (state.value[0],))

def test_hwo(hwo):
    print("Energy is: ", hwo.get_energy())
    print("Wavelength is: ", hwo.get_wavelength())
    print("Energy limits are: ", hwo.get_energy_limits())
    print("Wavelength limits are: ", hwo.get_wavelength_limits())
